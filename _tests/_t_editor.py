# -*- coding: utf-8 -*-
"""曲谱编辑器（录音 / 撤销 / 保存 / 重载）离屏功能测试"""
import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\AI\DF Harmonica\harmonica-visualizer")

import harmonica_visualizer as hv              # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox   # noqa: E402

TMP = tempfile.mkdtemp(prefix="hv_editor_test_")
hv.BASE_DIR = TMP
hv.CONFIG_PATH = os.path.join(TMP, "config.json")
hv.SONGS_DIR = os.path.join(TMP, "songs")
os.makedirs(hv.SONGS_DIR, exist_ok=True)
for name, text in hv.SAMPLE_SONGS.items():
    with open(os.path.join(hv.SONGS_DIR, name), "w", encoding="utf-8") as f:
        f.write(text)

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)

app = QApplication(sys.argv)
cfg = hv.load_config()
songs = hv.load_songs()
ov = hv.Overlay(cfg, songs)
panel = hv.PanelWindow(ov)
ov.panel = panel
ed = hv.SongEditor(ov)
ov.editor = ed
ok = True


def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print(("  ✓ " if good else "  ✗ ") + label, "->", got, "" if good else ("(期望 %s)" % (want,)))


print("[1] 录音：1 2 ^3 ^4 5  再按住左键弹 b 音")
ov.set_recording(True)
for ch, st in [(0, 0), (1, 0), (2, 3), (3, 3), (4, 0)]:
    ov.held_mods = [hv.MOD_ROLES[st - 1]] if st else []
    ov._record_note(ch)
ov.held_mods = ["降调"]
ov._record_note(5)
check("文本框内容", repr(ed.text.toPlainText()), "'1 2 ^3 ^4 5 b6\\n'")
check("音数", ed.note_tokens(), ["1", "2", "^3", "^4", "5", "b6"])

print("[2] 撤销两个音")
ed.undo_one()
ed.undo_one()
check("撤销后", ed.note_tokens(), ["1", "2", "^3", "^4"])

print("[3] 继续录到超过一行（%d 个音换行）" % hv.REC_WRAP)
while len(ed.note_tokens()) < hv.REC_WRAP + 3:
    ov._record_note(0)
lines = [ln for ln in ed.text.toPlainText().split("\n") if ln.strip()]
check("行数", len(lines), 2)
check("第一行音数", len(lines[0].split()), hv.REC_WRAP)
check("第二行音数", len(lines[1].split()), 3)

print("[4] 结束录音 → 界面恢复可编辑")
ov.set_recording(False)
check("可编辑", ed.text.isReadOnly(), False)
check("按钮文字", ed.rec_btn.text(),
      "● 开始录音（%s）" % hv.hotkey_text(cfg, "toggle_record"))

print("[5] 保存到曲谱库")
ed.name_edit.setText("测试曲目")
before = len(ov.songs)
ed.save_to_library()
path = os.path.join(hv.SONGS_DIR, "测试曲目.txt")
check("文件已写入", os.path.exists(path), True)
check("曲谱数 +1", len(ov.songs), before + 1)
check("当前曲谱", ov.song.title, "测试曲目")
check("音数一致", len(ov.song.notes), len(ed.note_tokens()))
print("      文件内容:", repr(open(path, encoding="utf-8").read()))

print("[6] 文件名安全 & 载入当前曲谱")
ed.name_edit.setText('a/b:c*?"<>|')
ed.save_to_library()
check("非法字符被替换", os.path.exists(
    os.path.join(hv.SONGS_DIR, hv.safe_filename('a/b:c*?"<>|') + ".txt")), True)
check("替换后的文件名", hv.safe_filename('a/b:c*?"<>|') + ".txt", "a_b_c_.txt")
ed.load_current()
check("载入的是当前曲谱", ed.note_tokens()[:4], ["1", "2", "^3", "^4"])

print("[7] 在“载入的旧谱（带注释）”后面继续录音 → 不会写到注释行里")
with open(os.path.join(hv.SONGS_DIR, "带注释.txt"), "w", encoding="utf-8") as f:
    f.write("BPM=90\nTITLE=带注释\n// 这是一行注释\n1 1 5 5\n")
ov.reload_songs(select_title="带注释")
ed.load_current()
ov.set_recording(True)
ov.held_mods = []
ov._record_note(4)
ov.set_recording(False)
print("      文本:", repr(ed.text.toPlainText()))
check("注释行没被污染",
      any(l.strip() == "// 这是一行注释" for l in ed.text.toPlainText().split("\n")), True)
check("接在原有音符行末尾", ed.text.toPlainText().strip().split("\n")[-1], "1 1 5 5 5")

