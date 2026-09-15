# -*- coding: utf-8 -*-
"""V9 效果图：所有音都要「按住才消」（跟随演奏模式）

三帧：刚接住 → 吃掉一半 → 快吃完。
"""
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

# 曲谱：1 拍音(ch0) + 4 拍音(ch1) + 5 拍音(ch2)，BPM 120 → 1 拍 = 0.5 秒
cfg = hv.load_config()
ov = hv.Overlay(cfg, [hv.parse_song("BPM=120\nTITLE=按住演示\n1 2 - - - 3 - - - -\n", "按住演示")])
cfg["follow_lead"] = 2.0
cfg["follow_rate"] = 1.0
cfg["bg_alpha"] = 255          # 出图用：背景拉成不透明，否则离屏 grab 会把透明区填白
ov._input_ok = True
ov.resize(760, 560)

LEAD = 2.0


def frame(play, hold_idx=1, hold_start=0.5, hold_dur=4.0, impact=False):
    ov.mode = "follow"
    ov.follow_state = "playing"
    ov.cfg["follow_rate"] = 1.0
    # 让此刻的播放时间正好 = play：play = (now - t0) * rate - lead
    ov.follow_t0 = hv.time.monotonic() - (play + LEAD) / 1.0
    ov.follow_next = hold_idx
    ov.follow_missed.clear()
    ov.follow_fade.clear()
    ov.follow_hold = {"idx": hold_idx, "ch": hold_idx, "state": 0,
                      "start": hold_start, "dur": hold_dur, "released": None}
    ov.key_down[hold_idx] = True
    ov.impacts = []
    if impact:
        ov.impacts.append((hv.time.monotonic(), hold_idx, 0))
    ov.show()
    return ov.grab()


plays = [(0.55, "① 刚接住：整块还在判定线上方（进度 0）"),
         (1.50, "② 按住中：判定线把它吃掉一半"),
         (2.30, "③ 快吃完：只剩贴着判定线的一小截（按满即消除）")]

raw = [frame(p, impact=(i > 0)) for i, (p, _) in enumerate(plays)]
W, H = raw[0].width(), raw[0].height()
CROP = 230                     # 只留判定线附近，看清楚"被吞进去"的过程
pms = [pm.copy(0, CROP, W, H - CROP) for pm in raw]
H = H - CROP
GAP, TOP = 16, 56
canvas = QPixmap(W * 3 + GAP * 2, H + TOP + 38)
canvas.fill(QColor(34, 32, 30))
p = QPainter(canvas)
p.setPen(QColor(255, 255, 255, 235))
p.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
p.drawText(QRectF(0, 10, canvas.width(), 32), Qt.AlignCenter,
           "V9：跟随模式下每个音都要「按住才消」—— 按下只算接住，按满这个音的时值才吃掉")
p.setFont(QFont("Microsoft YaHei UI", 10))
for i, (pm, (_, tag)) in enumerate(zip(pms, plays)):
    x = i * (W + GAP)
    p.drawPixmap(x, TOP, pm)
    p.setPen(QColor(255, 220, 140, 245))
    p.drawText(QRectF(x, TOP + H + 6, W, 24), Qt.AlignCenter, tag)
p.end()

out = r"D:\AI\DF Harmonica\长音按住消除.png"
canvas.save(out, "PNG")
print("saved:", out, canvas.width(), "x", canvas.height())
