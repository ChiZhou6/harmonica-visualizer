# -*- coding: utf-8 -*-
"""「一键隐藏 / 恢复」+「Shift 前缀热键」的离屏测试

覆盖：
  1. 热键解析：一个动作配多个备选键（"shift+f6|shift+f4"），组合键写法不受影响
  2. **所有 F 区热键都必须带 Shift**（防止和游戏里的 F4~F12 抢键）
  3. 注入假的按键状态，验证 Shift+F4 / Shift+F6 都能触发、按住不放不会连发、
     单按 F6（不按 Shift）/ 单按 Shift 都不能触发
  4. 隐藏时把「叠加层 + 面板 + 编辑器」一起收起来（编辑器开着也不留残余挡视野）
  5. 恢复时三个都回来；编辑器原本没开就不要自己冒出来
  6. 面板按钮里有「隐藏窗口」，并且按钮上的热键提示跟着 config 走（不再写死 F6）

⚠️ 本脚本用 offscreen 平台，字体是回退字体、比真实屏幕宽，
   所以**不要**在这里断言"提示一定画得出来"（像素宽度不可信），
   只断言文字内容与布局数值。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:/AI/DF Harmonica/harmonica-visualizer")

import harmonica_visualizer as hv
from PySide6.QtWidgets import QApplication, QWidget

app = QApplication(sys.argv)
cfg = hv.load_config()
songs = [hv.Song("测试曲", 90, [(0.0, 1.0, i % 8, i % 4) for i in range(8)])]

VK_SHIFT, VK_F4, VK_F6, VK_F7 = 0x10, 0x73, 0x75, 0x76
fails = []


def check(name, cond, extra=""):
    print(("  ✓ " if cond else "  ✗ ") + name + ((" -> %s" % (extra,)) if extra != "" else ""))
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------- 假键盘
class FakeU32:
    """只接管 GetAsyncKeyState，其它调用转给真的 user32"""

    def __init__(self, real):
        self._r = real
        self.down = set()

    def GetAsyncKeyState(self, vk):
        return 0x8000 if vk in self.down else 0

    def __getattr__(self, name):
        return getattr(self._r, name)


def build():
    ov = hv.Overlay(cfg, songs)
    p = hv.PanelWindow(ov)
    ov.panel = p
    ed = QWidget()
    ed.setWindowTitle("假编辑器")
    ov.editor = ed
    ov.show()
    p.show()
    app.processEvents()
    return ov, p, ed


print("[1] 热键解析：一个动作可以配多个备选键，Shift 是组合键的一部分")
ov, p, ed = build()
hk = ov.hotkey_vks
check("toggle_visible 有 2 组备选", len(hk.get("toggle_visible", [])) == 2,
      hk.get("toggle_visible"))
check("第 1 组是 Shift+F6", hk["toggle_visible"][0] == (VK_SHIFT, VK_F6), hk["toggle_visible"][0])
check("第 2 组是 Shift+F4", hk["toggle_visible"][1] == (VK_SHIFT, VK_F4), hk["toggle_visible"][1])
check("Shift / F4 / F6 都在轮询表里",
      all(v in ov._watched for v in (VK_SHIFT, VK_F4, VK_F6)))

print("\n[2] F 区热键全部带 Shift（不再有裸 F 键 → 不会和游戏抢键）")
naked = []
for act, combos in hk.items():
    if act == "quit":
        continue
    for c in combos:
        f_keys = [v for v in c if 0x70 <= v <= 0x7B]        # F1~F12
        if f_keys and VK_SHIFT not in c:
            naked.append((act, c))
check("每个含 F 键的组合都带 Shift", not naked, naked)
check("quit 只有 1 组且不受影响", hk["quit"] == [(0x11, 0x12, 0x51)], hk["quit"])
check("next_song 是 Shift+F7", hk["next_song"] == [(VK_SHIFT, VK_F7)], hk["next_song"])
check("save_song 是 Shift+F5", hk["save_song"] == [(VK_SHIFT, 0x74)], hk["save_song"])
check("editor 是 Shift+F11", hk["editor"] == [(VK_SHIFT, 0x7A)], hk["editor"])
check("toggle_record 是 Shift+F12", hk["toggle_record"] == [(VK_SHIFT, 0x7B)], hk["toggle_record"])

print("\n[2b] 面板按钮：有「隐藏窗口」，提示文字由 config 生成（改热键自动跟着变）")
actions = [a for row in hv.PANEL_ROWS for a, _ in row]
check("按钮里有 toggle_visible", "toggle_visible" in actions, actions)
check("隐藏窗口在最上面（一眼能看到）", actions[0] == "toggle_visible", actions)
check("按钮数量 = 7", len(actions) == 7, len(actions))
check("隐藏窗口的提示 = Shift+F6/Shift+F4",
      hv.hotkey_text(cfg, "toggle_visible") == "Shift+F6/Shift+F4",
      hv.hotkey_text(cfg, "toggle_visible"))
check("退出提示不受影响", hv.hotkey_text(cfg, "quit") == "Ctrl+Alt+Q",
      hv.hotkey_text(cfg, "quit"))

print("\n[3] 真的按键能触发（用假键盘状态跑 _poll_input）")
real_u32 = hv.user32
fake = FakeU32(real_u32)
hv.user32 = fake
try:
    def press(vk, on=True):
        if on:
            fake.down.add(vk)
        else:
            fake.down.discard(vk)

    def tick():
        ov._poll_input()
        app.processEvents()

    def hotkey(vk):
        """按一次组合键：先按 Shift，再按功能键，然后都松开（模拟真人按键顺序）"""
        press(VK_SHIFT, True); tick()
        press(vk, True); tick()
        press(vk, False); tick()
        press(VK_SHIFT, False); tick()

    # --- 初始：全都可见
    check("初始叠加层可见", ov.isVisible())
    check("初始面板可见", p.isVisible())

    # --- 裸 F6（不按 Shift）不应该触发
    press(VK_F6, True); tick()
    check("单按 F6（没按 Shift）不会隐藏", ov.isVisible())
    press(VK_F6, False); tick()

    # --- 单按 Shift 也不应该触发
    press(VK_SHIFT, True); tick()
    check("单按 Shift 不会隐藏", ov.isVisible())
    press(VK_SHIFT, False); tick()

    # --- Shift+F4 → 隐藏
    press(VK_SHIFT, True); tick()
    press(VK_F4, True); tick()
    check("Shift+F4 → 叠加层隐藏", not ov.isVisible())
    check("Shift+F4 → 面板隐藏", not p.isVisible())

    # --- 一直按着 → 不连发
    tick(); tick()
    check("按住 Shift+F4 不放不会连发（仍是隐藏）", not ov.isVisible())

    press(VK_F4, False); tick()
    check("松开 F4 后仍隐藏（松键不触发）", not ov.isVisible())
    press(VK_F4, True); tick()
    check("Shift 还按着、再按 F4 → 触发恢复", ov.isVisible() and p.isVisible())
    press(VK_F4, False); tick()
    press(VK_SHIFT, False); tick()

    # --- Shift+F6 同样能触发
    hotkey(VK_F6)
    check("Shift+F6 → 同样能隐藏", not ov.isVisible())
    hotkey(VK_F6)
    check("Shift+F6 → 同样能恢复", ov.isVisible() and p.isVisible())

    # --- 其它键不应该误触发
    press(VK_SHIFT, True); tick()
    press(VK_F7, True); tick()          # Shift+F7 = 换曲
    check("Shift+F7 不会误隐藏", ov.isVisible())
    press(VK_F7, False); tick()
    press(VK_SHIFT, False); tick()
finally:
    hv.user32 = real_u32

print("\n[4] 编辑器：开着的时候按隐藏，要跟着一起收起来")
ed.show()
app.processEvents()
check("编辑器已打开", ed.isVisible())
hv.user32 = fake
try:
    hotkey(VK_F6)
    check("隐藏时编辑器也被收起（没有残余窗口挡视野）", not ed.isVisible())
    check("隐藏时叠加层也收起", not ov.isVisible())
    hotkey(VK_F6)
    check("恢复时编辑器原样回来", ed.isVisible())
    check("恢复时叠加层也回来", ov.isVisible())

    print("\n[5] 编辑器原本没开 → 恢复时不要自己冒出来")
    ed.hide()
    app.processEvents()
    hotkey(VK_F6)
    check("隐藏成功", not ov.isVisible())
    hotkey(VK_F6)
    check("恢复后叠加层可见", ov.isVisible())
    check("恢复后编辑器仍是关闭状态", not ed.isVisible())

    print("\n[6] 反复快速隐藏 / 恢复 10 轮不出错")
    seq = []
    for _ in range(10):
        press(VK_SHIFT, True); tick()
        press(VK_F4, True); tick(); seq.append(ov.isVisible())
        press(VK_F4, False); tick()
        press(VK_F4, True); tick(); seq.append(ov.isVisible())
        press(VK_F4, False); tick()
        press(VK_SHIFT, False); tick()
    expect = [False, True] * 10
    check("10 轮隐藏/恢复状态都对", seq == expect, seq[:6])
    check("最终是可见状态", ov.isVisible())
finally:
    hv.user32 = real_u32

print("\n[7] 提示文字随 config 变（不再出现「写死 F6、实际要按 Shift+F6」）")
cfg2 = dict(cfg)
cfg2["hotkeys"] = dict(cfg["hotkeys"])
cfg2["hotkeys"]["toggle_visible"] = "f8"
check("改成 f8 后提示就显示 F8", hv.hotkey_text(cfg2, "toggle_visible") == "F8",
      hv.hotkey_text(cfg2, "toggle_visible"))
ov2 = hv.Overlay(cfg2, songs)
ov2.hotkey_vks  # noqa: B018  （确认构造不炸）
check("改成裸键后仍能解析出组合", ov2.hotkey_vks["toggle_visible"] == [(0x77,)],
      ov2.hotkey_vks["toggle_visible"])

print("\n结果:", "全部通过 ✓" if not fails else "失败 %d 项 ✗ %s" % (len(fails), fails))
sys.exit(0 if not fails else 1)
