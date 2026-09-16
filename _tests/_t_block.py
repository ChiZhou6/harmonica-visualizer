# -*- coding: utf-8 -*-
"""v9.2 经典模式「方块长度」离屏测试

覆盖：
  · 配置默认值 1.0、范围 50% ~ 200%、步进 10%
  · _leader_unit 随系数缩放（单位长度）
  · 块长 = 单位长度 × 拍数 → 长音永远按比例更长（跟长短音无关，是整体缩放）
  · 渲染像素：块的**宽度不变**、只有长度变
  · 热键 Shift+↑/↓ 按模式分派（跟随 → 倍速；经典 / 录音 → 方块长度）
  · 录音视图那排"已录音符"也跟着缩放
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402
from PySide6.QtGui import QColor, QImage                         # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox          # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_block_test_")
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


def near(label, got, want, tol):
    global ok
    good = abs(got - want) <= tol
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + label, "->", got,
          "" if good else ("(期望 %s ±%s)" % (want, tol)))


# `1 8 - - -`：通道 1 一个 1 拍的音 + 通道 8 一个 4 拍的长音
with open(os.path.join(hv.SONGS_DIR, "b.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=长短\n1 8 - - -\n")

cfg = hv.load_config()
ov = hv.Overlay(cfg, hv.load_songs())


def pick(title):
    for i, s in enumerate(ov.songs):
        if s.title == title:
            ov.song_idx = i
            return s
    raise AssertionError("找不到曲谱 " + title)


print("[1] 配置默认值与范围")
check("leader_block_scale 默认 1.0", hv.DEFAULT_CONFIG.get("leader_block_scale"), 1.0)
ov.cfg["leader_block_scale"] = 0.3
check("低于下限 → 夹到 0.5", ov._leader_scale(), 0.5)
ov.cfg["leader_block_scale"] = 3.0
check("高于上限 → 夹到 2.0", ov._leader_scale(), 2.0)
ov.cfg["leader_block_scale"] = "坏值"
check("坏值 → 回退 1.0", ov._leader_scale(), 1.0)
ov.cfg["leader_block_scale"] = 1.0

print("[2] change_block_scale：每次 10%，夹在 50% ~ 200%")
check("+10% → 1.1", ov.change_block_scale(0.1), 1.1)
check("-10% → 1.0", ov.change_block_scale(-0.1), 1.0)
ov.cfg["leader_block_scale"] = 0.5
check("已到下限 50% → 不再降", ov.change_block_scale(-0.1), 0.5)
ov.cfg["leader_block_scale"] = 2.0
check("已到上限 200% → 不再升", ov.change_block_scale(0.1), 2.0)
ov.change_block_scale(-5.0)
check("一次性大幅调整也夹在 0.5~2.0", 0.5 <= ov.cfg["leader_block_scale"] <= 2.0, True)
check("写进了 config.json", hv.load_config().get("leader_block_scale"),
      ov.cfg["leader_block_scale"])

print("[3] 单位长度随系数缩放（数值）")
ov.resize(880, 563)
ov.cfg["leader_block_scale"] = 1.0
u1 = ov._leader_unit()
ov.cfg["leader_block_scale"] = 2.0
u2 = ov._leader_unit()
ov.cfg["leader_block_scale"] = 0.5
u05 = ov._leader_unit()
near("200% = 100% 的两倍", u2 / u1, 2.0, 0.01)
near("50% = 100% 的一半", u05 / u1, 0.5, 0.01)
check("单位长度 = 窗口高度的 6%（上限 36px）", round(u1, 2), 33.78)

print("[4] 块长 = 单位长度 × 拍数（长音永远按比例更长）")
pick("长短")
ov.mode = "classic"
ov.cfg["leader_block_scale"] = 1.0
unit = ov._leader_unit()


def ghost_h(ch, idx):
    """按下再松开第 idx 个音（必须是它自己通道的键）→ 读出消除动画用的块高

    v9.3 起经典模式是"按住才消"：按下只进入 held_press，**松手**才生成 ghost。
    """
    ov.cursor = idx
    ov.finished_at = None
    ov.held_press = None
    ov._on_note_press(ch)
    ov._on_note_release(ch)
    h = ov.ghost[3]
    ov.ghost = None
    ov.held_press = None
    return h


h_1beat = ghost_h(0, 0)
h_4beat = ghost_h(7, 1)
near("1 拍块高 = 单位长度", h_1beat / unit, 1.0, 0.001)
near("4 拍块高 = 单位长度 × 4", h_4beat / unit, 4.0, 0.001)
near("长音 / 短音 = 4 倍", h_4beat / h_1beat, 4.0, 0.001)

ov.cfg["leader_block_scale"] = 1.5
unit15 = ov._leader_unit()
h1_15 = ghost_h(0, 0)
h4_15 = ghost_h(7, 1)
near("150%：短音块高 ×1.5", h1_15 / h_1beat, 1.5, 0.001)
near("150%：长音块高 ×1.5", h4_15 / h_4beat, 1.5, 0.001)
near("150%：长音 / 短音 仍是 4 倍（跟长短音无关）", h4_15 / h1_15, 4.0, 0.001)
check("单位长度也 ×1.5", round(unit15 / unit, 3), 1.5)
ov.cfg["leader_block_scale"] = 1.0

print("[5] 渲染像素：宽度不变，只有长度变")
BASE = QColor(10, 20, 30)


def render():
    """把叠加层画到预填色画布上。

    ⚠️ 必须先把所有随时间动画的状态清空：滑动/重影/碰撞光晕/按键闪光都是按
    time.monotonic() 算的，两次截图时刻不同 → 像素必然不一样，会误判成
    "参数没生效"。清干净后同一状态渲染两次是逐像素一致的。
    """
    ov._toast = None
    ov.slide = None
    ov.ghost = None
    ov.held_press = None        # 本测试只看"块长"，按住中的状态一律清掉
    ov.impacts.clear()
    ov.flashes.clear()
    ov.wrong.clear()
    img = QImage(ov.width(), ov.height(), QImage.Format_ARGB32)
    img.fill(BASE)
    ov.render(img)
    return img


def lum(img, x, y):
    r, g, b = img.pixelColor(int(x), int(y)).getRgb()[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def block_box(ch):
    """量该通道里那个块的包围盒（x0, x1, top, bottom），只认亮像素"""
    x0, ch_w, _ = ov._note_geometry()
    hit_y = ov.height() - float(ov.cfg.get("hit_line_offset", 10))
    img = render()
    xs0 = int(x0 + ch * ch_w + ch_w * 0.10)
    xs1 = int(x0 + ch * ch_w + ch_w * 0.90)
    ys0, ys1 = 120, int(hit_y - 8)          # 避开底部灯带
    pts = [(x, y) for y in range(ys0, ys1) for x in range(xs0, xs1)
           if lum(img, x, y) > 120]
    if not pts:
        return None
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts))


ov.cursor = 0
ov.cfg["leader_block_scale"] = 1.0
b1 = block_box(0)
ov.cfg["leader_block_scale"] = 2.0
b2 = block_box(0)
check("两种长度都画出来了", (b1 is not None, b2 is not None), (True, True))
near("宽度不变（100% vs 200%）", b2[1] - b2[0], b1[1] - b1[0], 2)
near("顶边上移 = 单位长度（1 拍音）", b1[2] - b2[2], unit, 3)
near("块变长 = 单位长度", (b2[3] - b2[2]) - (b1[3] - b1[2]), unit, 6)

print("[6] 热键 Shift+↑/↓ 按模式分派")
ov.mode = "classic"
ov.cfg["leader_block_scale"] = 1.0
ov.cfg["follow_rate"] = 1.0
ov.do_action("rate_up")
check("经典模式：Shift+↑ → 块长 110%", ov.cfg["leader_block_scale"], 1.1)
check("经典模式：倍速没被动过", ov.cfg["follow_rate"], 1.0)
ov.do_action("rate_down")
check("经典模式：Shift+↓ → 块长 100%", ov.cfg["leader_block_scale"], 1.0)

ov.mode = "follow"
ov.do_action("rate_up")
check("跟随模式：Shift+↑ → 倍速 110%", ov.cfg["follow_rate"], 1.1)
check("跟随模式：块长没被动过", ov.cfg["leader_block_scale"], 1.0)
ov.do_action("rate_down")
check("跟随模式：Shift+↓ → 倍速 100%", ov.cfg["follow_rate"], 1.0)

ov.recording = True
ov.do_action("rate_up")
check("录音模式（即使 mode=follow）：Shift+↑ → 块长 110%",
      ov.cfg["leader_block_scale"], 1.1)
check("录音模式：倍速没被动过", ov.cfg["follow_rate"], 1.0)
ov.recording = False
ov.mode = "classic"
ov.cfg["leader_block_scale"] = 1.0

print("[7] 录音视图那排「已录音符」也跟着缩放")
ov.recording = True
ov.rec_log = [(0, 0), (1, 1), (2, 2)]
ov.rec_count = 3
ov.flashes.clear()
ov._toast = None


def chip_box():
    """最右边那个录音方块（通道 3 的紫块）的包围盒"""
    img = render()
    hit_y = ov.height() - float(ov.cfg.get("hit_line_offset", 10))
    xs0, xs1 = int(ov.width() - 110), int(ov.width() - 2)
    ys0, ys1 = 200, int(hit_y - 12)          # 避开顶部提示条与底部灯带
    pts = [(x, y) for y in range(ys0, ys1) for x in range(xs0, xs1)
           if lum(img, x, y) > 120]
    if not pts:
        return None
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts))


ov.cfg["leader_block_scale"] = 1.0
c1 = chip_box()
ov.cfg["leader_block_scale"] = 2.0
c2 = chip_box()
check("两种长度都画出来了", (c1 is not None, c2 is not None), (True, True))
near("录音方块边长 ×2", (c2[3] - c2[2]) / (c1[3] - c1[2]), 2.0, 0.15)
near("顶边上移 30px（单位长度 30 → 60）", c1[2] - c2[2], 30, 3)
near("右边贴面板右缘（不越界）", c2[1], ov.width() - 8, 4)
ov.recording = False
ov.rec_log = []
ov.rec_count = 0
ov.cfg["leader_block_scale"] = 1.0

print("[8] 各档长度都能正常绘制")
for val in (0.5, 0.7, 1.0, 1.5, 2.0):
    ov.cfg["leader_block_scale"] = val
    ov.resize(880, 563)
    pm = ov.grab()
    check("块长 %d%% 重绘正常" % round(val * 100), (pm.width(), pm.height()), (880, 563))
    ov.resize(760, 420)
    check("块长 %d%% 小窗口也不崩" % round(val * 100), ov.grab().width(), 760)
    ov.resize(880, 563)
ov.cfg["leader_block_scale"] = 1.0

print("[9] 跟随模式不受方块长度影响（两边互不干扰）")
ov.resize(880, 563)
ov.mode = "follow"
ov.cfg["leader_block_scale"] = 1.0
p1 = render()
ov.cfg["leader_block_scale"] = 2.0
p2 = render()
same = all(p1.pixelColor(x, y) == p2.pixelColor(x, y)
           for x in range(0, 880, 20) for y in range(0, 563, 20))
check("跟随模式画面与块长无关（追逐时长由拍数×下落速度决定）", same, True)
ov.cfg["leader_block_scale"] = 1.0
ov.close()

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
