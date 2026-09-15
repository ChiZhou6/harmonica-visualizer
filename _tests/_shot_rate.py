# -*- coding: utf-8 -*-
"""V9 效果图：跟随倍速 —— 小面板三态 + 倍速下落对比"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                       # noqa: E402
from PySide6.QtWidgets import QApplication              # noqa: E402
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QFontDatabase   # noqa: E402
from PySide6.QtCore import Qt, QRectF                   # noqa: E402

app = QApplication(sys.argv)
for _p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"):
    if os.path.exists(_p):
        QFontDatabase.addApplicationFont(_p)

cfg = hv.load_config()
song = hv.parse_song("BPM=120\nTITLE=倍速演示\n1 2 3 4 5 6 7 8 1 2 3 4\n", "倍速演示")
ov = hv.Overlay(cfg, [song])
cfg["follow_lead"] = 2.0
cfg["follow_rate"] = 1.0
cfg["bg_alpha"] = 255          # 出图用：背景拉成不透明，否则离屏 grab 会把透明区填白
ov._input_ok = True
ov.mode = "follow"
ov.resize(760, 560)

sub = hv.SubPanel(ov)
ov.sub = sub
sub.resize(168, hv.SubPanel.HEIGHT)
sub.show()

LEAD = 2.0


def panel_pm(rate):
    ov.cfg["follow_rate"] = rate
    sub.update()
    return sub.grab()


def follow_pm(rate, play):
    """让此刻的播放时间正好 = play（play = (now - t0) * rate - lead）"""
    ov.cfg["follow_rate"] = rate
    ov.follow_state = "playing"
    ov.follow_t0 = hv.time.monotonic() - (play + LEAD) / rate
    ov.follow_next = 0
    ov.follow_hold = None
    ov.follow_missed.clear()
    ov.follow_fade.clear()
    ov.impacts = []
    ov.show()
    return ov.grab()


# ---- 图 A：小面板三态 ----
rates = [(0.2, "20%（最慢）"), (1.0, "100%（原速）"), (2.0, "200%（最快）")]
pmsA = [panel_pm(r) for r, _ in rates]
wA, hA = pmsA[0].width(), pmsA[0].height()
GAP, TOP = 20, 54
cA = QPixmap(wA * 3 + GAP * 2 + 40, hA + TOP + 40)
cA.fill(QColor(34, 32, 30))
p = QPainter(cA)
p.setPen(QColor(255, 255, 255, 235))
p.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
p.drawText(QRectF(0, 10, cA.width(), 30), Qt.AlignCenter,
           "V9：主面板下方新增「跟随倍速」小面板（Shift+↑ / Shift+↓，或直接点按钮）")
for i, (pm, (_, tag)) in enumerate(zip(pmsA, rates)):
    x = 20 + i * (wA + GAP)
    p.drawPixmap(x, TOP, pm)
    p.setPen(QColor(255, 220, 140, 245))
    p.setFont(QFont("Microsoft YaHei UI", 10))
    p.drawText(QRectF(x, TOP + hA + 6, wA, 24), Qt.AlignCenter, tag)
p.end()
outA = r"D:\AI\DF Harmonica\跟随倍速_面板.png"
cA.save(outA, "PNG")
print("saved:", outA, cA.width(), "x", cA.height())

# ---- 图 B：同一时刻 100% vs 200% 的下落对比 ----
pmsB = [follow_pm(1.0, 1.0), follow_pm(2.0, 2.0)]
wB, hB = pmsB[0].width(), pmsB[0].height()
cB = QPixmap(wB * 2 + GAP, hB + TOP + 40)
cB.fill(QColor(34, 32, 30))
p = QPainter(cB)
p.setPen(QColor(255, 255, 255, 235))
p.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
p.drawText(QRectF(0, 10, cB.width(), 30), Qt.AlignCenter,
           "同一时刻对比：200% 时谱面已经往下走了两倍 —— 块间距不变，只是整体更快")
tags = ["100%：真实 1 秒后", "200%：同一时刻，已经走得更远"]
for i, (pm, tag) in enumerate(zip(pmsB, tags)):
    x = i * (wB + GAP)
    p.drawPixmap(x, TOP, pm)
    p.setPen(QColor(255, 220, 140, 245))
    p.setFont(QFont("Microsoft YaHei UI", 10))
    p.drawText(QRectF(x, TOP + hB + 6, wB, 24), Qt.AlignCenter, tag)
p.end()
outB = r"D:\AI\DF Harmonica\跟随倍速_下落对比.png"
cB.save(outB, "PNG")
print("saved:", outB, cB.width(), "x", cB.height())
