# -*- coding: utf-8 -*-
"""小面板（v9.2 双面）离屏测试

小面板紧贴主面板下方、宽度跟着主面板走、屏幕下方放不下时挂到上方；
· 跟随模式（且没在录音）→ 显示「跟随倍速」，两个按钮点的是倍速
· 经典 / 录音模式        → 显示「方块长度」，两个按钮点的是块长
提示文字、按钮命中区、极端值重绘、面板穿透、接缝配色（v9.1）。
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox          # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_sub_test_")
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


class Ev:
    """极简鼠标事件替身（只需要 position()）"""

    def __init__(self, x, y):
        self._p = hv.QPointF(x, y)

    def position(self):
        return self._p


with open(os.path.join(hv.SONGS_DIR, "a.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=120\nTITLE=甲\n1 2 3\n")

cfg = hv.load_config()
ov = hv.Overlay(cfg, hv.load_songs())
panel = hv.PanelWindow(ov)
ov.panel = panel
sub = hv.SubPanel(ov)
ov.sub = sub


def rect_of(action):
    sub.grab()                      # 强制重画 → 命中区是最新的
    for r, a in sub._hit_buttons:
        if a == action:
            return r
    raise AssertionError("找不到按钮 " + action)


def click(action):
    r = rect_of(action)
    sub.mousePressEvent(Ev(r.center().x(), r.center().y()))


print("[1] 面板按钮按热键号排列（F5 → F11）")
order = [a for row in hv.PANEL_ROWS for a, _ in row]
check("按钮顺序", order, ["toggle_mode", "toggle_visible", "next_song",
                          "toggle_adjust", "toggle_play", "toggle_panel",
                          "editor", "quit"])
hk = hv.DEFAULT_CONFIG["hotkeys"]
check("第 1 个 = Shift+F5", hv.format_hotkey(hk["toggle_mode"]), "Shift+F5")
check("第 2 个 = Shift+F6", hv.format_hotkey(hk["toggle_visible"]), "Shift+F6")
check("第 3 个 = Shift+F7", hv.format_hotkey(hk["next_song"]), "Shift+F7")
check("第 4 个 = Shift+F8", hv.format_hotkey(hk["toggle_adjust"]), "Shift+F8")
check("第 5 个 = Shift+F9", hv.format_hotkey(hk["toggle_play"]), "Shift+F9")
check("第 6 个 = Shift+F10", hv.format_hotkey(hk["toggle_panel"]), "Shift+F10")
check("第 7 个 = Shift+F11", hv.format_hotkey(hk["editor"]), "Shift+F11")
check("最后一个 = 退出", hv.format_hotkey(hk["quit"]), "Ctrl+Alt+Q")

print("[2] 小面板几何：紧贴主面板下方、宽度一致")
ov.cfg["panel_width"] = 168
ov.resize(880, 563)
ov.move(100, 100)
ov.sync_panel()
check("宽度 = 主面板宽度", sub.width(), panel.width())
check("宽度 = panel_width", sub.width(), 168)
check("高度固定", sub.height(), hv.SubPanel.HEIGHT)
check("左边缘对齐主面板", sub.x(), ov.x())
check("紧贴主面板下方", sub.y(), ov.y() + ov.height())

print("[3] 改 panel_width 后跟着变")
ov.cfg["panel_width"] = 210
ov.sync_panel()
check("宽度跟着变", sub.width(), 210)
check("主面板 / 小面板仍然一致", sub.width(), panel.width())
ov.cfg["panel_width"] = 168
ov.sync_panel()

print("[4] 主面板贴到屏幕底边 → 小面板挂到上方，且不出屏")
scr = QApplication.primaryScreen().availableGeometry()
ov.resize(880, 400)
ov.move(100, scr.bottom() - 200)          # 主面板底边已超出屏幕
ov.sync_panel()
check("挂到主面板上方", sub.y(), ov.y() - hv.SubPanel.HEIGHT)
check("没跑出屏幕顶部", sub.y() >= scr.top(), True)
check("底边没超出屏幕", sub.y() + sub.height() <= scr.bottom(), True)

print("[5] 双面：跟随模式显示倍速，经典 / 录音模式显示方块长度")
ov.resize(880, 563)
ov.move(100, 100)
ov.sync_panel()
sub.show()

ov.mode = "follow"
ov.recording = False
v = sub._view()
check("跟随模式 → kind", v["kind"], "rate")
check("跟随模式 → 标题", v["title"], "跟随倍速")
check("跟随模式 → 两个按钮", v["actions"], ("rate_down", "rate_up"))
check("跟随模式 → 按钮文字", v["labels"], ("− 减慢", "＋ 加快"))
check("跟随模式 → 提示", sub._hint_text(), "Shift+↓ 减慢 · Shift+↑ 加快")

ov.mode = "classic"
v = sub._view()
check("经典模式 → kind", v["kind"], "block")
check("经典模式 → 标题", v["title"], "方块长度")
check("经典模式 → 两个按钮", v["actions"], ("block_down", "block_up"))
check("经典模式 → 按钮文字", v["labels"], ("− 缩短", "＋ 拉长"))
check("经典模式 → 提示", sub._hint_text(), "Shift+↓ 缩短 · Shift+↑ 拉长")

ov.mode = "follow"
ov.recording = True
check("录音时即使 mode=follow 也算经典（画的是录音视图）",
      sub._view()["kind"], "block")
ov.recording = False

print("[6] 点按钮：按当前模式改对应参数")
ov.mode = "follow"
ov.cfg["follow_rate"] = 1.0
ov.cfg["leader_block_scale"] = 1.0
click("rate_up")
check("跟随模式点 ＋ → 倍速 110%", ov.cfg["follow_rate"], 1.1)
check("同时块长没被动过", ov.cfg["leader_block_scale"], 1.0)
click("rate_down")
check("跟随模式点 − → 倍速 100%", ov.cfg["follow_rate"], 1.0)

ov.mode = "classic"
click("block_up")
check("经典模式点 ＋ → 块长 110%", ov.cfg["leader_block_scale"], 1.1)
check("同时倍速没被动过", ov.cfg["follow_rate"], 1.0)
click("block_down")
check("经典模式点 − → 块长 100%", ov.cfg["leader_block_scale"], 1.0)
check("块长写进了 config.json", hv.load_config().get("leader_block_scale"), 1.0)

ov.recording = True
click("block_up")
check("录音模式点 ＋ → 块长 110%", ov.cfg["leader_block_scale"], 1.1)
ov.recording = False
ov.cfg["leader_block_scale"] = 1.0

print("[7] 悬停高亮")
sub.grab()
r_up = rect_of("block_up")
sub.mouseMoveEvent(Ev(r_up.center().x(), r_up.center().y()))
check("悬停 block_up", sub.hover_action, "block_up")
sub.mouseMoveEvent(Ev(84.0, 84.0))        # 空白处
check("移开 → 取消高亮", sub.hover_action, None)

print("[8] 极端值也能画（进度条不越界）")
for kind in ("rate", "block"):
    ov.mode = "follow" if kind == "rate" else "classic"
    key = "follow_rate" if kind == "rate" else "leader_block_scale"
    lo, hi = (0.2, 2.0) if kind == "rate" else (0.5, 2.0)
    for val in (lo, (lo + hi) / 2, hi):
        ov.cfg[key] = val
        pm = sub.grab()
        check("%s %.2f 重绘正常" % (kind, val), pm.width(), 168)
ov.cfg["follow_rate"] = 1.0
ov.cfg["leader_block_scale"] = 1.0

print("[9] 主面板被压窄时也不会崩")
ov.resize(420, 400)
ov.sync_panel()
check("窄面板截图非空", sub.grab().width(), sub.width())
ov.resize(880, 563)
ov.sync_panel()

print("[10] 面板穿透时小面板一起穿透（不抛异常）")
ov.cfg["panel_interactive"] = False
sub.apply_style()
panel.apply_style()
ov.cfg["panel_interactive"] = True
sub.apply_style()
panel.apply_style()
check("穿透切换无异常", True, True)

print("[11] 接缝 / 配色修复（v9.1）")
from PySide6.QtGui import QColor, QImage                       # noqa: E402

BASE = QColor(10, 20, 30)


def render_on(widget):
    """把窗口画到一张预填色的图上。

    没被画到的地方会保留预填色 → 于是"该画却没画"的地方能被抓出来
    （小面板最右 12px 之前就是整条漏空的）。
    """
    img = QImage(widget.width(), widget.height(), QImage.Format_ARGB32)
    img.fill(BASE)
    widget.render(img)
    return img


def rgb(img, x, y):
    return img.pixelColor(int(x), int(y)).getRgb()[:3]


ov.cfg["bg_alpha"] = 150
sub_img = render_on(sub)
check("小面板最右 12px 画上了底色（不再漏空）",
      rgb(sub_img, sub.width() - 6, 4), rgb(sub_img, sub.width() / 2, 4))
check("小面板右边不是空的（没露桌面）",
      rgb(sub_img, sub.width() - 6, 4) != (10, 20, 30), True)

pan_img = render_on(panel)
blank = [rgb(pan_img, x, 6) for x in range(16, int(panel.width()) - 5, 8)]
check("主面板不再自带底色（顶部整条留白都是透明的）",
      all(c == (10, 20, 30) for c in blank), True)
dev = max(sum(abs(a - b) for a, b in zip(rgb(pan_img, x, panel.height() // 2),
                                         (10, 20, 30)))
          for x in range(int(panel.width()) - 3, int(panel.width())))
check("右侧分隔线还在（只是更淡）", dev > 5, True)

# 小面板贴在下方时：主面板左下角、小面板左上角都要补成直角，
# 否则两个窗口之间会露出一个约 12×12 的桌面缺口（同款"像没拼接好"）
ov_img = render_on(ov)
check("主面板左下角补成直角（与小面板接上）",
      rgb(ov_img, 3, ov.height() - 3) != (10, 20, 30), True)
check("小面板左上角补成直角（与主面板接上）",
      rgb(sub_img, 3, 3) != (10, 20, 30), True)

sub.close()
panel.close()
ov.close()

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
