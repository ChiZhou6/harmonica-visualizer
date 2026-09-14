# -*- coding: utf-8 -*-
"""成品 exe 真机端到端测试：F11 开编辑器 → 输入曲名 → F12 录音 → 注入按键
   → F12 结束 → Ctrl+S 保存 → 检查 songs 目录里真的多了一个内容正确的曲谱

   ⚠️ 会在真实屏幕上注入按键，请勿在游戏/编辑器正在输入时跑。
"""
import ctypes
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

from PIL import ImageGrab

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:                                  # 让本测试进程与屏幕坐标一致（否则取窗口矩形会偏）
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


assert ctypes.sizeof(INPUT) == 40, ctypes.sizeof(INPUT)   # x64 必须是 40 字节

VK = {"z": 0x5A, "x": 0x58, "c": 0x43, "v": 0x56, "b": 0x42, "n": 0x4E, "m": 0x4D,
      ",": 0xBC, "r": 0x52, "e": 0x45, "1": 0x31, "f5": 0x74, "f11": 0x7A, "f12": 0x7B,
      "ctrl": 0x11, "s": 0x53, "alt": 0x12, "q": 0x51, "shift": 0x10,
      "escape": 0x1B, "enter": 0x0D, "tab": 0x09}
MOUSE_DN = {"left": 0x0002, "right": 0x0008, "middle": 0x0020}
MOUSE_UP = {"left": 0x0004, "right": 0x0010, "middle": 0x0040}


def _inp(i):
    assert user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(i)) == 1


def key(name, down=True):
    _inp(INPUT(type=1, u=_U(ki=KEYBDINPUT(wVk=VK[name], wScan=0,
                                          dwFlags=0 if down else 2,
                                          time=0, dwExtraInfo=None))))


def tap(name, dur=0.06):
    key(name, True)
    time.sleep(dur)
    key(name, False)
    time.sleep(0.05)


def hot(name, dur=0.06):
    """按一次 F 区热键。

    ⚠️ 现在所有 F 区热键都要求**按住 Shift**（Shift+F5/F11/F12…），
    避免和游戏里的 F4~F12 抢键 → 注入时必须先按住 Shift。
    """
    key("shift", True)
    time.sleep(0.04)
    tap(name, dur)
    key("shift", False)
    time.sleep(0.05)


def mouse(btn, down=True):
    _inp(INPUT(type=0, u=_U(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0,
                                          dwFlags=(MOUSE_DN if down else MOUSE_UP)[btn],
                                          time=0, dwExtraInfo=None))))


def combo(*names, **kw):
    for n in names:
        key(n, True)
    time.sleep(kw.get("hold", 0.08))
    for n in reversed(names):
        key(n, False)
    time.sleep(0.25)


MOVE_ABS = 0x8000
MOVE_ONLY = 0x8000 | 0x0001   # ⚠️ 绝对移动必须带上 MOUSEEVENTF_MOVE(0x0001)，
                              #    只发 0x8000 光标根本不动（实测过）


def click(x, y):
    """真实鼠标点击（绝对坐标，物理像素）"""
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    ax, ay = int(x * 65535 / (sw - 1)), int(y * 65535 / (sh - 1))
    for flag in (MOVE_ABS | 0x0001 | 0x0002, MOVE_ABS | 0x0001 | 0x0004):
        _inp(INPUT(type=0, u=_U(mi=MOUSEINPUT(dx=ax, dy=ay, mouseData=0,
                                              dwFlags=flag, time=0, dwExtraInfo=None))))
        time.sleep(0.06)
    time.sleep(0.3)


def move_mouse(x, y):
    """只移动鼠标（不按键）——务必把光标挪到"不属于本程序"的地方再按住鼠标键，
       否则右键点到我们自己的标题栏会弹出 Windows 系统菜单，卡住程序自己的轮询"""
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    ax, ay = int(x * 65535 / (sw - 1)), int(y * 65535 / (sh - 1))
    _inp(INPUT(type=0, u=_U(mi=MOUSEINPUT(dx=ax, dy=ay, mouseData=0,
                                          dwFlags=MOVE_ONLY, time=0, dwExtraInfo=None))))
    time.sleep(0.2)
    pt = wintypes.POINT()                 # 确认光标真的挪走了
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


