# -*- coding: utf-8 -*-
"""V9 按住消除 离屏测试

v9 起跟随模式的语义：**每个音都要按住**（口琴本来就要长按）。
按下的瞬间只算"接住"，要一直按住让判定线把它一点点吃掉，按满这个音的
时值才算完成；中途松手剩下的漏过。经典模式完全不变（按一下即消）。

覆盖：全部音都要按住 / 按满才完成 / 松手宽限 / 超宽限中断 / 按住期间不判
miss 且忽略其他按键 / 连点不重置进度 / 按住不放自动接住同键连音 / 不同键不
会误接 / 最短按住地板 / 关输入不卡死 / reset 清空 / 经典模式不受影响 / 绘制不崩。
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox          # noqa: E402

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


# BPM 120 → 1 拍 = 0.5 秒
# mix：1 拍短音(ch0) / 3 拍(ch1) / 5 拍(ch2)，命中时刻 0 / 0.5 / 2.0 秒
with open(os.path.join(hv.SONGS_DIR, "hold.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=按住测试\n1 2 - - 3 - - - -\n")
# same：4 个同键连音，各 1 拍，命中时刻 0 / 0.5 / 1.0 / 1.5 秒
with open(os.path.join(hv.SONGS_DIR, "same.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=连音测试\n1 1 1 1\n")
# alt：两个键交替
with open(os.path.join(hv.SONGS_DIR, "alt.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=交替测试\n1 2 1 2\n")
# tiny：0.25 拍一个音 → 触发最短按住地板
with open(os.path.join(hv.SONGS_DIR, "tiny.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=超短音\n1 1 1 1\n")

cfg = hv.load_config()
ov = hv.Overlay(cfg, hv.load_songs())
ov._input_ok = True                    # 离屏环境强制打开输入（按住判定要看按键状态）
ov.cfg["follow_lead"] = 2.0
T0 = 100.0                             # play(now) = now - 102.0


def pick(title):
    for i, s in enumerate(ov.songs):
        if s.title == title:
            ov.song_idx = i
            return s
    raise AssertionError("找不到曲谱 " + title)


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


print("[1] 配置")
check("hold_min_seconds 默认 0.15", hv.DEFAULT_CONFIG.get("hold_min_seconds"), 0.15)
check("hold_grace 默认 0.20", hv.DEFAULT_CONFIG.get("hold_grace"), 0.20)
check("hold_min_beats 已废弃", "hold_min_beats" in hv.DEFAULT_CONFIG, False)

print("[2] 曲谱")
s = pick("按住测试")
check("音符数 3", len(s.notes), 3)
check("音[0] 1 拍 ch0", (s.notes[0][1], s.notes[0][2]), (1, 0))
check("音[1] 3 拍 ch1", (s.notes[1][1], s.notes[1][2]), (3, 1))
check("音[2] 5 拍 ch2", (s.notes[2][1], s.notes[2][2]), (5, 2))
spb = ov._follow_spb()
check("每拍 0.5 秒", round(spb, 4), 0.5)

print("[3] 短音也要按住：按下只算接住，不立即消除")
start_playing()
check("play(102.0)=0", round(ov._follow_play_time(102.0), 4), 0.0)
ov._follow_press(0, 102.0)
check("接住（进入按住状态）", ov.follow_hold is not None, True)
check("接住的是第 0 个音", ov.follow_hold and ov.follow_hold["idx"], 0)
check("follow_next 不前进", ov.follow_next, 0)
check("接住瞬间没有消除光晕（还没吃掉）", len(ov.impacts), 0)
check("但灯带亮一下做反馈", 0 in ov.flashes, True)

print("[4] 按住满时值 → 完成")
ov.key_down[0] = True
check("按了 0.4 秒还没满（1 拍 = 0.5 秒）", ov._follow_hold_tick(102.4), False)
check("进度 0.8", round(ov._follow_hold_progress(102.4), 2), 0.8)
check("按满 1 拍（0.5 秒）→ 完成", ov._follow_hold_tick(102.5), True)
check("完成 → follow_next=1", ov.follow_next, 1)
check("按住状态清空", ov.follow_hold, None)
check("完成时才出现消除光晕", len(ov.impacts), 1)
check("该通道灯带再亮一次", 0 in ov.flashes, True)

print("[5] 松手有宽限，超过宽限才断")
ov._follow_press(1, 102.5)             # 3 拍音，命中时刻 0.5 秒
check("接住 idx=1", ov.follow_hold and ov.follow_hold["idx"], 1)
ov.key_down[1] = False
ov._follow_hold_tick(103.0)            # 刚松手
check("刚松手不立刻断", ov.follow_hold is not None, True)
ov.key_down[1] = True
ov._follow_hold_tick(103.1)            # 宽限内按回来
check("宽限内按回来 → 继续按住", ov.follow_hold is not None, True)
check("松手计时被清掉", ov.follow_hold and ov.follow_hold["released"], None)

print("[6] 超宽限 → 中断，剩下的漏过")
ov.key_down[1] = False
ov._follow_hold_tick(103.3)            # 刚松手
ov._follow_hold_tick(103.6)            # 0.3 秒 > 0.2 宽限
check("超宽限 → 中断", ov.follow_hold, None)
check("中断后跳到下一个音", ov.follow_next, 2)
check("断掉的音记进 fade（继续变暗落走）", 1 in ov.follow_fade, True)
check("该通道红闪提示", 1 in ov.wrong, True)

print("[7] 按住期间：不判 miss、忽略其他按键")
start_playing()
ov._follow_press(0, 102.0)
ov.key_down[0] = True
n_imp = len(ov.impacts)
ov._follow_advance_missed(103.5)       # 早就过了第一个音的判定窗口
check("正被按住的音不判 miss", ov.follow_next, 0)
check("没被记进 missed", 0 in ov.follow_missed, False)
ov._follow_press(1, 102.6)             # 按住期间乱按别的键
check("按住期间忽略其他按键", (ov.follow_next, len(ov.impacts)), (0, n_imp))
check("按错的那个通道红闪", 1 in ov.wrong, True)

print("[8] 连点不重置进度（否则这个音永远吃不完）")
start_playing()
ov._follow_press(0, 102.0)
ov.key_down[0] = True
start_at = ov.follow_hold["start"]
ov.key_down[0] = False
ov._follow_hold_tick(102.2)            # 松手
ov.key_down[0] = True
ov._follow_press(0, 102.3)             # 宽限内又按一下（会触发按键事件）
check("重按没把开始时刻往后刷", ov.follow_hold and ov.follow_hold["start"], start_at)
ov._follow_hold_tick(102.5)
check("照样能在 102.5 吃满", ov.follow_hold, None)

print("[9] 按住不放 → 自动接住同键连音")
pick("连音测试")
check("4 个音都是 ch0", [n[2] for n in ov.song.notes], [0, 0, 0, 0])
start_playing()
ov._follow_press(0, 102.0)             # 接住第 1 个音
ov.key_down[0] = True                  # 手指一直按着不松
ov._follow_hold_tick(102.5)            # 吃满第 1 个
check("第 1 个吃完 follow_next=1", ov.follow_next, 1)
check("自动接住第 2 个", ov._follow_auto_catch(102.5), True)
check("接住的是 idx=1", ov.follow_hold and ov.follow_hold["idx"], 1)
ov._follow_hold_tick(103.0)            # 吃满第 2 个
ov._follow_auto_catch(103.0)
check("自动接住第 3 个", ov.follow_hold and ov.follow_hold["idx"], 2)
ov._follow_hold_tick(103.5)
ov._follow_auto_catch(103.5)
check("自动接住第 4 个", ov.follow_hold and ov.follow_hold["idx"], 3)
ov._follow_hold_tick(104.0)
check("全部吃完 → done", ov.follow_state, "done")
check("follow_next=4", ov.follow_next, 4)

print("[10] 松手后不会凭空接住")
start_playing()
ov._follow_press(0, 102.0)
ov.key_down[0] = False                 # 松手
ov._follow_hold_tick(102.5)
check("没按着 → 不自动接住", ov._follow_auto_catch(102.5), False)
check("没有按住状态", ov.follow_hold, None)

print("[11] 不同键不会被误接")
pick("交替测试")
check("键位交替 ch0/ch1", [n[2] for n in ov.song.notes[:4]], [0, 1, 0, 1])
start_playing()
ov._follow_press(0, 102.0)
ov.key_down[0] = True
ov._follow_hold_tick(102.5)            # 吃满 ch0 的音
check("跳到下一个音", ov.follow_next, 1)
check("下一个是 ch1、键没按着 → 不接住", ov._follow_auto_catch(102.5), False)

print("[12] 最短按住地板（超短音不至于抖得按不住）")
ov.cfg["follow_rate"] = 1.0
check("0.05 拍的音也要按 0.15 秒", round(ov._hold_total(0.05), 4), 0.15)
check("1 拍的音按 0.5 秒（地板不生效）", round(ov._hold_total(1.0), 4), 0.5)

print("[13] 关掉输入读取时不会卡死（一律当按住）")
pick("按住测试")
start_playing()
ov._input_ok = False
ov._follow_press(0, 102.0)
ov.key_down[0] = False                 # 读不到输入 → 不该被当成松手
ov._follow_hold_tick(102.2)
check("读不到输入时不会误判松手", ov.follow_hold is not None, True)
ov._follow_hold_tick(102.5)
check("按时间自然吃满", ov.follow_hold, None)
ov._input_ok = True

print("[14] reset_playback 清空按住状态")
start_playing()
ov._follow_press(0, 102.0)
ov.follow_fade.add(9)
ov.reset_playback()
check("按住状态清空", ov.follow_hold, None)
check("fade 清空", len(ov.follow_fade), 0)
check("回到 idle", ov.follow_state, "idle")

print("[15] 经典模式不受跟随模式那套长按逻辑影响（v9.3 起是「按住才消」）")
ov.mode = "classic"
ov.cursor = 0
ov.finished_at = None
ov.held_press = None
ov._on_note_press(0)
check("按下进入「按住中」，先不消", ov.cursor, 0)
check("经典模式不会进入 follow_hold（那是跟随模式的）", ov.follow_hold, None)
check("当前的按住状态是经典的 held_press", ov.held_press is not None, True)
ov._on_note_release(0)                       # 松手 → 这时才真正消掉
check("松手后消掉第 1 个音", ov.cursor, 1)
ov._on_note_press(1)
ov._on_note_release(1)
check("3 拍音也是松手才消", ov.cursor, 2)

print("[16] 绘制不崩（按住中的音）")
ov.mode = "follow"
pick("按住测试")
start_playing()
ov._follow_press(0, 102.0)
ov.key_down[0] = True
ov.resize(760, 560)
ov.show()
pm = ov.grab()
check("截图非空", (pm.width(), pm.height()), (760, 560))
ov._follow_hold_tick(102.3)
pm2 = ov.grab()
check("按住中重绘正常", pm2.width(), 760)
ov.close()

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
