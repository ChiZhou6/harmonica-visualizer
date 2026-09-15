# -*- coding: utf-8 -*-
"""V9 倍速小面板 离屏测试

小面板紧贴主面板下方、宽度跟着主面板走、屏幕下方放不下时挂到上方、
按钮点击能改倍速、窄面板也能画、面板穿透同步。
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

print("[5] 绘制与按钮命中区")
ov.resize(880, 563)
ov.move(100, 100)
ov.sync_panel()
sub.show()
pm = sub.grab()
check("截图非空", (pm.width(), pm.height()), (168, hv.SubPanel.HEIGHT))
check("有 ± 两个按钮", len(sub._hit_buttons), 2)
check("按钮动作名", [a for _, a in sub._hit_buttons], ["rate_down", "rate_up"])
check("按钮都在面板内", all(r.right() <= 168 and r.bottom() <= hv.SubPanel.HEIGHT
                            for r, _ in sub._hit_buttons), True)

print("[6] 点 ＋ / − 改倍速")
ov.cfg["follow_rate"] = 1.0
r_up = [r for r, a in sub._hit_buttons if a == "rate_up"][0]
r_dn = [r for r, a in sub._hit_buttons if a == "rate_down"][0]
sub.mousePressEvent(Ev(r_up.center().x(), r_up.center().y()))
check("点 ＋ → 110%", ov.cfg["follow_rate"], 1.1)
sub.mousePressEvent(Ev(r_up.center().x(), r_up.center().y()))
check("再点 → 120%", ov.cfg["follow_rate"], 1.2)
sub.mousePressEvent(Ev(r_dn.center().x(), r_dn.center().y()))
check("点 − → 110%", ov.cfg["follow_rate"], 1.1)
check("倍速写进了 config.json", hv.load_config().get("follow_rate"), 1.1)

print("[7] 悬停高亮")
sub.mouseMoveEvent(Ev(r_up.center().x(), r_up.center().y()))
check("悬停 rate_up", sub.hover_action, "rate_up")
sub.mouseMoveEvent(Ev(84.0, 84.0))        # 空白处
check("移开 → 取消高亮", sub.hover_action, None)

print("[8] 极端倍速也能画（进度条不越界）")
for rate in (0.2, 0.5, 1.0, 1.7, 2.0):
    ov.cfg["follow_rate"] = rate
    pm = sub.grab()
    check("倍速 %d%% 重绘正常" % round(rate * 100), pm.width(), 168)

print("[9] 主面板被压窄时也不会崩")
ov.resize(420, 400)
ov.sync_panel()
pm = sub.grab()
check("窄面板截图非空", pm.width(), sub.width())
ov.resize(880, 563)
ov.sync_panel()

print("[10] 跟随 / 经典模式切换都能画（跟随模式下才高亮）")
ov.mode = "follow"
pm1 = sub.grab()
ov.mode = "classic"
pm2 = sub.grab()
check("两种模式都画得出来",
      (pm1.width(), pm2.width()), (168, 168))

print("[11] 面板穿透时小面板一起穿透（不抛异常）")
ov.cfg["panel_interactive"] = False
sub.apply_style()
panel.apply_style()
ov.cfg["panel_interactive"] = True
sub.apply_style()
panel.apply_style()
check("穿透切换无异常", True, True)

sub.close()
panel.close()
ov.close()

print()
print("结果:", "全部通过 ✓" if ok else "有失败 ✗")
sys.exit(0 if ok else 1)