def windows_of(pid):
    out = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid:
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            out.append(dict(hwnd=hwnd, title=buf.value,
                            vis=bool(user32.IsWindowVisible(hwnd)),
                            rect=(r.left, r.top, r.right, r.bottom)))
        return True

    user32.EnumWindows(cb, 0)
    return out


TH32CS_SNAPPROCESS = 0x2


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260)]


def children_of(pid):
    """PyInstaller onefile：父进程只是引导，真正的程序在子进程里"""
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    out = []
    if kernel32.Process32FirstW(snap, ctypes.byref(e)):
        while True:
            if e.th32ParentProcessID == pid:
                out.append(e.th32ProcessID)
            if not kernel32.Process32NextW(snap, ctypes.byref(e)):
                break
    kernel32.CloseHandle(snap)
    return out


def target_pids(pid):
    """父进程 + 它的子进程（程序本体）"""
    out = [pid]
    for _ in range(3):
        more = []
        for p in out:
            more += [c for c in children_of(p) if c not in out]
        if not more:
            break
        out += more
    return out


def kill_instances_in(folder):
    """只结束"可执行文件位于 folder 里"的进程（不动用户自己那份程序）"""
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    killed = []
    if kernel32.Process32FirstW(snap, ctypes.byref(e)):
        while True:
            h = kernel32.OpenProcess(0x0001, False, e.th32ProcessID)   # PROCESS_TERMINATE
            if h:
                buf = ctypes.create_unicode_buffer(600)
                n = wintypes.DWORD(600)
                if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                    if os.path.normcase(folder) in os.path.normcase(buf.value):
                        kernel32.TerminateProcess(h, 0)
                        killed.append((e.th32ProcessID, buf.value))
                kernel32.CloseHandle(h)
            if not kernel32.Process32NextW(snap, ctypes.byref(e)):
                break
    kernel32.CloseHandle(snap)
    return killed


# ---------------------------------------------------------------- 准备临时副本
SRC = r"D:\AI\DF Harmonica\口琴曲谱"
TMP = os.path.join(os.environ["TEMP"], "hv_exe_record_test")
# 上一次跑崩了会把"还在运行的 exe"留在临时目录里、占住文件夹删不掉，
# 于是下一次报 FileExistsError 这种看不懂的错 → 这里显式重试并给出人话提示。
for _ in range(3):
    if not os.path.exists(TMP):
        break
    shutil.rmtree(TMP, ignore_errors=True)
    time.sleep(1.0)
if os.path.exists(TMP):
    print("⚠️ 临时目录删不掉：%s" % TMP)
    print("   多半是上一次测试崩溃后，那里的 三角洲口琴曲谱.exe 还在运行。")
    print("   请先在任务管理器里结束它（或运行：")
    print("     Get-Process | ? {$_.Path -like '*hv_exe_record_test*'} | Stop-Process -Force")
    print("   然后再重跑本测试。")
    sys.exit(2)
shutil.copytree(SRC, TMP)
shutil.copy(r"D:\AI\DF Harmonica\harmonica-visualizer\dist\HarmonicaScore.exe",
            os.path.join(TMP, "三角洲口琴曲谱.exe"))
songs_dir = os.path.join(TMP, "songs")
before = set(os.listdir(songs_dir))
print("测试副本:", TMP)
print("录音前 songs:", sorted(before))

ok = True


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + label, "->", got, "" if good else ("(期望 %s)" % (want,)))


exe = os.path.join(TMP, "三角洲口琴曲谱.exe")
old = kill_instances_in(TMP)          # 清掉上次测试可能残留的实例（不动用户自己那份）
if old:
    print("先结束上次残留的测试实例:", old)
    time.sleep(1.5)
proc = subprocess.Popen([exe], cwd=TMP)
print("启动 exe, pid =", proc.pid)
time.sleep(9)

PIDS = target_pids(proc.pid)
print("进程树:", PIDS, "（父进程是 PyInstaller 引导，程序本体在子进程）")


def all_wins():
    out = []
    for p in PIDS:
        out += windows_of(p)
    return out


wins = all_wins()
print("[A] 程序窗口:")
for w in wins:
    print("    ", w)
vis = [w for w in wins if w["vis"] and w["rect"][2] - w["rect"][0] > 60]
check("有可见窗口（叠加层 + 面板）", len(vis) >= 2, True)
check("进程还活着（没崩溃）", proc.poll(), None)

