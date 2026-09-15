# -*- coding: utf-8 -*-
"""V9 跟随模式倍速 离屏测试

覆盖：倍速默认值与步进/上下限、播放时间随倍速、判定窗口在真实时间上恒定、
按住时长随倍速同步、音符屏幕间距不受倍速影响、演奏中改倍速画面不跳、
热键绑定与 do_action 通路、倍速下按住的实际时长、绘制不崩。
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox          # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_rate_test_")
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


# BPM 120 → 1 拍 = 0.5 秒；三个音各 4 拍，命中时刻 0 / 2 / 4 秒
with open(os.path.join(hv.SONGS_DIR, "rate.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=倍速测试\n1 - - - 2 - - - 3 - - - -\n")

cfg = hv.load_config()
ov = hv.Overlay(cfg, hv.load_songs())
ov._input_ok = True


def pick(title):
    for i, s in enumerate(ov.songs):
        if s.title == title:
            ov.song_idx = i
            return s
    raise AssertionError("找不到曲谱 " + title)


print("[1] 配置默认值")
check("follow_rate 默认 1.0", hv.DEFAULT_CONFIG.get("follow_rate"), 1.0)
check("hold_min_seconds 默认 0.15", hv.DEFAULT_CONFIG.get("hold_min_seconds"), 0.15)
check("hold_min_beats 已废弃（不该再存在）", "hold_min_beats" in hv.DEFAULT_CONFIG, False)
check("热键 rate_up", hv.DEFAULT_CONFIG["hotkeys"].get("rate_up"), "shift+up")
check("热键 rate_down", hv.DEFAULT_CONFIG["hotkeys"].get("rate_down"), "shift+down")

print("[2] change_rate：每次 10%，夹在 20% ~ 200%")
ov.cfg["follow_rate"] = 1.0
check("+10% → 1.1", ov.change_rate(0.1), 1.1)
check("-10% → 1.0", ov.change_rate(-0.1), 1.0)
ov.cfg["follow_rate"] = 0.2
check("已到下限 20% → 不再降", ov.change_rate(-0.1), 0.2)
ov.cfg["follow_rate"] = 2.0
check("已到上限 200% → 不再升", ov.change_rate(0.1), 2.0)
ov.change_rate(-2.0)                                   # 越界值也要夹住
check("一次性大幅调整也夹在 0.2~2.0", 0.2 <= ov.cfg["follow_rate"] <= 2.0, True)

print("[3] 播放时间随倍速（lead 归零后一眼能看出来）")
ov.cfg["follow_lead"] = 0.0
ov.mode = "follow"
ov.follow_state = "playing"
ov.follow_t0 = 100.0
for rate, want in [(1.0, 1.0), (2.0, 2.0), (0.5, 0.5), (1.5, 1.5)]:
    ov.cfg["follow_rate"] = rate
    check("倍速 %d%% → play(101)=%.2f" % (round(rate * 100), want),
          round(ov._follow_play_time(101.0), 4), want)

print("[4] 判定窗口在真实时间上恒定")
ov.cfg["follow_window"] = 0.20
ov.cfg["follow_rate"] = 1.0
check("100% 窗口 0.20 曲谱秒", round(ov._follow_window(), 4), 0.20)
ov.cfg["follow_rate"] = 2.0
check("200% 窗口 0.40 曲谱秒 = 真实 0.20 秒", round(ov._follow_window(), 4), 0.40)
ov.cfg["follow_rate"] = 0.5
check("50% 窗口 0.10 曲谱秒 = 真实 0.20 秒", round(ov._follow_window(), 4), 0.10)

print("[5] 吃掉一个音要多久（曲谱秒）→ 真实时长随倍速同步")
pick("倍速测试")
ov.cfg["follow_rate"] = 1.0
check("4 拍音 = 2.0 曲谱秒", round(ov._hold_total(4.0), 4), 2.0)
check("0.1 拍音吃地板 0.15 秒", round(ov._hold_total(0.1), 4), 0.15)
ov.cfg["follow_rate"] = 2.0
check("200%：仍是 2.0 曲谱秒 → 真实 1.0 秒", round(ov._hold_total(4.0), 4), 2.0)
check("200%：地板也折算成 0.3 曲谱秒 → 真实 0.15 秒",
      round(ov._hold_total(0.1), 4), 0.3)
ov.cfg["follow_rate"] = 1.0

print("[6] 音符屏幕间距不受倍速影响（只是整体走得更快）")
hits1 = [n[0] * ov._follow_spb() for n in ov.song.notes]
ov.cfg["follow_rate"] = 2.0
hits2 = [n[0] * ov._follow_spb() for n in ov.song.notes]
check("命中时刻（=屏幕位置）与倍速无关", hits1, hits2)
check("相邻音间距 2.0 秒 × 200px/s = 400px",
      round((hits1[1] - hits1[0]) * 200.0, 1), 400.0)

print("[7] 演奏中改倍速：画面不跳（play 连续）")
ov.cfg["follow_lead"] = 2.0
ov.cfg["follow_rate"] = 1.0
ov.follow_t0 = 100.0
now = time.monotonic()
before = ov._follow_play_time(now)
ov.change_rate(0.1)
after = ov._follow_play_time(now)
check("改倍速前后 play 连续", abs(after - before) < 0.05, True)
check("倍速确实变了", ov.cfg["follow_rate"], 1.1)

print("[8] 热键绑定与动作通路")
check("rate_up → Shift+↑", ov.hotkey_vks.get("rate_up"), [(0x10, 0x26)])
check("rate_down → Shift+↓", ov.hotkey_vks.get("rate_down"), [(0x10, 0x28)])
check("面板提示文字", hv.hotkey_text(ov.cfg, "rate_up"), "Shift+↑")
ov.cfg["follow_rate"] = 1.0
ov.do_action("rate_up")
check("do_action(rate_up) → 110%", ov.cfg["follow_rate"], 1.1)
ov.do_action("rate_down")
check("do_action(rate_down) → 100%", ov.cfg["follow_rate"], 1.0)

print("[9] 200% 下按住：真实 1 秒吃满 4 拍")
ov.cfg["follow_rate"] = 2.0
ov.cfg["follow_lead"] = 0.0
ov.mode = "follow"
ov.follow_state = "playing"
ov.follow_next = 0
ov.follow_hold = None
ov.follow_missed.clear()
ov.follow_fade.clear()
ov.key_down.clear()
ov.finished_at = None
ov.flashes.clear()
ov.impacts.clear()
ov.wrong.clear()
ov.follow_t0 = 100.0
ov._follow_press(0, 100.0)                     # play(100)=0 = 第一个音命中时刻
check("接住第一个音", ov.follow_hold is not None, True)
ov.key_down[0] = True
ov._follow_hold_tick(100.5)                    # play=1.0 < 2.0
check("真实 0.5 秒时还没吃完", ov.follow_hold is not None, True)
ov._follow_hold_tick(101.0)                    # play=2.0 → 吃满
check("真实 1.0 秒时吃满（100% 下要 2 秒）", ov.follow_hold, None)
check("follow_next 前进", ov.follow_next, 1)

print("[10] 50% 下按住：真实 4 秒才吃满 4 拍")
ov.cfg["follow_rate"] = 0.5
ov.follow_state = "playing"
ov.follow_next = 0
ov.follow_hold = None
ov.key_down.clear()
ov.follow_t0 = 100.0
ov._follow_press(0, 100.0)
ov.key_down[0] = True
ov._follow_hold_tick(102.0)                    # play=1.0
check("真实 2 秒时还没吃完", ov.follow_hold is not None, True)
ov._follow_hold_tick(104.0)                    # play=2.0
check("真实 4 秒时吃满", ov.follow_hold, None)

print("[11] 绘制不崩（倍速提示画得出来）")
ov.cfg["follow_rate"] = 1.3
ov.resize(760, 560)
ov.show()
pm = ov.grab()
check("截图非空", (pm.width(), pm.height()), (760, 560))
ov.close()

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
