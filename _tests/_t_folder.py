# -*- coding: utf-8 -*-
"""曲谱文件夹：默认路径 / 切换到自定义 / 切回默认 —— 离屏测试"""
import json
import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                                    # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_folder_test_")
hv.BASE_DIR = TMP
hv.CONFIG_PATH = os.path.join(TMP, "config.json")
hv.DEFAULT_SONGS_DIR = os.path.join(TMP, "songs")
hv.SONGS_DIR = hv.DEFAULT_SONGS_DIR

app = QApplication(sys.argv)
ok = True


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + label, "->", got, "" if good else ("(期望 %s)" % (want,)))


print("[1] 首次运行：默认落在程序旁边，并生成 4+1 首自带曲谱")
hv.apply_songs_dir(hv.load_config())
hv.ensure_data_files()
check("默认目录 = exe 旁边的 songs", hv.SONGS_DIR, os.path.join(TMP, "songs"))
check("自带曲谱已生成", sorted(os.listdir(hv.SONGS_DIR)),
      sorted(hv.SAMPLE_SONGS.keys()))
check("See You Again 也在里面", "See You Again.txt" in os.listdir(hv.SONGS_DIR), True)
titles = [s.title for s in hv.load_songs()]
check("列表里读到了它", "See You Again" in titles, True)

print("\n[2] 在编辑器里点「曲谱文件夹…」改成别处")
CUSTOM = os.path.join(TMP, "我的曲谱收藏")
os.makedirs(CUSTOM, exist_ok=True)
with open(os.path.join(CUSTOM, "自定义曲目.txt"), "w", encoding="utf-8") as f:
    f.write("TITLE=自定义曲目\n1 2 3 ^4 ^5\n")

cfg = hv.load_config()
ov = hv.Overlay(cfg, hv.load_songs())
panel = hv.PanelWindow(ov)
ov.panel = panel
ed = hv.SongEditor(ov)
ov.editor = ed

QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: CUSTOM)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
ed.choose_folder()

check("SONGS_DIR 已切过去", hv.SONGS_DIR, os.path.normpath(CUSTOM))
check("config.json 里记下来了", json.load(open(hv.CONFIG_PATH, encoding="utf-8"))["songs_dir"],
      os.path.normpath(CUSTOM))
check("面板里只剩自定义那首", [s.title for s in ov.songs], ["自定义曲目"])
check("状态栏显示了新目录", CUSTOM in ed.status.text(), True)

print("\n[3] 重启程序（重新读 config）→ 仍然用自定义目录")
hv.SONGS_DIR = hv.DEFAULT_SONGS_DIR                       # 模拟重启
cfg2 = hv.load_config()
hv.apply_songs_dir(cfg2)
check("重启后仍是自定义目录", hv.SONGS_DIR, os.path.normpath(CUSTOM))
check("重启后读到的曲谱", [s.title for s in hv.load_songs()], ["自定义曲目"])

print("\n[4] 改成相对路径（相对 exe 所在目录）")
hv._save_config = lambda *a, **k: None                    # 避免动 config
cfg2["songs_dir"] = "我的曲谱收藏"
check("相对路径能解析到 exe 旁边", hv.resolve_songs_dir(cfg2), os.path.normpath(CUSTOM))

print("\n[5] 切回默认（选回程序旁边的 songs）")
cfg2["songs_dir"] = ""
check("恢复默认路径", hv.resolve_songs_dir(cfg2), os.path.join(TMP, "songs"))
check("是默认目录吗", hv.is_default_songs_dir(hv.resolve_songs_dir(cfg2)), True)

print("\n[6] 新文件夹是空的时候，问要不要把自带曲谱拷过去")
EMPTY = os.path.join(TMP, "全新空文件夹")
os.makedirs(EMPTY, exist_ok=True)
hv.apply_songs_dir({"songs_dir": ""})                     # 先确保默认目录有曲谱
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: EMPTY)
ed.choose_folder()                                        # 默认回答 No → 不该拷
check("回答 No 时不复制", os.listdir(EMPTY), [])
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
ed.choose_folder()                                        # 回答 Yes → 该拷
check("回答 Yes 时把自带曲谱都拷过去", sorted(os.listdir(EMPTY)),
      sorted(hv.SAMPLE_SONGS.keys()))

shutil.rmtree(TMP, ignore_errors=True)
print("\n结果:", "全部通过 ✓" if ok else "存在失败 ✗")
sys.exit(0 if ok else 1)
