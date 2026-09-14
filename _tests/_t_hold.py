# -*- coding: utf-8 -*-
"""长音（按住才消）离屏测试

覆盖：短音照旧"按一下即消"；长音按下只算接住、要按住到满时值才完成；
按住期间短暂松手有宽限；松太久则漏过（变暗落走）；按住期间不判 miss、
不接受别的按键；经典模式完全不受影响。
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                    # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox   # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_hold_test_")
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


# 曲谱：[0] 1 拍短音(ch0) / [1] 3 拍长音(ch1) / [2] 5 拍长音(ch2)，BPM 120 → 1 拍 = 0.5 秒
with open(os.path.join(hv.SONGS_DIR, "hold.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=长音测试\n1 2 - - 3 - - - -\n")
with open(os.path.join(hv.SONGS_DIR, "allhold.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=全长音\n5 - - - -\n")

cfg = hv.load_config()
ov = hv.Overlay(cfg, hv.load_songs())
ov._input_ok = True                       # 离屏环境强制打开输入（长音判定要看按住状态）
ov.cfg["follow_lead"] = 2.0

print("[1] 配置与曲谱")
check("hold_min_beats 默认 1.5", hv.DEFAULT_CONFIG.get("hold_min_beats"), 1.5)
check("hold_grace 默认 0.20", hv.DEFAULT_CONFIG.get("hold_grace"), 0.20)


def pick(title):
    for i, s in enumerate(ov.songs):
        if s.title == title:
            ov.song_idx = i
            return s
    raise AssertionError("找不到曲谱 " + title)


s = pick("长音测试")
check("音符数 3", len(s.notes), 3)
check("音[0] 1 拍", (s.notes[0][1], s.notes[0][2]), (1, 0))
check("音[1] 3 拍", (s.notes[1][1], s.notes[1][2]), (3, 1))
check("音[2] 5 拍", (s.notes[2][1], s.notes[2][2]), (5, 2))

spb = ov._follow_spb()
check("每拍 0.5 秒", round(spb, 4), 0.5)

# 让 play(now) = now - 102.0；第一个音 hit=0 秒 → now=102 命中
T0 = 100.0
ov.follow_t0 = T0


def start_playing():
    ov.mode = "follow"
    ov.follow_state = "playing"
    ov.follow_t0 = T0
    ov.follow_next = 0
    ov.follow_missed.clear()
    ov.follow_fade.clear()
    ov.follow_hold = None
    ov.key_down.clear()
    ov.finished_at = None
    ov.flashes.clear()
    ov.impacts.clear()
    ov.wrong.clear()


print("[2] 短音：照旧按一下即消")
start_playing()
check("play(102.0)=0", round(ov._follow_play_time(102.0), 4), 0.0)
ov._follow_press(0, 102.0)
check("命中后 follow_next=1", ov.follow_next, 1)
check("短音不进入按住状态", ov.follow_hold, None)
check("有碰撞特效", len(ov.impacts), 1)

print("[3] 长音：按下只算接住，不立即消除")
ov._follow_press(1, 102.5)                # 第二个音 hit=0.5 秒 → now=102.5
check("follow_next 不动（仍是 1）", ov.follow_next, 1)
check("进入按住状态", ov.follow_hold is not None, True)
check("按住的音符下标", ov.follow_hold and ov.follow_hold["idx"], 1)
check("按住的时值 3 拍", ov.follow_hold and ov.follow_hold["dur"], 3.0)

print("[4] 按住期间：不判 miss、不接受其他按键")
ov._follow_advance_missed(103.5)          # 时间已过第二个音的判定窗口
check("正按住的长音不被判 miss", ov.follow_next, 1)
check("没被记进 missed", 1 in ov.follow_missed, False)
n_impacts = len(ov.impacts)
ov._follow_press(0, 103.5)                # 期间乱按别的键
check("按住期间忽略其他按键", (ov.follow_next, len(ov.impacts)), (1, n_impacts))

print("[5] 按住到满时值 → 完成")
ov.key_down[1] = True
check("进度 0.67", round(ov._follow_hold_progress(103.5), 2), 0.67)
check("103.5 时还没完（1.5 秒才满）", ov._follow_hold_tick(103.5), False)
check("follow_next 仍未动", ov.follow_next, 1)
check("进度 1.0", round(ov._follow_hold_progress(104.0), 2), 1.0)
check("104.0 时按满 3 拍（1.5 秒）→ 完成", ov._follow_hold_tick(104.0), True)
check("完成 → follow_next=2", ov.follow_next, 2)
check("按住状态已清空", ov.follow_hold, None)
check("完成时又有一圈光晕", len(ov.impacts) > n_impacts, True)

print("[6] 长音松手有宽限，超过宽限才断")
ov._follow_press(2, 104.0)                # 第三个音 hit=2.0 秒 → now=104.0（5 拍长音）
check("进入按住 idx=2", ov.follow_hold and ov.follow_hold["idx"], 2)
ov.key_down[2] = False
ov._follow_hold_tick(104.5)               # 刚松手
check("刚松手不立刻断", ov.follow_hold is not None, True)
ov.key_down[2] = True
ov._follow_hold_tick(104.6)               # 宽限内又按回来
check("宽限内按回来 → 继续按住", ov.follow_hold is not None, True)
check("松手计时被清掉", ov.follow_hold and ov.follow_hold["released"], None)

ov.key_down[2] = False
ov._follow_hold_tick(105.0)               # 再次松手
ov._follow_hold_tick(105.3)               # 105.3-105.0 = 0.3 秒 > 0.2 宽限
check("超宽限 → 中断", ov.follow_hold, None)
check("中断后跳到下一个音", ov.follow_next, 3)
check("断掉的长音记进 fade（继续变暗落走）", 2 in ov.follow_fade, True)
check("该通道红闪提示", 2 in ov.wrong, True)
check("全弹完 → done", ov.follow_state, "done")

print("[7] 全曲都是长音：一起按满 → 完成")
pick("全长音")
start_playing()
ov.cfg["follow_t0_play"] = None
ov._follow_press(4, 102.0)                # 唯一一个音（简谱 5 = 通道 4）：5 拍
check("进入按住", ov.follow_hold and ov.follow_hold["idx"], 0)
check("还没完成", ov.follow_state, "playing")
ov.key_down[4] = True
ov._follow_hold_tick(103.0)               # 0.5 秒 < 2.5 秒
check("1 秒时仍未完成", ov.follow_state, "playing")
ov._follow_hold_tick(104.5)               # 2.5 秒整 → 完成
check("按满 5 拍 → done", ov.follow_state, "done")
check("follow_next=1", ov.follow_next, 1)

print("[8] 关掉输入读取时不会卡住（一律当按住）")
pick("长音测试")
start_playing()
ov._input_ok = False
ov._follow_press(0, 102.0)
ov._follow_press(1, 102.5)
check("进入按住", ov.follow_hold is not None, True)
ov.key_down[1] = False
ov._follow_hold_tick(103.0)
check("读不到输入时不会误判松手", ov.follow_hold is not None, True)
ov._follow_hold_tick(104.0)
check("按时间自然完成", ov.follow_hold, None)
ov._input_ok = True

print("[9] reset_playback 清空长音状态")
start_playing()
ov._follow_press(0, 102.0)
ov._follow_press(1, 102.5)
ov.follow_fade.add(9)
ov.reset_playback()
check("按住状态清空", ov.follow_hold, None)
check("fade 清空", len(ov.follow_fade), 0)
check("回到 idle", ov.follow_state, "idle")

print("[10] 经典模式不受影响（长音也是点一下即消）")
ov.mode = "classic"
ov.cursor = 0
ov.finished_at = None
ov._on_note_press(0)                      # 第一个音 ch0
check("经典模式立即消除", ov.cursor, 1)
check("经典模式不会进入按住状态", ov.follow_hold, None)
ov._on_note_press(1)                      # 第二个音是 3 拍长音
check("经典长音也是按一下即消", ov.cursor, 2)

print("[11] 绘制不崩（按住中的长音）")
ov.mode = "follow"
pick("长音测试")
start_playing()
ov._follow_press(1, 102.5)
ov.key_down[1] = True
ov.resize(760, 560)
ov.show()
pm = ov.grab()
check("截图非空", (pm.width(), pm.height()), (760, 560))
ov._follow_hold_tick(103.6)
pm2 = ov.grab()
check("按住中重绘正常", pm2.width(), 760)
ov.close()

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
