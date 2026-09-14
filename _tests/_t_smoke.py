# -*- coding: utf-8 -*-
"""交付目录里那份成品 exe 的冒烟测试。

（--noconsole 的程序崩溃时什么都不会显示，所以必须靠"窗口在不在"来判断）

★ 不会在交付目录里直接跑：先把整个文件夹复制到临时目录再跑，
  否则退出时会用默认窗口位置覆盖用户辛苦对齐好的 config.json 里的 geometry。
★ 顺便验证：把复制品里的 songs 文件夹删掉后启动，exe 能不能自己把自带曲谱
  （含 See You Again）重新生成出来 —— 这同时证明"重新打包确实打进去了新曲谱"。
"""
import ctypes
import json
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


SRC = r"D:\AI\DF Harmonica\口琴曲谱"
TMP = tempfile.mkdtemp(prefix="hv_smoke_")
D = os.path.join(TMP, "口琴曲谱")
shutil.copytree(SRC, D)
shutil.rmtree(os.path.join(D, "songs"), ignore_errors=True)      # 故意删掉曲谱文件夹
exe = os.path.join(D, "三角洲口琴曲谱.exe")
print("交付 exe:", exe)
print("（已复制到临时目录，且故意删掉了 songs 文件夹）")

proc = subprocess.Popen([exe], cwd=D)
time.sleep(9)
pids = {proc.pid} | {p for p, pp, _ in procs() if pp == proc.pid}
titles = wins_of(pids)
alive = proc.poll() is None

print("进程:", pids, "｜ 还活着:", alive)
print("可见窗口:", titles)

songs_dir = os.path.join(D, "songs")
have = sorted(os.listdir(songs_dir)) if os.path.isdir(songs_dir) else []
print("自动生成的曲谱:", have)
cfg_text = open(os.path.join(D, "config.json"), encoding="utf-8").read()
print("config.json 里有 songs_dir 字段:", '"songs_dir"' in cfg_text)

ok = (alive
      and any("可视化曲谱" in t for t in titles)
      and any("口琴曲谱" in t for t in titles)
      and "See You Again.txt" in have
      and "小星星.txt" in have
      and "欢乐颂.txt" in have
      and "父亲.txt" in have
      and "音域与变调练习.txt" in have)

print("结果:", "交付副本能正常启动、画出窗口、并把 5 首自带曲谱（含 See You Again / 父亲）重新生成 ✓"
      if ok else "有问题 ✗")

proc.terminate()
time.sleep(1.5)
kill(pids)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ok else 1)
