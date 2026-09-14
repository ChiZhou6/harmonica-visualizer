# -*- coding: utf-8 -*-
"""面板截图：4 首（用户当前状态）vs 30 首（列表爆满 + 滚动条）"""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:/AI/DF Harmonica/harmonica-visualizer")
import harmonica_visualizer as hv
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont
from PySide6.QtCore import Qt

app = QApplication(sys.argv)
cfg = hv.load_config()

def make(n, h=620):
    names = ["See You Again", "小星星", "欢乐颂", "父亲（筷子兄弟）", "音域与变调练习"] + \
            ["我的曲谱%d" % i for i in range(1, n - 4)]
    songs = [hv.Song(t, 90, [(0.0, 1.0, i % 8, i % 4)]) for i, t in enumerate(names[:n])]
    ov = hv.Overlay(cfg, songs)
    p = hv.PanelWindow(ov)
    ov.panel = p
    p.song_scroll = 0
    p.resize(168, h)
    pm = p.grab()
    return pm

for n, h in ((4, 620), (30, 620), (30, 380)):
    pm = make(n, h)
    # 拼到灰底 + 标题
    out = QPixmap(pm.width() + 220, pm.height() + 24)
    out.fill(QColor(90, 90, 95))
    pt = QPainter(out)
    pt.setPen(QColor(255, 255, 255))
    pt.setFont(QFont("Microsoft YaHei UI", 10))
    pt.drawText(6, 17, "%d 首曲谱 / 面板高 %d" % (n, h))
    pt.drawPixmap(14, 24, pm)
    pt.end()
    out.save(r"D:/AI/DF Harmonica/harmonica-visualizer/_tests/_shot_panel_%d_%d.png" % (n, h))
    print("saved", n, h)