print("[7b] 文本只有注释行时录音 → 新起一行，不写进注释里")
ed.text.setPlainText("// 只有注释\n")
ov.set_recording(True)
ov.held_mods = []
ov._record_note(1)
ov.set_recording(False)
print("      文本:", repr(ed.text.toPlainText()))
check("注释行完好", ed.text.toPlainText().strip().split("\n")[0], "// 只有注释")
check("音符单独一行", ed.text.toPlainText().strip().split("\n")[1], "2")
check("能被解析出 1 个音", len(hv.parse_song(ed.text.toPlainText(), "t").notes), 1)

print("[8] 空内容保存 → 不产生文件（只弹提示）")
n_before = len(os.listdir(hv.SONGS_DIR))
ed.text.setPlainText("")
ed.save_to_library()
check("没有新增文件", len(os.listdir(hv.SONGS_DIR)), n_before)

print("[9] 录音视图能画出来（离屏渲染 + 像素检查）")
ov.set_recording(True)
ov.held_mods = ["升调"]
for ch in (0, 2, 4, 7):
    ov._record_note(ch)
ov.resize(760, 560)
ov.show()
app.processEvents()
img = ov.grab().toImage()
w, h = img.width(), img.height()
blues = reds = 0
for y in range(0, h, 2):
    for x in range(0, w, 2):
        c = img.pixelColor(x, y)
        if c.blue() - c.red() > 40 and c.blue() > 150:
            blues += 1
        if c.red() > 170 and c.red() - c.green() > 60 and c.red() - c.blue() > 60:
            reds += 1
check("录音视图里有蓝色音符块", blues > 50, True)
check("录音视图里有红色“录音中”圆点", reds > 5, True)
img.save(os.path.join(TMP, "rec_view.png"))
print("      截图:", os.path.join(TMP, "rec_view.png"))
check("录音时不会自动弹编辑器（不挡游戏）", ed.isVisible(), False)
ov.set_recording(False)

print("[10] 编辑器窗口能正常显示（离屏）")
ed.show_editor()
app.processEvents()
check("编辑器可见", ed.isVisible(), True)
check("状态栏有音数", "共" in ed.status.text(), True)

print("[11] 面板多了“添加曲谱”按钮，且能点中")
panel.resize(168, 560)
panel.grab()                       # grab 会触发 paintEvent，填充 _hit_buttons
acts = [a for _, a in panel._hit_buttons]
check("按钮列表", acts, ["toggle_visible", "editor", "toggle_adjust", "toggle_play",
                        "next_song", "toggle_panel", "quit"])
r = [rr for rr, a in panel._hit_buttons if a == "editor"][0]
check("按钮在面板内", 0 <= r.left() and r.right() <= panel.width(), True)
check("按钮标签", panel._button_label("editor")[0], "添加曲谱")
ov.recording = True
check("录音时按钮变醒目", panel._button_label("editor")[1], True)
ov.recording = False

print("[12] 编辑器打开/关闭（面板按钮与 F11 走同一个动作）")
ed.hide()
app.processEvents()
ov.do_action("editor")
app.processEvents()
check("打开", ed.isVisible(), True)
ov.do_action("editor")
app.processEvents()
check("再点一次关闭", ed.isVisible(), False)
check("F11 已注册", cfg["hotkeys"]["editor"], "shift+f11")
check("F12 已注册", cfg["hotkeys"]["toggle_record"], "shift+f12")

print("[13] 热键 F5 → 静默保存（游戏在前台也能按，一个框都不弹）")
check("F5 已注册", cfg["hotkeys"].get("save_song"), "shift+f5")
ed.text.setPlainText("")
ed.hide()                                    # 模拟"用户从没打开过编辑器"的真实场景
n0 = len(os.listdir(hv.SONGS_DIR))
ov.set_recording(True)
ov.held_mods = ["升调"]                       # 相当于按住鼠标右键 → 高音
ov._record_note(0)
ov._record_note(2)
ed.name_edit.setText("测试曲目")              # 这个名字库里已经有了 → 应该自动换名
ov._toast = None
ov.do_action("save_song")
check("录音中按 F5 会先结束录音", ov.recording, False)
check("重名自动改成《测试曲目2》",
      os.path.exists(os.path.join(hv.SONGS_DIR, "测试曲目2.txt")), True)
check("曲名框同步更新", ed.name_edit.text(), "测试曲目2")
check("文件多了一个", len(os.listdir(hv.SONGS_DIR)), n0 + 1)
check("叠加层给了提示（不切窗口也能看到结果）", bool(ov._toast), True)
print("      提示:", ov._toast[1] if ov._toast else None)
txt2 = open(os.path.join(hv.SONGS_DIR, "测试曲目2.txt"), encoding="utf-8").read()
print("      文件内容:", repr(txt2))
check("内容是刚录的两个高音", hv.clean_song_body(txt2).split(), ["^1", "^3"])

print("[13b] 没有任何音符时按 F5 → 不写文件，只提示")
ed.text.setPlainText("")
n1 = len(os.listdir(hv.SONGS_DIR))
ov._toast = None
ov.do_action("save_song")
check("没新增文件", len(os.listdir(hv.SONGS_DIR)), n1)
check("给出了提示", bool(ov._toast), True)
print("      提示:", ov._toast[1] if ov._toast else None)