print("[B] Shift+F11 → 打开曲谱编辑器")
hot("f11")
time.sleep(1.5)
wins = all_wins()
editor = [w for w in wins if "编辑曲谱" in w["title"]]
check("编辑器窗口存在", len(editor), 1)
check("编辑器可见", editor[0]["vis"] if editor else False, True)
ed_hwnd = editor[0]["hwnd"] if editor else 0
ed_rect = editor[0]["rect"] if editor else (0, 0, 0, 0)
shot0 = ImageGrab.grab(bbox=ed_rect)

print("[C] 用真实鼠标点一下编辑器标题栏（游戏在前台时窗口可能拿不到键盘焦点）")
click(ed_rect[0] + (ed_rect[2] - ed_rect[0]) // 2, ed_rect[1] + 12)
time.sleep(0.6)
fg = user32.GetForegroundWindow()
check("编辑器已拿到前台焦点", fg, ed_hwnd)

print("[D] Shift+F12 → 开始录音，检查叠加层出现红点")
hot("f12")
time.sleep(1.0)
wins = all_wins()
overlay = [w for w in wins if w["vis"] and w["rect"][2] - w["rect"][0] > 300]
ov_rect = overlay[0]["rect"] if overlay else (0, 0, 0, 0)
shot = ImageGrab.grab(bbox=ov_rect)
px = shot.load()
reds = 0
for y in range(0, shot.height, 2):
    for x in range(0, shot.width, 2):
        r, g, b = px[x, y][:3]
        if r > 150 and r - g > 55 and r - b > 55:
            reds += 1
check("叠加层出现红色“录音中”标记（像素 > 5）", reds > 5, True)
shot.save(os.path.join(TMP, "_rec_overlay.png"))

def editor_rect():
    for w in all_wins():
        if "编辑曲谱" in w["title"]:
            return w["rect"]
    return (0, 0, 0, 0)


def grab_editor(tag):
    r = editor_rect()
    print("      编辑器矩形:", r)
    img = ImageGrab.grab(bbox=r)
    img.save(os.path.join(TMP, "_rec_%s.png" % tag))
    return img


print("[E] 注入演奏：按住右键弹 z x c（= 高音 ^1 ^2 ^3），松开后弹 v b n m ,（= 4 5 6 7 8），"
      "再验证半音组合：中键+左键=#b（黄）、中键+右键=#^（红）")
# 光标必须离开本程序的所有窗口：否则右键按在"自己的标题栏"上会弹出本进程的系统菜单，
# 那是模态菜单，会把我们自己的消息循环整个卡住 → 右键期间的音全丢。
SW, SH = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
cur = move_mouse(SW - 60, SH - 200)


def outside_program(x, y):
    for w in all_wins():
        if not w["vis"]:
            continue
        l, t, r, b = w["rect"]
        if l <= x <= r and t <= y <= b:
            return w["title"] or w["hwnd"]
    return None


hit = outside_program(*cur)
print("      光标已挪到:", cur, "→", "不在任何程序窗口内 ✓" if not hit else ("落在了 %s 里 ✗" % hit))
check("光标已离开本程序窗口（否则右键会弹出自己的系统菜单卡住轮询）", hit, None)
mouse("right", True)
time.sleep(0.3)
for k in "zxc":
    tap(k)
time.sleep(0.4)
grab_editor("after_high")          # 此刻文本框里应该已经有 ^1 ^2 ^3
mouse("right", False)
time.sleep(0.2)
for k in "vbnm,":
    tap(k)
time.sleep(0.5)
grab_editor("after_all")           # 此刻应该是 ^1 ^2 ^3 4 5 6 7 8

# 半音+降调（中键+左键）→ 黄 #b1；半音+升调（中键+右键）→ 红 #^2
tap("escape")                       # 关掉右键在桌面上弹出的系统菜单，避免它吃掉组合键
time.sleep(0.3)
mouse("middle", True)
mouse("left", True)
time.sleep(0.3)
tap("z")
time.sleep(0.3)
mouse("left", False)
mouse("middle", False)
time.sleep(0.3)

mouse("middle", True)
mouse("right", True)
time.sleep(0.3)
tap("x")
time.sleep(0.3)
mouse("right", False)
mouse("middle", False)
time.sleep(0.5)
grab_editor("after_combo")        # 此刻应该是 ^1 ^2 ^3 4 5 6 7 8 #b1 #^2

print("[E2] 右键在桌面上弹过系统菜单，前台焦点已被抢走；重新点编辑器把焦点要回来")
print("     （真实使用时右键按在游戏里，不会弹菜单、也不会抢走焦点）")


def focus_editor():
    for i in range(3):
        click(ed_rect[0] + (ed_rect[2] - ed_rect[0]) // 2, ed_rect[1] + 12)
        time.sleep(0.5)
        if user32.GetForegroundWindow() == ed_hwnd:
            return i + 1
    return 0


tries = focus_editor()
check("保存前编辑器重新拿到前台焦点（Ctrl+S 是窗口级快捷键）", tries != 0, True)

print("[F] Shift+F12 → 结束录音；Ctrl+S → 保存到曲谱库")
hot("f12")
time.sleep(0.8)
ImageGrab.grab(bbox=ed_rect).save(os.path.join(TMP, "_rec_editor.png"))
combo("ctrl", "s")
time.sleep(2.0)
ImageGrab.grab(bbox=ed_rect).save(os.path.join(TMP, "_rec_editor_saved.png"))
tap("escape")                     # 万一弹出提示框，关掉它，别卡住后面的测试
time.sleep(0.4)

after = set(os.listdir(songs_dir))
new = after - before
print("录音后 songs:", sorted(after))
check("新增了 1 个曲谱文件", len(new), 1)
if new:
    path = os.path.join(songs_dir, list(new)[0])
    text = open(path, encoding="utf-8").read()
    print("      文件内容:", repr(text))
    body = " ".join(l for l in text.splitlines()
                    if l.strip() and not l.strip().upper().startswith(("TITLE=", "BPM=")))
check("录下来的音（含 高音 ^ / 半音+降调 #b / 半音+升调 #^）", body.split(),
      ["^1", "^2", "^3", "4", "5", "6", "7", "8", "#b1", "#^2"])

print("[F2] 真实场景：焦点不在本程序上（相当于游戏在前台），不碰编辑器直接按 Shift+F5 保存")
click(SW - 60, SH - 200)                  # 把焦点让出去，模拟游戏独占前台
time.sleep(0.5)
print("      此时前台窗口 =", user32.GetForegroundWindow(), "（编辑器是", ed_hwnd, "）")
check("前台已不是本程序窗口", user32.GetForegroundWindow() != ed_hwnd, True)
hot("f12")                                # 开始录音
time.sleep(0.8)
for k in "zn":
    tap(k)
time.sleep(0.4)
hot("f5")                                  # 一条龙：结束录音 + 存进曲谱库
time.sleep(2.0)
after2 = set(os.listdir(songs_dir))
new2 = sorted(after2 - after)
print("F5 保存后 songs:", sorted(after2))
check("F5 又新增了 1 个曲谱文件", len(new2), 1)
if new2:
    path2 = os.path.join(songs_dir, new2[0])
    text2 = open(path2, encoding="utf-8").read()
    print("      新文件名:", new2[0])
    print("      文件内容:", repr(text2))
    body2 = " ".join(l for l in text2.splitlines()
                     if l.strip() and not l.strip().upper().startswith(("TITLE=", "BPM=")))
    check("F5 存下的最后两个音是刚弹的 1 和 6（z 与 n 键）", body2.split()[-2:], ["1", "6"])
    check("曲名重名时自动改成《我的曲谱2》", new2[0], "我的曲谱2.txt")

print("[H] exe 能往自己所在目录写文件")
cfg_text = open(os.path.join(TMP, "config.json"), encoding="utf-8").read()
check("config.json 里热键都带 Shift 前缀（Shift+F5/F11/F12）",
      ('"editor": "shift+f11"' in cfg_text and '"toggle_record": "shift+f12"' in cfg_text
       and '"save_song": "shift+f5"' in cfg_text), True)

print("[G] 退出（Ctrl+Alt+Q）")
combo("ctrl", "alt", "q", hold=0.2)
for _ in range(12):                     # onefile 的引导进程要等子进程收尾，别急着判失败
    if proc.poll() is not None:
        break
    time.sleep(0.5)
if proc.poll() is None:
    proc.terminate()
    print("      （热键没退成，已强制结束）")
    ok = False
else:
    print("      ✓ 进程已正常退出")

print("\n结果:", "全部通过 ✓" if ok else "存在失败 ✗")
print("临时目录:", TMP)
sys.exit(0 if ok else 1)
