# -*- coding: utf-8 -*-
"""「删掉的曲谱不会再被自动加回来」离屏测试

用户反馈：把默认曲谱删了之后，重新打开软件时被删掉的默认曲谱又回来了。

根因：`ensure_data_files()` 每次启动都跑，逻辑是"对 SAMPLE_SONGS 里每一首，
文件不存在就写一份" → 缺哪首补哪首，用户白删。

改法：示例曲谱**只在程序第一次运行时给一次**，判断依据是 config.json 是否已存在
（它由 ensure_data_files 在首次运行时创建）。之后曲谱目录怎么增删都听用户的。
曲谱目录被清空时，列表里给一首**内存里的**占位曲谱（不写盘），免得程序没东西可用。

覆盖：
  1. 全新环境（没 config、没 songs）→ 生成 config + 示例曲谱
  2. 全新环境但目录里已有自己的曲谱 → 不插示例（不覆盖用户东西）
  3. 老环境（config 已在）→ 反复启动也不动目录内容
  4. ★ 老环境 + 删掉一首 → 那首不会回来，其余照旧
  5. ★ 老环境 + 全删光 → 再启动多少次，目录都保持为空
  6. 曲谱为空时 load_songs 给占位曲谱（不崩、标题看得懂、有音符）
  7. ★ 占位曲谱不写盘 → 曲谱文件夹仍然是空的（不会"复活"）
  8. song_files()：只认 .txt、排序、目录不存在不炸
  9. 自定义曲谱目录（config.songs_dir）为空时同样不补
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv                                # noqa: E402

ok = True


def check(name, got, want):
    global ok
    if got == want:
        print("  [OK] %s" % name)
    else:
        ok = False
        print("  [FAIL] %s  得到=%r  期望=%r" % (name, got, want))


def sandbox():
    """每个用例一套干净目录，避免互相污染"""
    d = tempfile.mkdtemp(prefix="hv_seed_")
    hv.BASE_DIR = d
    hv.CONFIG_PATH = os.path.join(d, "config.json")
    hv.SONGS_DIR = os.path.join(d, "songs")
    return d


def write_song(name, title="测试曲"):
    with open(os.path.join(hv.SONGS_DIR, name), "w", encoding="utf-8") as f:
        f.write("TITLE=%s\n1 2 3 4 5 -\n" % title)


def wipe_songs():
    for n in hv.song_files():
        os.remove(os.path.join(hv.SONGS_DIR, n))


print("[1] 全新环境（没 config、没 songs）→ 应该生成 config + 示例曲谱")
sb = sandbox()
hv.ensure_data_files()
check("config.json 生成", os.path.isfile(hv.CONFIG_PATH), True)
check("示例曲谱全都写出来了", len(hv.song_files()), len(hv.SAMPLE_SONGS))
check("数量不为 0（确认 SAMPLE_SONGS 非空）", len(hv.SAMPLE_SONGS) > 0, True)

print("[2] 全新环境但目录里已有自己的曲谱 → 不插示例、不覆盖")
sb = sandbox()
os.makedirs(hv.SONGS_DIR, exist_ok=True)
write_song("我的谱.txt", "我的谱")
hv.ensure_data_files()
check("目录里只有我自己的那首", hv.song_files(), ["我的谱.txt"])

print("[3] 老环境（config 已在）→ 反复启动不动目录")
sb = sandbox()
hv.ensure_data_files()
before = hv.song_files()
for _ in range(3):
    hv.ensure_data_files()                     # 模拟反复重启
check("目录内容一字不变", hv.song_files(), before)
check("也没有多塞东西", len(os.listdir(hv.SONGS_DIR)), len(before))

print("[4] ★ 老环境 + 删掉其中一首 → 那首不会回来")
sb = sandbox()
hv.ensure_data_files()
victim = hv.song_files()[0]
os.remove(os.path.join(hv.SONGS_DIR, victim))
check("先确认真的删掉了", victim in hv.song_files(), False)
hv.ensure_data_files()                         # 重新打开软件
check("★ 删掉的那首没有回来", victim in hv.song_files(), False)
check("其余曲谱原封不动", len(hv.song_files()), len(hv.SAMPLE_SONGS) - 1)
hv.ensure_data_files()
check("再启动一次还是不回来", victim in hv.song_files(), False)

print("[5] ★ 老环境 + 全删光 → 目录保持为空")
sb = sandbox()
hv.ensure_data_files()
wipe_songs()
check("先确认清空了", hv.song_files(), [])
for _ in range(2):
    hv.ensure_data_files()
check("★ 全删光后再启动也不会补回来", hv.song_files(), [])
check("目录里真的一首都没有", [n for n in os.listdir(hv.SONGS_DIR)], [])

print("[6] 曲谱为空 → load_songs 给占位曲谱（不崩）")
sb = sandbox()
hv.ensure_data_files()
wipe_songs()
ss = hv.load_songs()
check("有一首占位，不会崩", len(ss), 1)
check("标题看得懂（提示文件夹是空的）", "空" in ss[0].title, True)
check("占位曲谱带音符（不是空壳）", len(ss[0].notes) > 0, True)
check("不再是旧的「内置示例」", ss[0].title == "内置示例", False)

print("[7] ★ 占位曲谱只活在内存里 → 不写盘")
check("★ 曲谱文件夹仍然是空的", hv.song_files(), [])
check("目录里没有任何文件", os.listdir(hv.SONGS_DIR), [])

print("[8] song_files() 的行为")
sb = sandbox()
os.makedirs(hv.SONGS_DIR, exist_ok=True)
write_song("b曲.txt")
write_song("a曲.txt")
with open(os.path.join(hv.SONGS_DIR, "说明.md"), "w", encoding="utf-8") as f:
    f.write("不算曲谱")
with open(os.path.join(hv.SONGS_DIR, "空文件夹占位"), "w", encoding="utf-8") as f:
    f.write("也不算")
check("只认 .txt 且按名字排序", hv.song_files(), ["a曲.txt", "b曲.txt"])
hv.SONGS_DIR = os.path.join(sb, "根本没这个目录")
check("目录不存在时返回空列表、不抛异常", hv.song_files(), [])

print("[9] 自定义曲谱目录（换过 songs_dir）为空时同样不补")
sb = sandbox()
hv.ensure_data_files()                         # 先让它成为"老环境"
wipe_songs()
custom = os.path.join(sb, "我的曲谱夹")
os.makedirs(custom, exist_ok=True)
hv.SONGS_DIR = custom                          # 模拟 config.songs_dir 指到别处
hv.ensure_data_files()
check("新指向的空目录没被塞示例", hv.song_files(), [])
ss = hv.load_songs()
check("列表给占位曲谱", len(ss), 1)

print()
print("结果: %s" % ("全部通过 ✓" if ok else "有失败 ✗"))
sys.exit(0 if ok else 1)