print("\n[14] 撤销要让叠加层上那串音符块跟着消失（v8.1 bug 修复）")
ov.set_recording(True)
ov.held_mods = []
for ch in (0, 1, 2, 3, 4):
    ov._record_note(ch)                         # 5 个音，本音
ov.rec_log = list(ov.rec_log)                   # 拷贝一份防止 _record_note 共用引用
ov.rec_count = 5
check("已录 5 个音", ov.rec_count, 5)
check("overlay 串里也有 5 个", len(ov.rec_log), 5)
ed.undo_one()
ed.undo_one()
check("文本里剩 3 个", len(ed.note_tokens()), 3)
check("叠加层的 rec_count 也跟着减到 3", ov.rec_count, 3)
check("叠加层里那串音符块也只显示 3 个", len(ov.rec_log), 3)
# 撤销非音符的记号（比如 "- -" 延长号）应该不动 rec_count
ed.undo_one()                                   # 文本最后一个 "1" 没了
ed.undo_one()
check("撤销 2 个真音符后 rec_count=1", ov.rec_count, 1)
ov.set_recording(False)

print("[14b] 清空文本 → 叠加层上那一串也清空")
ov.set_recording(True)
for ch in (5, 6, 7):
    ov._record_note(ch)
check("已录 3 个音", ov.rec_count, 3)
ed.clear_all()
check("文本清空", len(ed.note_tokens()), 0)
check("rec_count 也归零", ov.rec_count, 0)
check("rec_log 也归零", len(ov.rec_log), 0)
ov.set_recording(False)

print("[15] 六色音调：半音+降调=#b（黄）、半音+升调=#^（红）")
check("纯 1 个字符的 token", hv.note_token(0, 0), "1")
check("降调", hv.note_token(1, 1), "b2")
check("半音", hv.note_token(2, 2), "#3")
check("升调", hv.note_token(3, 3), "^4")
check("半音+降调（黄）", hv.note_token(0, 4), "#b1")
check("半音+升调（红）", hv.note_token(1, 5), "#^2")
check("state 4 配色（黄）", hv.STATE_STYLE[4]["fill"].red(), 0xF2)
check("state 5 配色（红）", hv.STATE_STYLE[5]["fill"].red(), 0xE0)
check("灯带数组长度为 6", len(hv.STRIP_COLORS), 6)
check("combo_state(\"#b\")→4", hv.combo_state("#b"), 4)
check("combo_state(\"b#\")→4（两种顺序都认）", hv.combo_state("b#"), 4)
check("combo_state(\"#^\")→5", hv.combo_state("#^"), 5)
check("combo_state(\"^#\")→5", hv.combo_state("^#"), 5)
check("combo_state(\"\")→0", hv.combo_state(""), 0)
# 整曲解析：写一段带组合音调的，parse_song 拿回来 state 对得上
song = hv.parse_song("1 #b2 #^3 ^4 b5 #6 #^7 b#1", "t")
got = [(s, d, ch, st) for s, d, ch, st in song.notes]
want = [(0.0, 1.0, 0, 0), (1.0, 1.0, 1, 4), (2.0, 1.0, 2, 5),
        (3.0, 1.0, 3, 3), (4.0, 1.0, 4, 1), (5.0, 1.0, 5, 2),
        (6.0, 1.0, 6, 5), (7.0, 1.0, 0, 4)]
check("整曲解析（顺序无关、state 正确）", got, want)

print("[15b] 录音能直接生成 #b / #^ token")
ov.set_recording(True)
ov.held_mods = ["半音", "降调"]                 # 中键+左键
ov._record_note(0)
ov.held_mods = ["半音", "升调"]                 # 中键+右键
ov._record_note(1)
ov.held_mods = ["半音"]
ov._record_note(2)
ov.held_mods = []                                # 松开所有修饰键
ov.set_recording(False)
check("编辑器里出现 #b / #^ / #", ed.note_tokens(), ["#b1", "#^2", "#3"])
check("current_state 还原到 0", ov.current_state(), 0)

print("[15c] current_state 优先级：半音 + 双方向键 → 看最近按的方向")
ov.held_mods = ["降调", "半音", "升调"]          # 升调最新
check("升调最新 → 半音+升调=红", ov.current_state(), 5)
ov.held_mods = ["升调", "半音", "降调"]          # 降调最新
check("降调最新 → 半音+降调=黄", ov.current_state(), 4)
ov.held_mods = ["半音", "降调"]
check("半音+降调（黄）", ov.current_state(), 4)
ov.held_mods = ["半音", "升调"]
check("半音+升调（红）", ov.current_state(), 5)
ov.held_mods = ["半音"]
check("单独半音（紫）", ov.current_state(), 2)
ov.held_mods = []

print("\n结果:", "全部通过 ✓" if ok else "存在失败 ✗")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ok else 1)
