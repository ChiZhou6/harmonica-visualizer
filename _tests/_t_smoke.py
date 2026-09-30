# -*- coding: utf-8 -*-
"""交付目录里那份成品 exe 的冒烟测试。

（--noconsole 的程序崩溃时什么都不会显示，所以必须靠"窗口在不在"来判断）

★ 不会在交付目录里直接跑：先把整个文件夹复制到临时目录再跑，
  否则退出时会用默认窗口位置覆盖用户辛苦对齐好的 config.json 里的 geometry。
★ 两个阶段一起验：
  [阶段 1] 全新解压（songs + config.json 都没有）→ exe 应该自己把自带曲谱生成出来，
           这同时证明"重新打包确实打进去了新曲谱"。
  [阶段 2] 老用户（config.json 已经在）把曲谱全删掉再启动 → **不许补回来**。
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


SRC = r"D:\AI\DF Harmonica\三角洲口琴曲谱_发布版"
TMP = tempfile.mkdtemp(prefix="hv_smoke_")
D = os.path.join(TMP, "口琴曲谱")
shutil.copytree(SRC, D)
exe = os.path.join(D, "三角洲口琴曲谱.exe")
songs_dir = os.path.join(D, "songs")
cfg_path = os.path.join(D, "config.json")
print("交付 exe:", exe)
print("（已复制到临时目录，不在交付目录里跑）")


def run_exe(seconds):
    """启动交付 exe，等一会，返回 (进程还活着?, 可见窗口标题列表)，然后收掉进程"""
    proc = subprocess.Popen([exe], cwd=D)
    time.sleep(seconds)
    pids = {proc.pid} | {p for p, pp, _ in procs() if pp == proc.pid}
    titles = wins_of(pids)
    alive = proc.poll() is None
    kill(pids)
    time.sleep(0.8)
    return alive, titles


# ---------- 阶段 1：全新解压（songs 和 config.json 都没有）----------
# 这是"新用户下载解压后第一次打开"的场景：应该自动生成 config + 自带曲谱，
# 顺便证明"重新打包确实把曲谱打进去了"。
print("\n[阶段 1] 全新解压：删掉 songs 文件夹和 config.json 后启动")
shutil.rmtree(songs_dir, ignore_errors=True)
if os.path.exists(cfg_path):
    os.remove(cfg_path)

alive, titles = run_exe(9)
print("  进程还活着:", alive)
print("  可见窗口:", titles)
have = sorted(os.listdir(songs_dir)) if os.path.isdir(songs_dir) else []
print("  自动生成的曲谱:", have)
if os.path.isfile(cfg_path):
    cfg_text = open(cfg_path, encoding="utf-8").read()
    print("  config.json 里有 songs_dir 字段:", '"songs_dir"' in cfg_text)

WANT = ["See You Again.txt", "小星星.txt", "欢乐颂.txt", "父亲.txt", "音域与变调练习.txt"]
ok1 = (alive
       and any("可视化曲谱" in t for t in titles)
       and any("口琴曲谱" in t for t in titles)
       and all(n in have for n in WANT))
print("  阶段 1:", "全新解压能正常启动、并自动补齐 5 首自带曲谱 ✓" if ok1
      else "有问题 ✗（起不来 / 窗口没出来 / 曲谱没打进去）")

# ---------- 阶段 2：老用户把曲谱删了 → 不许再补回来 ----------
# 本轮用户反馈的 bug：删掉默认曲谱，重开软件又被加回来。
# 现在 config.json 已经存在（= 老用户），把曲谱全删掉再启动，目录应该保持为空。
print("\n[阶段 2] 老用户场景：config.json 还在，把曲谱全删掉后重新启动")
for n in list(os.listdir(songs_dir)) if os.path.isdir(songs_dir) else []:
    if n.lower().endswith(".txt"):
        os.remove(os.path.join(songs_dir, n))
print("  启动前曲谱:", sorted(os.listdir(songs_dir)) if os.path.isdir(songs_dir) else [])

ok2 = False
if os.path.isfile(cfg_path):
    run_exe(8)
    left = sorted(os.listdir(songs_dir)) if os.path.isdir(songs_dir) else []
    print("  启动后曲谱:", left)
    ok2 = (left == [])
    print("  阶段 2:", "删掉的曲谱没有被补回来 ✓" if ok2
          else "有问题 ✗（曲谱又自己回来了：%s）" % left)
else:
    print("  阶段 1 没能生成 config.json，无法模拟老用户 ✗")

print("\n结果:",
      "交付副本能正常启动、画出窗口、全新解压自动补齐曲谱、老用户删掉的曲谱不会再回来 ✓"
      if (ok1 and ok2) else "有问题 ✗")
sys.exit(0 if (ok1 and ok2) else 1)
time.sleep(1.5)
kill(pids)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ok else 1)
