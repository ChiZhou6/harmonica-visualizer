# -*- coding: utf-8 -*-
"""跟随演奏模式 + Dr-hydra 曲谱库格式解析 离屏测试"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv              # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox   # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_follow_test_")
hv.BASE_DIR = TMP
hv.CONFIG_PATH = os.path.join(TMP, "config.json")
hv.SONGS_DIR = os.path.join(TMP, "songs")
os.makedirs(hv.SONGS_DIR, exist_ok=True)

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)

app = QApplication(sys.argv)
ok = True


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + label, "->", got, "" if good else ("(期望 %s)" % (want,)))


print("[1] 节奏标记 → 拍数")
for tok, want in [("1", 4.0), ("2·", 3.0), ("2", 2.0), ("4·", 1.5), ("4", 1.0),
                  ("8·", 0.75), ("8", 0.5), ("16·", 0.375), ("16", 0.25), ("32", 0.125),
                  ("2.5b", 2.5), ("4.25b", 4.25), ("1.25b", 1.25), ("5b", 5.0)]:
    check("rhythm_to_beats(%r)" % tok, hv.rhythm_to_beats(tok), want)

print("[2] 键位 token → (通道, 音调)")
for tok, want in [("N-#", (5, 4)), ("X#", (1, 2)), ("Z+", (0, 3)), (",-", (7, 1)),
                  ("V", (3, 0)), ("M-", (6, 1)), ("X+#", (1, 5)), ("N#", (5, 2))]:
    check("dfh_key_token(%r)" % tok, hv.dfh_key_token(tok), want)

print("[3] Dr-hydra 样张解析")
SAMPLE = """测试曲 — 三角洲口琴谱
BPM 120 · 8 音符 · 2 小节 · 移调 0

键位标记：+ 升调（鼠标右键） / - 降调（鼠标左键） / # 半音（鼠标中键）

小节   1 (4/4)
  简谱  1 2 3 4
  键位  Z X C V
  节奏  4 4 4 4

小节   2 (4/4)
  简谱  5 6 7 1'
  键位  B N M ,
  节奏  2 2 2 2
"""
s = hv.parse_dfh_tab(SAMPLE)
check("is_dfh_tab", hv.is_dfh_tab(SAMPLE), True)
check("标题", s.title, "测试曲")
check("BPM", s.bpm, 120.0)
check("音符数", len(s.notes), 8)
check("第2小节首音 start", s.notes[4][0], 4.0)
check("第2小节第2音 start", s.notes[5][0], 6.0)
check("总拍数", s.total_beats, 12.0)

print("[4] 跟随演奏模式状态机（idle→countdown→playing→done）")
with open(os.path.join(hv.SONGS_DIR, "t.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=状态机测试\n1 2 3 -\n")
cfg = hv.load_config()
songs = hv.load_songs()
ov = hv.Overlay(cfg, songs)
for i, ss in enumerate(songs):
    if ss.title == "状态机测试":
        ov.song_idx = i
        break
ov.mode = "follow"
ov.reset_playback()
check("初始 idle", ov.follow_state, "idle")
check("follow_next=0", ov.follow_next, 0)

# 第一个音是 ch=0（音符 1）；按错键不触发倒计时
ov._follow_press(1, 100.0)
check("按错键仍 idle", ov.follow_state, "idle")

# 按对第一个音 → countdown（这次点击不消除任何矩形）
ov._follow_press(0, 100.0)
check("进入 countdown", ov.follow_state, "countdown")
check("倒计时 3 秒", round(ov.countdown_deadline - 100.0), 3)
check("倒计时期间 follow_next 不动", ov.follow_next, 0)

# 模拟倒计时结束（_tick 里的赋值逻辑）
spb = ov._follow_spb()
first = ov.song.notes[0][0] * spb
ov.follow_t0 = 103.0 - first
ov.follow_state = "playing"
check("进入 playing", ov.follow_state, "playing")

lead = ov._follow_lead()
hit_now = 103.0 + lead          # 第一个音的命中时刻
check("播放时间对齐（第一个音在判定线）",
      round(ov._follow_play_time(hit_now), 4), round(first, 4))

# 在正确时刻按对 → 命中，follow_next 前进
ov._follow_press(0, hit_now)
check("第一个音命中 follow_next=1", ov.follow_next, 1)

# 时机太早（超窗口）→ 不命中
ov.follow_next = 1
ov._follow_press(1, hit_now - 1.0)
check("太早按不命中", ov.follow_next, 1)

# miss 检查：过了很久 → 自动跳过
ov.follow_next = 1
ov._follow_advance_missed(hit_now + 5.0)
check("miss 后 follow_next 前进", ov.follow_next >= 2, True)
check("有 miss 记录", len(ov.follow_missed) > 0, True)

print("[5] 两个真实曲谱文件的解析（念张师 / 春日影）")
for path, want_n, want_bpm in [
    (r"E:/收纳盒/QQ/念张师 主旋律.txt", 387, 135.0),
    (r"E:/收纳盒/QQ/春日影（CRYCHIC ver.）干净无杂音,适合三角洲.txt", 593, 97.0),
]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    ss = hv.parse_dfh_tab(text)
    check("音符数 %s" % path.split("/")[-1][:6], len(ss.notes), want_n)
    check("BPM %s" % path.split("/")[-1][:6], ss.bpm, want_bpm)

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
