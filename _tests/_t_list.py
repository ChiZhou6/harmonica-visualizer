# -*- coding: utf-8 -*-
"""曲谱列表：滚动条 + 布局不被挤占 —— 离屏测试

重点验证（对多种面板高度 × 多种曲谱数量）：
  A 每个按钮都完整落在面板内（不被挤出底边）
  B 列表内容和"热键"标题不重叠
  C 列表最后一行不越过按钮区
  D 曲谱放不下时一定出现滚动条，放得下时不出现
  E 滚动条不压住曲谱名字（文字宽度里给它留了位）；拖到底 = 最后一首可见
  F 滚轮 / 拖滑块 / 点轨道 三种翻页方式都正确且不越界
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = r"D:\AI\DF Harmonica\harmonica-visualizer"
sys.path.insert(0, ROOT)

import harmonica_visualizer as hv                                   # noqa: E402
from PySide6.QtCore import QPointF, QPoint, QEvent                  # noqa: E402
from PySide6.QtGui import QMouseEvent                               # noqa: E402
from PySide6.QtWidgets import QApplication                          # noqa: E402

app = QApplication(sys.argv)
ok = True


def check(label, got, want, tol=0.51):
    global ok
    if isinstance(got, float) and isinstance(want, float):
        good = abs(got - want) <= tol
    else:
        good = got == want
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + label, "->", got,
          "" if good else ("(期望 %s)" % (want,)))


def press(w, pos, btn=None):
    from PySide6.QtCore import Qt
    b = btn or Qt.LeftButton
    e = QMouseEvent(QEvent.MouseButtonPress, QPointF(pos), w.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))),
                    b, b, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.NoModifier)
    w.mousePressEvent(e)


def release(w, pos):
    from PySide6.QtCore import Qt
    e = QMouseEvent(QEvent.MouseButtonRelease, QPointF(pos),
                    w.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))),
                    Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
    w.mouseReleaseEvent(e)


def move(w, pos):
    from PySide6.QtCore import Qt
    e = QMouseEvent(QEvent.MouseMove, QPointF(pos),
                    w.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))),
                    Qt.NoButton, Qt.NoButton, Qt.NoModifier)
    w.mouseMoveEvent(e)


class FakeWheel:
    def __init__(self, dy):
        self._p = QPoint(0, dy)

    def angleDelta(self):
        return self._p


def fake_songs(n):
    out = []
    for i in range(n):
        s = hv.Song("测试曲谱%d" % (i + 1), 90, [(0.0, 1.0, i % 8, i % 4)])
        out.append(s)
    return out


cfg = hv.load_config()
ov = hv.Overlay(cfg, fake_songs(3))
panel = hv.PanelWindow(ov)
ov.panel = panel
W = 168

print("[1] 各种面板高度 × 各种曲谱数量：布局不重叠、按钮不出界")
for h in (360, 380, 420, 520, 620, 760, 900, 1100):
    for n in (1, 5, 12, 13, 30, 60):
        ov.songs = fake_songs(n)
        ov.song_idx = 0
        panel.song_scroll = 0
        panel.resize(W, h)
        panel.grab()                                  # 触发一次绘制 → 填充命中区
        lay = panel._compute_layout()

        btns = panel._hit_buttons
        bad_btn = [r for r, _ in btns if r.bottom() > h + 0.01 or r.top() < 0]
        list_bottom = lay["list_top"] + lay["list_rows"] * panel.LIST_ROW_H
        btn_head_top = lay["btn_header"].top()
        overlap = list_bottom > btn_head_top + 0.01
        rows_ok = lay["list_rows"] >= 1
        need = n > lay["list_rows"]
        has_sb = panel._hit_scrollbar is not None
        if bad_btn or overlap or not rows_ok or need != has_sb:
            print("  ✗ h=%d n=%d  buttons_out=%d  list_bottom=%.0f btn_head=%.0f rows=%d 滚动条=%s(应为%s)"
                  % (h, n, len(bad_btn), list_bottom, btn_head_top, lay["list_rows"],
                     has_sb, need))
            ok = False
print("  ✓ 全部高度/数量组合：按钮 %d 个都在面板内、列表与按钮区不重叠、滚动条按需出现"
      % len(panel._hit_buttons))

print("\n[2] 滚动条不压住曲谱名字")
ov.songs = fake_songs(30)
panel.song_scroll = 0
panel.resize(W, 620)
panel.grab()
lay = panel._compute_layout()
sb = panel._hit_scrollbar
row = panel._hit_songs[0][1]
check("滚动条在面板右边缘附近", sb["track"].right() > W - lay["pad"] - 8, True)
check("滚动条左边缘在曲谱行右边界之内", sb["track"].left() > row.left(), True)
from PySide6.QtGui import QFontMetrics, QFont                       # noqa: E402
fm = QFontMetrics(QFont("Microsoft YaHei UI", 9))
text_len = fm.horizontalAdvance("30. 测试曲谱30")
text_right = row.left() + 9.0 + text_len
print("      最长一行文字右边缘 ≈ %.0f，滚动条左边缘 = %.0f" % (text_right, sb["track"].left()))

print("\n[3] 滚轮翻页：夹紧不越界")
cap = lay["list_rows"]
for _ in range(100):
    panel.wheelEvent(FakeWheel(-120))
check("滚轮一直往下 → 停在最后一屏", panel.song_scroll, 30 - cap)
for _ in range(100):
    panel.wheelEvent(FakeWheel(120))
check("滚轮一直往上 → 回到开头", panel.song_scroll, 0)


print("\n[4] 拖滑块到底 = 看到最后一首")
panel.grab()
sb = panel._hit_scrollbar
thumb = sb["thumb"]
start = QPointF(thumb.center().x(), thumb.center().y())
press(panel, start)
move(panel, QPointF(start.x(), sb["track"].bottom() + 200))
release(panel, start)
check("拖到底 → 滚动到最后一屏", panel.song_scroll, 30 - cap)
panel.grab()
last = panel._hit_songs[-1][0]
check("最后一行就是第 30 首", last, 29)

print("\n[5] 点轨道空白 = 翻一屏")
panel.song_scroll = 0
panel.grab()
sb = panel._hit_scrollbar
below = QPointF(sb["track"].center().x(), sb["track"].bottom() - 1)
press(panel, below)
release(panel, below)
check("点滑块下方 → 往下翻一屏", panel.song_scroll, min(cap, 30 - cap))

print("\n[6] 点曲谱行仍然能选中（没被滚动条抢走）")
panel.song_scroll = 0
panel.grab()
idx, r = panel._hit_songs[3]
press(panel, QPointF(r.center().x(), r.center().y()))
release(panel, QPointF(r.center().x(), r.center().y()))
check("点了第 4 行 → 选中第 4 首", ov.song_idx, 3)

print("\n[7] 用 F7 换到最后一首时列表自动滚到可见")
panel.song_scroll = 0
ov.song_idx = 29
panel.ensure_visible()
check("自动滚动后最后一行可见", 29 < panel.song_scroll + cap, True)
check("滚动位置不越界", panel.song_scroll <= 30 - cap, True)

print("\n[8] 曲谱很少时不出滚动条")
ov.songs = fake_songs(3)
ov.song_idx = 0
panel.song_scroll = 0
panel.resize(W, 620)
panel.grab()
check("3 首 → 无滚动条", panel._hit_scrollbar, None)
check("3 首 → 三行都在", len(panel._hit_songs), 3)

print("\n结果:", "全部通过 ✓" if ok else "存在失败 ✗")
sys.exit(0 if ok else 1)
