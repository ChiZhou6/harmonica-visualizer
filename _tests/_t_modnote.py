# -*- coding: utf-8 -*-
"""v9.3「切音高 = 一个新音」离屏测试

背景（B站观众反馈）：纯手弹玩家的习惯弹法是**按住琴键不动、只切鼠标修饰键**，
游戏里这样会重新起音 —— 比如按住 z 切中键，就是 1 → #1 → 1 三个音。
而本程序原来只有"琴键被按下"这一个事件源：
  · 经典模式：只被琴键按下边沿推进 → 他弹到第 3、4 个音，程序还卡在第 2 个音；
  · 录音：只记按下那一下 → 三个音只录成一个。

本脚本用假键盘（只接管 GetAsyncKeyState）**真跑 `_poll_input`**，覆盖：
  1. 配置默认值 + 开关能关
  2. 经典模式：按住不动切修饰键，照样一个个把音消掉
  3. 没按琴键时切修饰键 → 什么也不算
  4. 同一周期"按下中键 + 按下琴键"只算一个音（去重），且录下来的音高是切换后的
  5. 录音：按住不动切修饰键，三个音全录下来，音高正确
  6. 两个琴键同时按住 → 切一次修饰键，两个通道各算一个新音
  7. 跟随模式不受影响（不额外触发按键判定，仍靠"按住自动接续"）
  8. 切音高但通道对不上谱面 → 红闪、不推进（与按错键一致）
  9. 绘制不崩
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402
from PySide6.QtWidgets import QApplication                       # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_modnote_test_")
hv.BASE_DIR = TMP
hv.CONFIG_PATH = os.path.join(TMP, "config.json")
hv.SONGS_DIR = os.path.join(TMP, "songs")
os.makedirs(hv.SONGS_DIR, exist_ok=True)

app = QApplication(sys.argv)
ok = True


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + label, "->", got, "" if good else ("(期望 %s)" % (want,)))


# ---------------------------------------------------------------- 假键盘
class FakeU32:
    """只接管 GetAsyncKeyState，其它调用转给真的 user32"""

    def __init__(self, real):
        self._r = real
        self.down = set()

    def GetAsyncKeyState(self, vk):
        return 0x8000 if vk in self.down else 0

    def __getattr__(self, name):
        return getattr(self._r, name)


real_u32 = hv.user32
fake = FakeU32(real_u32)
hv.user32 = fake

VK_Z = hv.vk_of("z")                    # 通道 0
VK_X = hv.vk_of("x")                    # 通道 1
VK_MID = hv.vk_of("mouse_middle")       # 半音
VK_L = hv.vk_of("mouse_left")           # 降调

cfg = hv.load_config()

# 三连：同一个键 ch0，音高 本音 → 半音 → 本音（正是观众说的 1 #1 1）
S1 = hv.Song("切音高三连", 120, [(0.0, 1.0, 0, 0), (1.0, 1.0, 0, 2), (2.0, 1.0, 0, 0)])
# 换键：ch0 → ch1 → ch0（用来验"通道对不上就红闪"）
S2 = hv.Song("换键", 120, [(0.0, 1.0, 0, 0), (1.0, 1.0, 1, 0), (2.0, 1.0, 0, 0)])
songs = [S1, S2]


def build(song_idx=0, mode="classic", recording=False):
    ov = hv.Overlay(cfg, songs)
    ov.cfg = dict(cfg)                  # 隔离，免得测试改坏的配置
    ov.mode = mode
    ov.song_idx = song_idx
    ov.cursor = 0
    ov.finished_at = None
    ov._input_ok = True
    ov.recording = bool(recording)
    ov.rec_count = 0
    ov.rec_log = []
    ov.key_down.clear()
    ov.held_mods = []
    ov._prev = {}
    ov._prev_mod = {}
    ov._prev_state = 0
    ov.wrong.clear()
    fake.down = set()
    return ov


print("[1] 配置")
check("mod_change_note 默认打开", hv.DEFAULT_CONFIG.get("mod_change_note"), True)

print("[2] 经典模式：按住琴键不动、只切修饰键 → 三个音都能消掉")
ov = build()
fake.down = {VK_Z}
ov._poll_input()
check("按下 z → 进入「按住中」（还没消）",
      (ov.held_press is not None and ov.held_press[1] == 0), True)
fake.down = set()                       # 松手 → 这时才真正消掉（v9.3）
ov._poll_input()
check("松手 → 第 1 个音消掉", (ov.cursor, ov.held_press), (1, None))
fake.down = {VK_Z}                      # 第 2 个音（半音）也是按 z
ov._poll_input()
check("再按住 z → 又进入按住中", ov.held_press is not None, True)
fake.down = {VK_Z, VK_MID}              # 手指没松，切中键（本音 → 半音，又一个新音）
ov._poll_input()
check("按住不动切中键 → 前一个消掉、新的接上（光标到 2）", ov.cursor, 2)
check("新的那个也在按住中", ov.held_press is not None, True)
fake.down = {VK_Z}                      # 松中键（半音 → 本音，第三个新音）
ov._poll_input()
check("再切回来 → 第 3 个也消掉", ov.cursor, 3)
fake.down = set()
ov._poll_input()
check("松手 → 结束标记已置上", ov.finished_at is not None, True)

print("[3] 没按琴键时切修饰键 → 什么也不算")
ov = build()
fake.down = {VK_MID}
ov._poll_input()
check("只按中键不按琴键 → 不推进", ov.cursor, 0)
fake.down = set()
ov._poll_input()
check("松掉中键也不推进", ov.cursor, 0)

print("[4] 同一周期：按下中键 + 按下琴键 → 只算一个音（去重）")
ov = build(recording=True)
fake.down = {VK_MID, VK_Z}
ov._poll_input()
check("只算一个音（没被算成两个）", ov.rec_count, 1)
check("录下来的音高是切换后的（半音）", ov.rec_log[-1], (0, 2))
ov.recording = False

print("[5] 录音：按住不动切修饰键 → 三个音全录下来，音高正确")
ov = build(recording=True)
fake.down = {VK_Z}
ov._poll_input()
check("第 1 个音（本音）", (ov.rec_count, ov.rec_log[-1]), (1, (0, 0)))
fake.down = {VK_Z, VK_MID}
ov._poll_input()
check("第 2 个音（半音）", (ov.rec_count, ov.rec_log[-1]), (2, (0, 2)))
fake.down = {VK_Z}
ov._poll_input()
check("第 3 个音（回到本音）", (ov.rec_count, ov.rec_log[-1]), (3, (0, 0)))
fake.down = {VK_Z, VK_L}
ov._poll_input()
check("再切左键（降调）→ 第 4 个音", (ov.rec_count, ov.rec_log[-1]), (4, (0, 1)))
check("录音记录顺序正确", [st for _ch, st in ov.rec_log], [0, 2, 0, 1])

print("[6] 两个琴键同时按住 → 切一次修饰键，两个通道各算一个新音")
ov = build(recording=True)
fake.down = {VK_Z, VK_X}
ov._poll_input()
check("两键同时按下 → 2 个音", ov.rec_count, 2)
fake.down = {VK_Z, VK_X, VK_MID}
ov._poll_input()
check("切一次修饰键 → 再来 2 个（共 4 个）", ov.rec_count, 4)
check("新记的两个都是半音", [st for _ch, st in ov.rec_log[-2:]], [2, 2])

print("[7] 跟随模式不受影响：切修饰键不额外触发按键判定")
ov = build(mode="follow")
calls = []
ov._on_note_press = lambda ch: calls.append(ch)
fake.down = {VK_Z}
ov._poll_input()
check("按下琴键照常判定一次", calls, [0])
fake.down = {VK_Z, VK_MID}
ov._poll_input()
check("跟随模式下切修饰键不判定（仍靠按住自动接续）", calls, [0])
ov = build(mode="classic")
calls = []
ov._on_note_press = lambda ch: calls.append(ch)
fake.down = {VK_Z}
ov._poll_input()
fake.down = {VK_Z, VK_MID}
ov._poll_input()
check("对照：经典模式下切修饰键会判定（[0, 0]）", calls, [0, 0])

print("[8] 切音高但通道对不上谱面 → 红闪、不推进（与按错键一致）")
ov = build(song_idx=1)
fake.down = {VK_Z}
ov._poll_input()
fake.down = set()
ov._poll_input()
check("先消掉第 1 个音（ch0）", ov.cursor, 1)
ov.wrong.clear()
fake.down = {VK_Z}                      # 下一个音是 ch1，却按着 z
ov._poll_input()
check("不推进", ov.cursor, 1)
check("该通道红闪", 0 in ov.wrong, True)
check("更不会进入按住中", ov.held_press, None)

print("[9] 开关关掉 → 退回旧行为（只有重新按琴键才算）")
ov = build()
ov.cfg["mod_change_note"] = False
fake.down = {VK_Z}
ov._poll_input()
fake.down = set()
ov._poll_input()
check("按一下再松手 → 照常消一个", ov.cursor, 1)
fake.down = {VK_Z, VK_MID}
ov._poll_input()
check("按住 + 切修饰键 → 光标不动（不算新音）", ov.cursor, 1)
check("但当前这个音仍是「按住中」", ov.held_press is not None, True)
fake.down = {VK_Z, VK_MID, VK_L}
ov._poll_input()
check("再切一个也不动", ov.cursor, 1)
fake.down = set()
ov._poll_input()
check("松手 → 才推进到第 2 个", ov.cursor, 2)

print("[10] 关掉输入读取时一切照旧（不炸）")
ov = build()
ov._input_ok = False
ov._poll_input()
check("不读输入时直接返回", ov.cursor, 0)
ov._input_ok = True

print("[11] 绘制不崩（含「按住中」的状态）")
ov = build(recording=True)
fake.down = {VK_Z, VK_MID}
ov._poll_input()
ov.resize(760, 560)
ov.show()
pm = ov.grab()
check("录音视图截图非空", (pm.width(), pm.height()), (760, 560))
ov.recording = False
fake.down = set()
ov._poll_input()
fake.down = {VK_Z}
ov._poll_input()
check("经典模式按住中", ov.held_press is not None, True)
pm = ov.grab()
check("「按住中」截图非空", (pm.width(), pm.height()), (760, 560))
ov.close()

hv.user32 = real_u32

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
