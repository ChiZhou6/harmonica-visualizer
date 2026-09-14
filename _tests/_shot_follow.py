# -*- coding: utf-8 -*-
"""渲染跟随演奏模式的三种状态（待命 / 倒计时 / 演奏中），拼成一张演示图。

输出：D:/AI/DF Harmonica/跟随演奏模式.png
"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:/AI/DF Harmonica/harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402
from PySide6.QtWidgets import QApplication                       # noqa: E402
from PySide6.QtGui import (QPainter, QPixmap, QColor, QFont, QPen,   # noqa: E402
                           QFontDatabase)
from PySide6.QtCore import Qt, QRectF                             # noqa: E402

app = QApplication(sys.argv)

for _p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"):
    if os.path.exists(_p):
        QFontDatabase.addApplicationFont(_p)

SAMPLE = """演示曲 — 三角洲口琴谱
BPM 120 · 12 音符 · 3 小节 · 移调 0

键位标记：+ 升调（鼠标右键） / - 降调（鼠标左键） / # 半音（鼠标中键）

小节   1 (4/4)
  简谱  1 2 3 4
  键位  Z X C V
  节奏  4 4 4 4

小节   2 (4/4)
  简谱  5 6 7 1'
  键位  B N M ,
  节奏  2 2 2 2

小节   3 (4/4)
  简谱  #2 #6. 5.
  键位  X# N-# B-
  节奏  4  4  4
"""

cfg = hv.load_config()
song = hv.parse_dfh_tab(SAMPLE)
songs = [song]


def render(state, t0_offset=None, countdown_remain=None):
    ov = hv.Overlay(cfg, songs)
    ov.mode = "follow"
    ov.follow_state = state
    if state == "countdown":
        ov.countdown_deadline = time.monotonic() + (countdown_remain or 2.4)
    elif state == "playing" and t0_offset is not None:
        first = ov.song.notes[0][0] * ov._follow_spb()
        ov.follow_t0 = time.monotonic() - first - t0_offset
        # 前两个音已经"命中"，让画面有消除感
        ov.follow_next = 2
    ov.resize(760, 560)
    ov.show()
    pm = ov.grab()
    ov.close()
    return pm


print("渲染 idle（待命）…")
pm_idle = render("idle")
print("渲染 countdown（倒计时）…")
pm_cd = render("countdown", countdown_remain=2.4)
print("渲染 playing（演奏中）…")
pm_play = render("playing", t0_offset=3.5)

W, H = pm_idle.width(), pm_idle.height()
gap = 14
canvas = QPixmap(W * 3 + gap * 2, H + 46)
canvas.fill(QColor(40, 40, 44))
p = QPainter(canvas)
p.setRenderHint(QPainter.Antialiasing)
for i, (pm, label) in enumerate([(pm_idle, "① 待命（点第一个音开始）"),
                                 (pm_cd, "② 倒计时 3 秒"),
                                 (pm_play, "③ 演奏中（音符按时值下落）")]):
    x = i * (W + gap)
    p.drawPixmap(x, 46, pm)
    p.setPen(QColor(255, 255, 255, 235))
    p.setFont(QFont("Microsoft YaHei UI", 11, QFont.DemiBold))
    p.drawText(QRectF(x, 10, W, 30), Qt.AlignCenter, label)
p.end()

out = r"D:/AI/DF Harmonica/跟随演奏模式.png"
canvas.save(out, "PNG")
print("saved:", out, canvas.width(), "x", canvas.height())
