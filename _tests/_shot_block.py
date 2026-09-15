# -*- coding: utf-8 -*-
"""v9.2 效果图：小面板"双面"+ 经典模式三种方块长度对比"""
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
song = hv.parse_song("BPM=120\nTITLE=块长演示\n1 2 3 4 5 8 - - - 7 6 5\n", "块长演示")
ov = hv.Overlay(cfg, [song])
cfg["bg_alpha"] = 255          # 出图用：背景不透明，否则离屏 grab 会把透明区填白
ov._input_ok = True
ov.resize(760, 560)
sub = hv.SubPanel(ov)
ov.sub = sub
sub.resize(168, hv.SubPanel.HEIGHT)
sub.show()
ov.show()

GAP, TOP = 20, 56


def quiet():
    """清掉随时间动画的状态 → 渲染可复现"""
    ov._toast = None
    ov.slide = None
    ov.ghost = None
    ov.impacts = []
    ov.flashes.clear()
    ov.wrong.clear()


# ---- 图 A：小面板两种形态 ----
ov.mode = "follow"
ov.recording = False
ov.cfg["follow_rate"] = 1.2
sub.update()
pmA1 = sub.grab()

ov.mode = "classic"
ov.cfg["leader_block_scale"] = 1.0
ov.cfg["follow_rate"] = 1.2
sub.update()
pmA2 = sub.grab()

ov.cfg["leader_block_scale"] = 1.6
sub.update()
pmA3 = sub.grab()

pmsA = [pmA1, pmA2, pmA3]
tagsA = ["跟随模式：显示跟随倍速", "经典模式：显示方块长度", "调大后（160%）"]
wA, hA = pmsA[0].width(), pmsA[0].height()
cA = QPixmap(wA * 3 + GAP * 2 + 40, hA + TOP + 40)
cA.fill(QColor(34, 32, 30))
p = QPainter(cA)
p.setPen(QColor(255, 255, 255, 235))
p.setFont(QFont("Microsoft YaHei UI", 10, QFont.DemiBold))
p.drawText(QRectF(0, 10, cA.width(), 30), Qt.AlignCenter,
           "小面板按模式换内容：跟随模式＝倍速，经典 / 录音模式＝方块长度")
for i, (pm, tag) in enumerate(zip(pmsA, tagsA)):
    x = 20 + i * (wA + GAP)
    p.drawPixmap(x, TOP, pm)
    p.setPen(QColor(255, 220, 140, 245))
    p.setFont(QFont("Microsoft YaHei UI", 10))
    p.drawText(QRectF(x, TOP + hA + 6, wA, 24), Qt.AlignCenter, tag)
p.end()

# ---- 图 B：经典模式三种方块长度 ----
ov.mode = "classic"
ov.recording = False
ov.cursor = 0
ov.cfg["leader_block_scale"] = 1.0

pmsB = []
for scale in (0.5, 1.0, 2.0):
    ov.cfg["leader_block_scale"] = scale
    quiet()
    pm = ov.grab()
    x0, ch_w, pad = ov._note_geometry()
    crop = pm.copy(int(x0) - 4, 0, int(ov.width() - x0) + 2, pm.height())
    pmsB.append(crop.scaled(int(crop.width() * 0.62), int(crop.height() * 0.62),
                            Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
    ov.cfg["leader_block_scale"] = 1.0

wB, hB = pmsB[0].width(), pmsB[0].height()
cB = QPixmap(wB * 3 + GAP * 2 + 40, hB + TOP + 40)
cB.fill(QColor(34, 32, 30))
p = QPainter(cB)
p.setPen(QColor(255, 255, 255, 235))
p.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
p.drawText(QRectF(0, 10, cB.width(), 30), Qt.AlignCenter,
           "经典模式方块长度：长度 = 拍数 × 单位长度，只改长短、宽度不变（长音仍按比例更长）")
for i, (pm, tag) in enumerate(zip(pmsB, ["50%（最短）", "100%（原样）", "200%（最长）"])):
    x = 20 + i * (wB + GAP)
    p.drawPixmap(x, TOP, pm)
    p.setPen(QColor(255, 220, 140, 245))
    p.setFont(QFont("Microsoft YaHei UI", 10))
    p.drawText(QRectF(x, TOP + hB + 6, wB, 24), Qt.AlignCenter, tag)
p.end()

outA = r"D:\AI\DF Harmonica\方块长度_面板.png"
outB = r"D:\AI\DF Harmonica\方块长度_三种长度对比.png"
cA.save(outA, "PNG")
cB.save(outB, "PNG")
print("saved:", outA, cA.width(), "x", cA.height())
print("saved:", outB, cB.width(), "x", cB.height())
