# -*- coding: utf-8 -*-
"""v9.3「经典模式：按住才消」离屏测试

需求（用户提的）：经典模式下按对键的那一瞬间块就立刻缩小消失了，
导致演奏长音时"手还没松、块已经没了"。改成：按下的那一刻块变成半透明 +
"被按住"的特效，一直留到**玩家松手**才真正消失。

本脚本用假键盘（只接管 GetAsyncKeyState）真跑 `_poll_input`，覆盖：
  1. 配置默认值
  2. 按下 → 进入"按住中"：光标不动、画面不跳（没有 ghost / slide）
  3. 长音：按住期间反复轮询（模拟 1 秒）也一直不消
  4. 松手 → 才真正消掉（出现 ghost 残影 + 整叠下落 + 光标前进）
  5. 开关关掉 → 退回旧行为（按下即消）
  6. 按住期间按错键 → 红闪，但手上的按住状态不受影响
  7. "松开旧键 + 按下新键"落在同一轮询周期 → 不误判（先松后按）
  8. 按错键不会进入"按住中"
  9. 最后一个音也要松手才算完成
 10. 绘制：同一帧里"按住中的块"比常态块明显更淡（半透明），且还看得见
 11. 跟随模式不受影响（按住是它自己的时间轴在管）
 12. 重来 / 换曲谱会清掉按住状态
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402
from PySide6.QtWidgets import QApplication                       # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_holdrel_test_")
hv.BASE_DIR = TMP
hv.CONFIG_PATH = os.path.join(TMP, "config.json")
hv.SONGS_DIR = os.path.join(TMP, "songs")
os.makedirs(hv.SONGS_DIR, exist_ok=True)

app = QApplication(sys.argv)

# 字体要在 QApplication 之后注册：离屏(offscreen)平台下没注册会退回很宽的替身字体，
# 块中心会被字母占满 → 像素比对不准。⚠️ 在 QApplication 之前调用会直接段错误。
try:
    from PySide6.QtGui import QFontDatabase
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")
except Exception:
    pass

ok = True


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + label, "->", got, "" if good else ("(期望 %s)" % (want,)))


class FakeU32:
    """只接管 GetAsyncKeyState，其它调用转给真 user32"""

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

# 同色同通道三连（像素比对用：同帧内三块长得一样，只有第一块在"按住中"）
SAME = hv.Song("同色三连", 120, [(0.0, 1.0, 0, 0), (1.0, 1.0, 0, 0), (2.0, 1.0, 0, 0)])
# 换键（验"松旧键 + 按新键"落在同一周期的顺序问题）：先 ch1(x) 再 ch0(z)
SWAP = hv.Song("换键", 120, [(0.0, 1.0, 1, 0), (1.0, 1.0, 0, 0)])
# 单音（验最后一个音也要松手才算完成）
ONE = hv.Song("单音", 120, [(0.0, 1.0, 0, 0)])
# 长音（时值 4 拍）
LONG = hv.Song("长音", 120, [(0.0, 4.0, 0, 0), (4.0, 1.0, 0, 0)])
songs = [SAME, SWAP, ONE, LONG]


def build(song_idx=0, mode="classic"):
    ov = hv.Overlay(cfg, songs)
    ov.cfg = dict(cfg)
    ov.mode = mode
    ov.song_idx = song_idx
    ov.cursor = 0
    ov.slide = None
    ov.ghost = None
    ov.held_press = None
    ov.finished_at = None
    ov._input_ok = True
    ov.recording = False
    ov.key_down.clear()
    ov.held_mods = []
    ov._prev = {}
    ov._prev_mod = {}
    ov._prev_state = 0
    ov.wrong.clear()
    ov.flashes.clear()
    ov.impacts.clear()
    fake.down = set()
    return ov


def press(ov, *vks):
    fake.down = set(vks)
    ov._poll_input()


print("[1] 配置")
check("leader_hold_until_release 默认打开", hv.DEFAULT_CONFIG.get("leader_hold_until_release"), True)
check("leader_block_scale 仍在（v9.2）", hv.DEFAULT_CONFIG.get("leader_block_scale"), 1.0)

print("[2] 按下 → 进入「按住中」，光标不动、画面不跳")
ov = build()
press(ov, VK_Z)
check("进入按住中", ov.held_press is not None, True)
check("按住的是通道 0", ov.held_press[1], 0)
check("光标不动（音还没消）", ov.cursor, 0)
check("没有残影", ov.ghost, None)
check("没有整叠下落", ov.slide, None)
check("灯带闪一下（按下有反馈）", 0 in ov.flashes, True)
check("碰撞光晕也放出来", len(ov.impacts), 1)

print("[3] 长音：按住期间反复轮询也一直不消")
ov = build(song_idx=3)
press(ov, VK_Z)
for _ in range(30):                     # 模拟约 1 秒的轮询（60fps 下约 30 帧）
    ov._poll_input()
check("按住 1 秒后光标还是不动", ov.cursor, 0)
check("块还在按住中", ov.held_press is not None, True)

print("[4] 松手 → 才真正消掉")
press(ov)                               # 全部松开
check("松手后光标前进", ov.cursor, 1)
check("按住状态清空", ov.held_press, None)
check("出现缩小淡出的残影", ov.ghost is not None, True)
check("整叠往下落一层", ov.slide is not None, True)
check("残影高度 = 方块单位 × 4 拍（长音更长）",
      round(ov.ghost[3] / ov._leader_unit(), 3), 4.0)

print("[5] 开关关掉 → 退回旧行为（按下即消）")
ov = build()
ov.cfg["leader_hold_until_release"] = False
press(ov, VK_Z)
check("按下就消", ov.cursor, 1)
check("没有按住状态", ov.held_press, None)
check("照旧出现残影", ov.ghost is not None, True)

print("[6] 按住期间按错键 → 红闪，不影响手上的按住状态")
ov = build(song_idx=2)                  # 单音谱：目标永远是通道 0
press(ov, VK_Z)
press(ov, VK_Z, VK_X)                   # 手上按着 z，又按了 x
check("x 判错红闪", 1 in ov.wrong, True)
check("z 的按住状态没被打断", ov.held_press is not None and ov.held_press[1] == 0, True)
check("光标仍不动", ov.cursor, 0)
press(ov, VK_Z)
check("x 松掉也不影响", ov.held_press is not None, True)

print("[7] 「松开旧键 + 按下新键」落在同一轮询周期 → 不误判")
ov = build(song_idx=1)                  # 谱面：先 x（ch1）再 z（ch0）
press(ov, VK_X)
check("先按住 x", (ov.held_press is not None and ov.held_press[1] == 1), True)
press(ov, VK_Z)                         # 同一周期：松 x + 按 z（顺序对调也不该误判）
check("光标前进到第 2 个音", ov.cursor, 1)
check("z 顺利接上（没有红闪）", 0 in ov.wrong, False)
check("新的音在按住中", ov.held_press is not None and ov.held_press[1] == 0, True)

print("[8] 按错键不会进入「按住中」")
ov = build()
press(ov, VK_X)                         # 第 1 个音是 z 通道
check("红闪", 0 in ov.wrong or 1 in ov.wrong, True)
check("没有进入按住中", ov.held_press, None)
check("光标不动", ov.cursor, 0)

print("[9] 最后一个音也要松手才算完成")
ov = build(song_idx=2)
press(ov, VK_Z)
check("按住时还没判完成", ov.finished_at, None)
press(ov)
check("松手才置完成标记", ov.finished_at is not None, True)

print("[10] 绘制：按住中的块明显更淡，但还看得见")
ov = build()
press(ov, VK_Z)
ov.resize(760, 560)
ov.show()
ov.update()
pm = ov.grab()
ratio = pm.devicePixelRatio() or 1.0
img = pm.toImage()

unit = ov._leader_unit()
gap = 6.0
hit_y = 560.0 - float(cfg.get("hit_line_offset", 10))
x0, ch_w, _pad = ov._note_geometry()
bl = x0 + ch_w * 0.22                       # 块左边缘
br = x0 + ch_w * 0.78                       # 块右边缘
b0_bottom = hit_y - 4.0


def row_lum(img_, cy):
    """在块内横向扫一行取平均亮度。

    特意取"离块底 5px"那一行：避开中间的按键字母（深色，会盖住底色）
    和顶部那道白色高光，量到的就是底色本身 —— 只比"透不透"。
    """
    vals = []
    x = int(bl + 3)
    while x < int(br - 3):
        c = img_.pixelColor(int(x * ratio), int(cy * ratio))
        vals.append(0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        x += 2
    return sum(vals) / max(1, len(vals))


# 块 0 = 目标（按住中）；块 1 = 它上面那块（常态，同通道同色）
cy_hold = b0_bottom - 5.0
cy_norm = b0_bottom - unit - gap - 5.0
l_hold, l_norm = row_lum(img, cy_hold), row_lum(img, cy_norm)
print("     底色亮度：按住中 %.0f ｜ 常态 %.0f" % (l_hold, l_norm))
check("按住中的块明显更淡（半透明）", l_hold < l_norm - 40, True)
check("但还看得见（不像背景那么黑）", l_hold > 60, True)

# 松手后同一位置回到常态（不透明）
press(ov)
ov.ghost = None
ov.slide = None
ov.update()
img = ov.grab().toImage()
l_after = row_lum(img, cy_hold)             # 松手后第 2 块落到这一层、且不再是"按住中"
print("     松手后同位置亮度 %.0f" % l_after)
check("松手后不再是半透明", l_after > 150, True)
ov.close()

print("[11] 跟随模式不受影响")
ov = build(mode="follow")
press(ov, VK_Z)
check("跟随模式不会进入经典那套按住状态", ov.held_press, None)
ov2 = build(song_idx=2, mode="follow")
ov2.follow_state = "playing"
ov2.follow_t0 = time.monotonic()
ov2._follow_press = lambda ch, now: None         # 只看松手分支不炸
ov2.key_down[0] = True
fake.down = {VK_Z}
ov2._poll_input()
fake.down = set()
ov2._poll_input()
check("跟随模式松手不抛异常", ov2.held_press, None)

print("[12] 重来 / 换曲谱会清掉按住状态")
ov = build()
press(ov, VK_Z)
check("先进入按住中", ov.held_press is not None, True)
ov.reset_playback()
check("reset_playback 清干净", (ov.held_press, ov.cursor), (None, 0))
press(ov, VK_Z)
ov.select_song(1)
check("换曲谱也清干净", (ov.held_press, ov.cursor), (None, 0))

print("[13] 按住 + 切修饰键（v9.3 的切音高算新音）→ 前一个先落地")
ov = build()
press(ov, VK_Z)
check("先按住 z（第 1 个音）", ov.held_press is not None, True)
press(ov, VK_Z, VK_MID)
check("切中键 → 第 1 个音落地、第 2 个音接上",
      (ov.cursor, ov.held_press is not None), (1, True))
press(ov, VK_Z, VK_MID, VK_L)
check("再切左键 → 第 2 个落地、第 3 个接上", ov.cursor, 2)
press(ov)
check("松手 → 结束", ov.finished_at is not None, True)

print("[14] 关掉输入读取时一切照旧（不炸）")
ov = build()
ov._input_ok = False
ov._poll_input()
check("不读输入时直接返回", (ov.cursor, ov.held_press), (0, None))

hv.user32 = real_u32

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
