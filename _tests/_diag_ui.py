# -*- coding: utf-8 -*-
"""界面接缝诊断（真机）：把三个窗口摆到真实屏幕上，抓屏量像素。

排查"面板与音符区颜色不一样 / 接缝处有竖条 / 某块没画满"这类问题的第一件工具：
  1) 先铺一块浅色背景板（模拟用户的浅色桌面），再建 Overlay / Panel / Sub 三个窗口
  2) 1.8 秒后抓全屏，沿水平 + 垂直线扫描，打印颜色变化点
  3) 同时存一张 _diag_real.png，方便放大看

⚠️ 逻辑坐标必须乘 devicePixelRatio（本机 3840x2160 @144dpi → dpr 1.5），
   否则量到的是错位置（第一版就踩了这个坑）。
⚠️ 会真的在屏幕上弹出窗口 1.8 秒。跑法：python _diag_ui.py
"""

import ctypes
import sys

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                       # noqa: E402
from PySide6.QtCore import QTimer                       # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget     # noqa: E402


class Bg(QWidget):
    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(245, 245, 245))


cfg = hv.load_config()
hv.apply_songs_dir(cfg)
hv.ensure_data_files()
songs = hv.load_songs()

app = QApplication(sys.argv)
bg = Bg()
bg.setGeometry(0, 0, 1500, 1000)
bg.show()

ov = hv.Overlay(cfg, songs)
ov.setGeometry(300, 200, 900, 640)
panel = hv.PanelWindow(ov)
ov.panel = panel
sub = hv.SubPanel(ov)
ov.sub = sub
ov.sync_panel()
ov.show()
panel.show()
panel.raise_()
sub.show()
sub.raise_()


def dump():
    print("=" * 66)
    print("overlay.geometry   =", ov.geometry())
    print("panel.geometry     =", panel.geometry())
    print("sub.geometry       =", sub.geometry())
    print("overlay.width()    =", ov.width(), " _panel_width() =", ov._panel_width())
    print("panel.width()      =", panel.width(), " sub.width() =", sub.width())
    print("devicePixelRatio   =", ov.devicePixelRatioF(),
          " screen =", ov.screen().geometry(), ov.screen().devicePixelRatio())
    print("panel 右边缘 x =", panel.x() + panel.width(),
          " sub 右边缘 x =", sub.x() + sub.width())
    print("=" * 66)

    from PIL import ImageGrab
    img = ImageGrab.grab()
    print("屏幕截图尺寸 =", img.size)

    S = ov.devicePixelRatioF()        # 逻辑 → 物理

    def scan_h(y, x0, x1, tag):
        row = []
        prev = None
        for x in range(int(x0 * S), int(x1 * S)):
            c = img.getpixel((x, int(y * S)))[:3]
            if prev is None or sum(abs(a - b) for a, b in zip(c, prev)) > 6:
                row.append("%.0f%s" % (x / S, c))
                prev = c
        print("%s y=%.0f: %s" % (tag, y, " | ".join(row)))

    def scan_v(x, y0, y1, tag):
        row = []
        prev = None
        for y in range(int(y0 * S), int(y1 * S)):
            c = img.getpixel((int(x * S), y))[:3]
            if prev is None or sum(abs(a - b) for a, b in zip(c, prev)) > 6:
                row.append("%.0f%s" % (y / S, c))
                prev = c
        print("%s x=%.0f: %s" % (tag, x, " | ".join(row)))

    pr = panel.x() + panel.width()
    print("面板右边缘(逻辑) =", pr, " 叠加层右边缘 =", ov.x() + ov.width())
    scan_h(ov.y() + 300, pr - 20, pr + 20, "[接缝·水平]")
    scan_v(ov.x() + 30, ov.y() + 10, ov.y() + ov.height() + 130, "[左侧·垂直]")
    scan_v(ov.x() + panel.width() - 8,
           ov.y() + ov.height() - 20, ov.y() + ov.height() + 110, "[主面板↔小面板]")
    img.save(r"D:\AI\DF Harmonica\_diag_real.png")
    print("已存 _diag_real.png")
    app.quit()


QTimer.singleShot(1800, dump)
app.exec()
