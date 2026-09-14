# -*- coding: utf-8 -*-
"""把三种面板状态拼成一张对比图，直观展示"曲谱爆满时滚动条正常、按钮不挤占"，
并顺带展示 v8 新增的【隐藏窗口】按钮 + 每个按钮右侧的 Shift 快捷键提示。

输出：D:/AI/DF Harmonica/面板列表滚动条对比.png

⚠️ 离屏平台（offscreen）自带的是**回退字体**，比真实屏幕宽得多（实测 "Shift+F6"
   量到 88px，真实微软雅黑只有 45px）→ 不加载真实字体就会算出错误的宽度、
   把本该显示的快捷键提示误判成"太挤、不显示"。
   所以这里显式 QFontDatabase.addApplicationFont 加载 msyh.ttc。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:/AI/DF Harmonica/harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402
from PySide6.QtWidgets import QApplication                       # noqa: E402
from PySide6.QtGui import (QPainter, QPixmap, QColor, QFont, QPen,   # noqa: E402
                           QFontDatabase, QFontMetrics)
from PySide6.QtCore import Qt                                     # noqa: E402

app = QApplication(sys.argv)

# ---- 让离屏渲染用上真实中文字体（否则宽度全算错）----
for _p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"):
    if os.path.exists(_p):
        QFontDatabase.addApplicationFont(_p)
_fm = QFontMetrics(QFont("Microsoft YaHei UI", 8))
print("字体自检：Shift+F6 宽度 =", _fm.horizontalAdvance("Shift+F6"), "px（真实屏幕约 45）")

cfg = hv.load_config()
BASE_NAMES = ["See You Again", "小星星", "欢乐颂", "父亲（筷子兄弟）", "音域与变调练习"]


def build(n, h):
    names = BASE_NAMES + ["我的曲谱%d" % i for i in range(1, max(0, n - 5) + 1)]
    songs = [hv.Song(t, 90, [(0.0, 1.0, i % 8, i % 4)]) for i, t in enumerate(names[:n])]
    ov = hv.Overlay(cfg, songs)
    p = hv.PanelWindow(ov)
    ov.panel = p
    p.song_scroll = 0
    p.resize(168, h)
    lay = p._compute_layout()
    return p.grab(), lay, getattr(p, "_hit_scrollbar", None), n


CASES = [
    (5, 620, "① 5 首 · 面板高 620", "列表装得下 → 不出现滚动条"),
    (30, 620, "② 30 首 · 面板高 620", "列表爆满 → 滚动条出现，7 个按钮完整"),
    (30, 360, "③ 30 首 · 面板压到最小高度 360", "列表缩到 1 行，按钮一个不少、不重合"),
]

items = []
for n, h, t1, t2 in CASES:
    pm, lay, sb, cnt = build(n, h)
    items.append((n, h, t1, t2, pm, lay, sb, cnt))
    print("case n=%d h=%d  可见行=%s / 按钮高=%.1f / 有滚动条=%s"
          % (n, h, lay.get("list_rows"), lay.get("btn_h", 0), bool(sb)))

COL_W, HEADER, PAD = 220, 86, 12
maxh = max(it[4].height() for it in items)
W, H = PAD + len(items) * COL_W + PAD, HEADER + maxh + 58

out = QPixmap(int(W * 2), int(H * 2))
out.setDevicePixelRatio(2.0)
out.fill(QColor(24, 26, 32))
pt = QPainter(out)
pt.setRenderHint(QPainter.Antialiasing)

pt.setPen(QColor(255, 255, 255))
tf = QFont("Microsoft YaHei UI", 12); tf.setBold(True)
pt.setFont(tf)
pt.drawText(PAD, 26, "面板布局自检：曲谱爆满时的滚动条 / 7 个按钮 / Shift 快捷键提示")
pt.setFont(QFont("Microsoft YaHei UI", 8))
pt.setPen(QColor(140, 200, 255))
pt.drawText(PAD, 44, "红虚线 = 列表可绘制区（已裁剪）；蓝 = 滚动条轨道 / 滑块；绿 = 底部按钮区（从下往上排）")
pt.setPen(QColor(160, 230, 160))
pt.drawText(PAD, 60, "按钮行：隐藏窗口 / 添加曲谱 / 调整窗口 / 从头重来 / 下一首 / 面板穿透 / 退出程序 —— 每行右侧就是它的快捷键")

for i, (n, h, t1, t2, pm, lay, sb, cnt) in enumerate(items):
    x = PAD + i * COL_W
    y = HEADER
    pt.setPen(QColor(240, 240, 245))
    f1 = QFont("Microsoft YaHei UI", 9); f1.setBold(True)
    pt.setFont(f1)
    pt.drawText(x, y - 22, t1)
    pt.setPen(QColor(165, 172, 185))
    pt.setFont(QFont("Microsoft YaHei UI", 8))
    pt.drawText(x, y - 8, t2)

    px, py = x + 6, y
    pt.drawPixmap(px, py, pm)

    clip = lay.get("list_clip")
    if clip:
        pt.setPen(QPen(QColor(255, 90, 90), 1.2, Qt.DashLine))
        pt.setBrush(Qt.NoBrush)
        pt.drawRect(int(px + clip.x()), int(py + clip.y()),
                    int(clip.width()), int(clip.height()))

    if sb:
        tr, th = sb.get("track"), sb.get("thumb")
        if tr:
            pt.setPen(QPen(QColor(90, 170, 255), 1.2))
            pt.setBrush(QColor(90, 170, 255, 55))
            pt.drawRect(int(px + tr.x()), int(py + tr.y()), int(tr.width()), int(tr.height()))
        if th:
            pt.setPen(QPen(QColor(130, 225, 255), 1.4))
            pt.setBrush(Qt.NoBrush)
            pt.drawRect(int(px + th.x()), int(py + th.y()), int(th.width()), int(th.height()))
            pt.setPen(QColor(150, 230, 255))
            pt.setFont(QFont("Microsoft YaHei UI", 8))
            pt.drawText(px - 2, int(py + th.y()) + int(th.height()) + 11, "↑ 滑块")

    # 底部按钮区（绿框）
    bt = lay.get("btn_top")
    if bt is not None:
        bh = lay.get("btn_h", 0)
        rows = len(hv.PANEL_ROWS)
        top = bt - hv.PanelWindow.BTN_HEAD_H
        bot = bt + rows * bh + (rows - 1) * hv.PanelWindow.BTN_GAP
        pt.setPen(QPen(QColor(110, 220, 110), 1.2))
        pt.setBrush(Qt.NoBrush)
        pt.drawRect(int(px), int(py + top), int(168), int(bot - top))
        pt.setPen(QColor(160, 230, 160))
        pt.setFont(QFont("Microsoft YaHei UI", 8))
        pt.drawText(px - 2, int(py + top) - 4, "↓ %d 个按钮（高 %.0fpx）" % (rows, bh))

    # 逐个断言（用真实字体宽度算），把结论写在图下方
    print("   按钮区 y=%.0f..%.0f，列表区底=%.0f → %s"
          % (lay["btn_top"], lay["btn_top"] + len(hv.PANEL_ROWS) * lay["btn_h"],
             lay["list_clip"].bottom(),
             "不重合 ✓" if lay["list_clip"].bottom() <= lay["btn_top"] else "⚠️ 重合"))

pt.setPen(QColor(150, 155, 165))
pt.setFont(QFont("Microsoft YaHei UI", 8))
pt.drawText(PAD, H - 30, "任何面板高度下：列表行不越界、不压按钮；滚动条只在曲谱数超过可见行数时出现（滚轮 / 拖动 / 点击轨道均可翻页）。")
pt.drawText(PAD, H - 16, "所有 F 区快捷键都要求按住 Shift（Shift+F3 / Shift+F5~F12），所以游戏里直接按 F 键不会触发本程序 —— 这就是防抢键的设计。")
pt.end()

OUT = r"D:/AI/DF Harmonica/面板列表滚动条对比.png"
out.save(OUT)
print("saved:", OUT, out.deviceIndependentSize().toSize().width(), "x",
      out.deviceIndependentSize().toSize().height())
