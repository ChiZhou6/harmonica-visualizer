# -*- coding: utf-8 -*-
"""真机验证「一键隐藏 / 恢复」（F6 与 F4 都要能触发）

为什么要真机测：--noconsole 的 exe 出问题什么都不显示；
而且"隐藏后还能不能再显示回来"依赖主循环在窗口不可见时仍在跑，这个只能实测。

顺便验证：恢复后窗口位置大小不变、仍然置顶、叠加层仍然是鼠标穿透（不挡游戏点击）。
"""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    user32.SetProcessDPIAware()
PUL = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", PUL)]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


assert ctypes.sizeof(INPUT) == 40

VK = {"shift": 0x10, "f4": 0x73, "f5": 0x74, "f6": 0x75, "f7": 0x76}


def _send(vk, down):
    i = INPUT(type=1, u=_U(ki=KEYBDINPUT(wVk=vk, wScan=0,
                                         dwFlags=0 if down else 2,
                                         time=0, dwExtraInfo=None)))
    assert user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(i)) == 1


def tap(name, dur=0.07, shift=True):
    """按一次热键。

    shift=True → 先按住 Shift 再按功能键（现在所有 F 区热键都要求 Shift）。
    shift=False → 只按功能键（用来验证"裸 F 键不再触发"，即不再和游戏抢键）。
    """
    if shift:
        _send(VK["shift"], True)
        time.sleep(dur)
    for down in (True, False):
        _send(VK[name], down)
        time.sleep(dur)
    if shift:
        _send(VK["shift"], False)
    time.sleep(0.06)


TH32CS_SNAPPROCESS = 0x2


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260)]


def procs():
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    out = []
    if kernel32.Process32FirstW(snap, ctypes.byref(e)):
        while True:
            out.append((e.th32ProcessID, e.th32ParentProcessID, e.szExeFile))
            if not kernel32.Process32NextW(snap, ctypes.byref(e)):
                break
    kernel32.CloseHandle(snap)
    return out


def kill(pids):
    for p, _, _ in procs():
        if p in pids:
            h = kernel32.OpenProcess(0x0001, False, p)   # PROCESS_TERMINATE
            if h:
                kernel32.TerminateProcess(h, 0)
                kernel32.CloseHandle(h)


GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000

# 只看这两个"真窗口"（Qt 内部辅助窗口 _q_titlebar、PyInstaller 的隐藏窗口都不算）
MAIN = {"口琴可视化曲谱": "叠加层", "三角洲口琴曲谱": "面板"}


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def snapshot(pids):
    """只返回 MAIN 里的窗口；顺序 = Z 序（越靠前越在上层）"""
    found = {}

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value in pids and user32.GetWindow(hwnd, GW_OWNER) == 0:
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value in MAIN and buf.value not in found:
                r = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                found[buf.value] = {
                    "title": buf.value, "what": MAIN[buf.value], "hwnd": hwnd,
                    "visible": bool(user32.IsWindowVisible(hwnd)),
                    "rect": (r.left, r.top, r.right - r.left, r.bottom - r.top),
                    "topmost": bool(ex & WS_EX_TOPMOST),
                    "transparent": bool(ex & WS_EX_TRANSPARENT),
                    "noactivate": bool(ex & WS_EX_NOACTIVATE),
                }
        return True

    user32.EnumWindows(cb, 0)
    return list(found.values())


fails = []


def check(name, cond, extra=""):
    print(("  ✓ " if cond else "  ✗ ") + name + (("  -> %s" % (extra,)) if extra != "" else ""))
    if not cond:
        fails.append(name)


SRC = r"D:\AI\DF Harmonica\口琴曲谱"
TMP = tempfile.mkdtemp(prefix="hv_hide_")
D = os.path.join(TMP, "口琴曲谱")
shutil.copytree(SRC, D)
exe = os.path.join(D, "三角洲口琴曲谱.exe")
print("成品 exe:", exe)

proc = subprocess.Popen([exe], cwd=D)
time.sleep(9)
pids = {proc.pid} | {p for p, pp, _ in procs() if pp == proc.pid}
print("进程:", pids)

s0 = snapshot(pids)
print("\n[初始]  ", {x["what"]: (x["visible"], x["rect"]) for x in s0})
check("两个窗口都在", len(s0) == 2, [x["title"] for x in s0])

for key in ("f6", "f4"):
    print("\n----- 测试 Shift+%s -----" % key.upper())
    tap(key)
    time.sleep(0.9)
    s1 = snapshot(pids)
    hidden = [x["what"] for x in s1 if not x["visible"]]
    print("  按 Shift+%s 后:" % key.upper(), {x["what"]: x["visible"] for x in s1})
    check("按 Shift+%s → 两个窗口都隐藏" % key.upper(), len(hidden) == 2, hidden)

    tap(key)
    time.sleep(0.9)
    s2 = snapshot(pids)
    shown = [x["what"] for x in s2 if x["visible"]]
    print("  再按 Shift+%s 后:" % key.upper(), {x["what"]: x["visible"] for x in s2})
    check("再按 Shift+%s → 两个窗口都回来" % key.upper(), len(shown) == 2, shown)

    if s2:
        same = all(any(a["title"] == b["title"] and a["rect"] == b["rect"] for b in s2)
                   for a in s0)
        check("恢复后位置大小没变", same)
        check("恢复后仍然置顶", all(b["topmost"] for b in s2))
        ov = [b for b in s2 if b["what"] == "叠加层"]
        if ov:
            check("叠加层恢复后仍是鼠标穿透", ov[0]["transparent"])
            check("叠加层恢复后仍不抢焦点", ov[0]["noactivate"])

# 改成 Shift+F 之后，裸按 F 键必须完全没反应（这才是"不和游戏抢键"的证明）
print("\n----- 裸按 F6（不按 Shift）不应该有任何反应 -----")
check("裸按之前是可见的", all(x["visible"] for x in snapshot(pids)))
tap("f6", shift=False)
time.sleep(0.9)
s_bare = snapshot(pids)
check("裸按 F6 → 窗口还在（不再抢键）", all(x["visible"] for x in s_bare),
      {x["what"]: x["visible"] for x in s_bare})

# 隐藏状态下不该被别的键唤醒
print("\n----- 隐藏状态下按 Shift+F7（换曲）不应该把窗口弄出来 -----")
tap("f6")
time.sleep(0.9)
check("已隐藏", all(not x["visible"] for x in snapshot(pids)))
tap("f7")
time.sleep(0.9)
check("按 Shift+F7 后仍然是隐藏的", all(not x["visible"] for x in snapshot(pids)))
tap("f4", shift=False)
time.sleep(0.9)
check("裸按 F4 也不会把它叫回来", all(not x["visible"] for x in snapshot(pids)))
tap("f4")
time.sleep(0.9)
check("按 Shift+F4 能把窗口叫回来", all(x["visible"] for x in snapshot(pids)))

print("\n结果:", "隐藏 / 恢复（Shift+F6 与 Shift+F4）全部正常 ✓" if not fails
      else "失败 %d 项 ✗ %s" % (len(fails), fails))

proc.terminate()
time.sleep(1.5)
kill(pids)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if not fails else 1)
