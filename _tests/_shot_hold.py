# -*- coding: utf-8 -*-
"""长音「按住被吃掉」效果图：接住 → 吃一半 → 快吃完（跟随演奏模式）"""
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

# 曲谱：1 拍短音 + 4 拍长音（BPM 120 → 1 拍 = 0.5 秒），直接内存构造，不落盘
cfg = hv.load_config()
ov = hv.Overlay(cfg, [hv.parse_song("BPM=120\nTITLE=长音演示\n1 2 - - -\n", "长音演示")])
cfg["follow_lead"] = 2.0
ov._input_ok = True
ov.resize(760, 560)

def frame(play, tag):
    ov.mode = "follow"
    ov.follow_state = "playing"
    ov.follow_t0 = hv.time.monotonic() - play - 2.0   # 让此刻的播放时间正好 = play
    ov.follow_next = 1                       # 第一个短音已消掉
    ov.follow_missed.clear()
    ov.follow_fade.clear()
    ov.follow_flash = None
    ov.follow_hold = {"idx": 1, "ch": 1, "state": 0,
                      "start": 0.5, "dur": 4.0, "released": None}
    ov.key_down[1] = True
    ov.impacts = []
    if play > 0.7:
        ov.impacts.append((hv.time.monotonic(), 1, 0))
    ov.show()
    pm = ov.grab()
    return pm


plays = [(0.65, "① 按住了：矩形还在，没消失"),
         (1.60, "② 按住中：判定线正在把它吃掉一半"),
         (2.30, "③ 快吃完了：只剩一小截")]

pms = [frame(p, t) for p, t in plays]

W, H = pms[0].width(), pms[0].height()
GAP, TOP = 16, 52
canvas = QPixmap(W * 3 + GAP * 2, H + TOP + 34)
canvas.fill(QColor(34, 32, 30))
p = QPainter(canvas)
p.setPen(QColor(255, 255, 255, 235))
p.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
p.drawText(QRectF(0, 10, canvas.width(), 32), Qt.AlignCenter,
           "长音（4 拍）按下后不再瞬间消失 —— 要一直按住，矩形被判定线一点点吃掉")
p.setFont(QFont("Microsoft YaHei UI", 10))
for i, (pm, (_, tag)) in enumerate(zip(pms, plays)):
    x = i * (W + GAP)
    p.drawPixmap(x, TOP, pm)
    p.setPen(QColor(255, 220, 140, 245))
    p.drawText(QRectF(x, TOP + H + 4, W, 24), Qt.AlignCenter, tag)
p.end()

out = r"D:\AI\DF Harmonica\长音按住消除.png"
canvas.save(out, "PNG")
print("saved:", out, canvas.width(), "x", canvas.height())
