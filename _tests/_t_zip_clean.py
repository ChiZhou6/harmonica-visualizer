# -*- coding: utf-8 -*-
"""模拟"别人拿到 zip 之后的电脑"：

1. 用 Python 解开 三角洲口琴曲谱_v9.3.zip（顺便验证中文文件名能正确还原）
2. **把 PATH 剥到只剩系统目录**（排除本机 venv 里 PySide6 的 DLL 帮忙）后启动 exe
3. 检查窗口有没有画出来、自带曲谱有没有生成

如果这一步过，说明"一个陌生人的电脑（没装 Python、没装 PySide6）也能直接跑"。
"""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from ctypes import wintypes

# ------------------------------------------------------------------ Win32 工具
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    user32.SetProcessDPIAware()

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


def wins_of(pids):
    out = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value in pids:
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if user32.IsWindowVisible(hwnd):
                out.append(buf.value)
        return True

    user32.EnumWindows(cb, 0)
    return out


def kill(pids):
    for p, _, _ in procs():
        if p in pids:
            h = kernel32.OpenProcess(0x0001, False, p)   # PROCESS_TERMINATE
            if h:
                kernel32.TerminateProcess(h, 0)
                kernel32.CloseHandle(h)


# ------------------------------------------------------------------ 1. 解压
ZIP = r"D:\AI\DF Harmonica\三角洲口琴曲谱_v9.3.zip"
TMP = tempfile.mkdtemp(prefix="hv_zip_clean_")
print("压缩包:", ZIP, "(%.1f MB)" % (os.path.getsize(ZIP) / 1048576))
with zipfile.ZipFile(ZIP) as z:
    names = z.namelist()
    print("包内条目:")
    for n in names:
        print("   ", n)
    z.extractall(TMP)

D = os.path.join(TMP, "三角洲口琴曲谱")
print("\n解压到:", D)
print("目录存在:", os.path.isdir(D))

have = sorted(os.listdir(D))
print("解压出来的文件:", have)
songs = sorted(os.listdir(os.path.join(D, "songs")))
print("songs 里的曲谱:", songs)

# 中文文件名在解压后必须完好
name_ok = (os.path.isfile(os.path.join(D, "三角洲口琴曲谱.exe"))
           and os.path.isfile(os.path.join(D, "使用说明.txt"))
           and os.path.isfile(os.path.join(D, "1分钟上手.txt"))
           and "See You Again.txt" in songs
           and "父亲.txt" in songs)
print("中文文件名完好:", name_ok)

# ------------------------------------------------------------------ 2. 干净环境启动
env = {
    "SystemRoot": r"C:\Windows",
    "windir": r"C:\Windows",
    "SystemDrive": "C:",
    "OS": "Windows_NT",
    "PROCESSOR_ARCHITECTURE": "AMD64",
    "NUMBER_OF_PROCESSORS": os.environ.get("NUMBER_OF_PROCESSORS", "4"),
    "COMPUTERNAME": os.environ.get("COMPUTERNAME", "PC"),
    "USERNAME": os.environ.get("USERNAME", "user"),
    "USERPROFILE": os.environ.get("USERPROFILE", ""),
    "APPDATA": os.environ.get("APPDATA", ""),
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
    "TEMP": os.environ.get("TEMP", r"C:\Windows\Temp"),
    "TMP": os.environ.get("TMP", r"C:\Windows\Temp"),
    "PATH": r"C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem",   # 只剩系统目录
    "QT_QPA_PLATFORM": "",                    # 不给任何 Qt 提示
}
env = {k: v for k, v in env.items() if v != ""}

exe = os.path.join(D, "三角洲口琴曲谱.exe")
print("\n用干净环境启动（PATH = %s）" % env["PATH"])
print("注意：环境里没有 venv、没有 PySide6 —— 相当于一台陌生人的电脑")

proc = subprocess.Popen([exe], cwd=D, env=env)
time.sleep(10)
pids = {proc.pid} | {p for p, pp, _ in procs() if pp == proc.pid}
titles = wins_of(pids)
alive = proc.poll() is None

print("  进程:", pids, "｜ 还活着:", alive)
print("  可见窗口:", titles)

regenerated = sorted(os.listdir(os.path.join(D, "songs")))
print("  启动后 songs:", regenerated)

ok = (alive and name_ok
      and any("可视化曲谱" in t for t in titles)
      and any("口琴曲谱" in t for t in titles))
print("\n结果:", "解压即用、干净环境能跑 ✓" if ok else "有问题 ✗")

proc.terminate()
time.sleep(1.5)
kill(pids)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ok else 1)
