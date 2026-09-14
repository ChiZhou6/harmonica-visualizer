# -*- coding: utf-8 -*-
"""
三角洲行动 · 口琴可视化曲谱 (Delta Force Harmonica Visualizer) v8

悬浮在屏幕最顶层的半透明曲谱窗口。由**两个窗口**组成：

  ② 音符层（全宽）——始终鼠标穿透（WS_EX_TRANSPARENT），绝不影响游戏点击；
                    画整块背景板 + 8 条音符通道 + 底部灯带 + 右上角提示气泡。
  ② 左侧面板（独立小窗）——正常命中测试，**会吃掉落在它上面的点击**，点击不会漏给游戏；
                    画控制面板：曲目信息、音调指示、输入检测、曲谱列表、热键按钮。
                    带 WS_EX_NOACTIVATE，点击面板不会抢走游戏焦点。

  ⚠️ 为什么必须拆成两个窗口：实测确认 `WM_NCHITTEST` 返回 HTTRANSPARENT 的"按区域穿透"
     只能在**同一进程内**把鼠标消息让给下层窗口，**跨进程（也就是游戏本体）无效**。
     所以音符区只能用 WS_EX_TRANSPARENT 做整窗穿透；面板要能点，就必须是另一个正常窗口。

模式（v6 起只有一种，即原先的"主导模式"）：
  音符块不自动下落，全部从下往上堆叠。按下"最靠近底部的那一个"块对应的按键即可
  消除它，随后整叠音符带着缓动下落一层，如此往复。不需要精确节奏与时长，
  导入曲谱只需按顺序记录音符。

音符块：圆角药丸 + 按键字母（z x c v b n m ,）——块上的字母就是该按的键。
  块越长表示这个音要按得越久（长按）。块的颜色表示需要配合哪个修饰键：
    暖白 = 本音（不按修饰键）    绿 = 降调（游戏内长按鼠标左键）
    紫   = 半音（长按鼠标中键）  蓝 = 升调（长按鼠标右键）
    黄   = 半音+降调（中键+左键一起按）
    红   = 半音+升调（中键+右键一起按）

底部灯带（对齐 + 音调指示）：
  窗口最底部一条细灯带，用于对齐游戏口琴按键的上沿（灯带即"按键时刻"基准线）。
  颜色跟随你当前按住的修饰键实时变化，与音符块配色一致。
  界面内不绘制琴键数字与键帽——对齐时直接看游戏原版口琴 UI。

安全设计（直读按键，无钩子、无注入、无内存读取）：
  - 不安装任何键盘/鼠标钩子（不调用 SetWindowsHookEx）
  - 不模拟按键、不发送任何输入事件（不调用 SendInput / mouse_event）
  - 不读取游戏内存、不注入游戏进程、不联网
  - 只调用 user32.GetAsyncKeyState 读取按键与鼠标键状态（面板按钮、热键、灯带配色）
  - 悬浮层是普通分层窗口（WS_EX_LAYERED），由 DWM 合成
  - 如需彻底静默：把 config.json 的 keyboard_monitor 设为 false（完全不读取键鼠）

热键（全局有效，均可在 config.json 中改）：
  ⚠️ 全部 F 区热键都要**按住 Shift** 再按，避免和游戏里的 F 键抢键。
  Shift+F6      显示 / 隐藏全部窗口（游戏中防遮挡视野，一键收起 / 一键回来）
  Shift+F7      切换下一首曲谱
  Shift+F8      锁定 / 调整模式（拖动、缩放以对齐灯带与游戏按键）
  Shift+F9      从头重来
  Shift+F10     面板可点击 / 面板也鼠标穿透
  Shift+F11     打开 / 关闭【曲谱编辑器】（添加、录制、编辑、导出曲谱）
  Shift+F12     开始 / 结束 录音（弹一遍按键即可录成曲谱）
  Shift+F5      切换 经典模式 / 跟随演奏模式
  Shift+F3      保存录音为曲谱（静默，不弹框，游戏在前台也能按）
  Ctrl+Alt+Q    退出
  想换成别的键 / 加备用键：改 config.json 的 hotkeys。
  例："toggle_visible": "shift+f6"（| = 备选键，+ = 同时按下）

曲谱编辑器（v7 新增）：
  面板上的「✚ 添加曲谱」按钮或 Shift+F11 打开。窗口里可以：
    · 录制：点「● 开始录音」或按 Shift+F12，然后在游戏里按顺序弹一遍
      （z x c v b n m , ），每个音都会实时写进文本框；
      按住鼠标左/中/右键再弹 = 绿/紫/蓝（降调/半音/升调），和游戏里一致。
    · 撤销：点「撤销一个音」或 Ctrl+Z。
    · 保存到曲谱库：写进曲谱文件夹，面板列表立刻刷新。
    · 导出 / 导入：存成 / 读取任意位置的 .txt 曲谱文件。
    · 编辑：直接改文本框里的内容（数字与字母都可），或「载入当前曲谱」再改。
    · 曲谱文件夹：点「曲谱文件夹…」可换存放位置；「打开文件夹」直接在资源管理器里打开。

曲谱文件夹（v8 新增可自定义）：
  默认 = 程序旁边的 songs 文件夹（config.songs_dir 为空）。
  config.songs_dir 也可以填绝对路径或相对 exe 的相对路径 → 曲谱存到别处。
  分享给朋友时把整个文件夹（exe + songs + config.json）打包发过去即可，开箱即用。

面板曲谱列表：
  放不下时右侧自动出现滚动条，鼠标滚轮 / 拖滑块 / 点轨道都能翻页；
  布局会按面板高度自适应（按钮自动变矮），任何高度下都不会互相挤占。
"""

import ctypes
import json
import math
import os
import re
import sys
import time

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QEvent
from PySide6.QtGui import (QColor, QPainter, QPen, QFont, QFontMetrics, QPainterPath,
                           QBrush, QRadialGradient, QShortcut, QKeySequence, QTextCursor)
from PySide6.QtWidgets import (QApplication, QWidget, QLineEdit, QPlainTextEdit,
                               QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                               QFileDialog, QMessageBox)

if getattr(sys, "frozen", False):        # 打包成 exe 后：读写 exe 所在目录
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DEFAULT_SONGS_DIR = os.path.join(BASE_DIR, "songs")
SONGS_DIR = DEFAULT_SONGS_DIR          # 运行期实际使用的曲谱目录（见 apply_songs_dir）


def resolve_songs_dir(cfg=None):
    """算出曲谱文件夹在哪。

    config.songs_dir 留空 = 默认（exe / 源码旁边的 songs 文件夹，跟着程序走）；
    填相对路径 = 相对 exe 所在目录；填绝对路径 = 用那个文件夹。
    """
    raw = ""
    if isinstance(cfg, dict):
        raw = str(cfg.get("songs_dir") or "").strip()
    if not raw:
        return DEFAULT_SONGS_DIR
    if not os.path.isabs(raw):
        raw = os.path.join(BASE_DIR, raw)
    return os.path.normpath(raw)


def apply_songs_dir(cfg=None):
    """把 config 里的曲谱目录生效（目录不存在就建出来），返回最终路径"""
    global SONGS_DIR
    SONGS_DIR = resolve_songs_dir(cfg)
    try:
        os.makedirs(SONGS_DIR, exist_ok=True)
    except Exception as e:
        print("[曲谱] 无法创建曲谱文件夹:", SONGS_DIR, e)
        SONGS_DIR = DEFAULT_SONGS_DIR
    return SONGS_DIR


def is_default_songs_dir(path):
    try:
        return os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(DEFAULT_SONGS_DIR))
    except Exception:
        return False


# 首次运行时自动生成的示例曲谱
SAMPLE_SONGS = {
    "小星星.txt": """BPM=90
TITLE=小星星
// 数字 = 简谱音高，与游戏按键一一对应：1=z 2=x 3=c 4=v 5=b 6=n 7=m 8=,
// 每个音 1 拍，后面的 - 表示延长 1 拍；| 只是小节线，随便写
1 1 5 5 6 6 5 -
4 4 3 3 2 2 1 -
5 5 4 4 3 3 2 -
5 5 4 4 3 3 2 -
1 1 5 5 6 6 5 -
4 4 3 3 2 2 1 -
""",
    "欢乐颂.txt": """BPM=100
TITLE=欢乐颂
3 3 4 5 | 5 4 3 2 | 1 1 2 3 | 3 - 2 -
3 3 4 5 | 5 4 3 2 | 1 1 2 3 | 2 - 1 -
""",
    "音域与变调练习.txt": """BPM=80
TITLE=音域与变调练习
// 本音（白）：八个键全弹一遍，8 = 高音1（, 键）
1 2 3 4 5 6 7 8 -
// 降调（绿）：长按鼠标左键再弹
b1 b2 b3 b4 b5 b6 b7 -
// 半音（紫）：长按鼠标中键再弹
#1 #2 #3 #4 #5 #6 #7 -
// 升调（蓝）：长按鼠标右键再弹
^1 ^2 ^3 ^4 ^5 ^6 ^7 -
// 半音+降调（黄）：同时按住鼠标中键 + 左键再弹
#b1 #b2 #b3 #b4 #b5 #b6 #b7 -
// 半音+升调（红）：同时按住鼠标中键 + 右键再弹
#^1 #^2 #^3 #^4 #^5 #^6 #^7 -
""",
    "父亲.txt": """TITLE=父亲（筷子兄弟）
// =====================================================================
// 《父亲》键盘谱（由网络流传的键盘谱图片逐音转写 · 已按原图色块逐音复核）
//
// 记号对照：
//   z x c v b n m = 简谱 1 2 3 4 5 6 7
//   前缀 ^  = 按住鼠标右键（原图写作"高音"，浅蓝色块）
//   无前缀  = 不按鼠标    （原图写作"中音"，橙色块）
//
// ⚠️ 复核说明：原图的"高音"标记有两处线索——数字头上的小圆点、以及
//    按键块的底色。这张谱里少数音"漏打了圆点"，但按键块是蓝色的，
//    本文件一律以【按键块底色】为准（蓝=高音）。
// =====================================================================

// 1. 总是向你索取 却不曾说谢谢你
^1 5 ^1 ^3 ^4 ^3 | ^2 ^1 ^1 5 ^1 ^2 ^3

// 2. 直到长大以后 才懂得你不容易
^1 5 ^1 ^3 ^4 ^3 | ^2 ^1 ^3 ^2 ^2 ^1 ^1

// 3. 每次离开总是 装作轻松的样子
^1 5 ^1 ^3 ^4 ^3 | ^2 ^1 ^6 ^5 ^5 ^4 ^3

// 4. 微笑着说回去吧 转身泪湿眼底
^1 5 ^1 ^3 ^4 ^3 | ^2 ^1 ^3 ^2 ^2 ^1 ^1

// 5. 多想和从前一样 牵你温暖手掌
^1 6 ^6 ^6 ^5 ^3 | ^3 ^3 ^4 ^5 ^1 ^5 ^3

// 6. 可是你不在我身旁 托清风捎去安康
^1 7 6 ^6 ^6 ^7 ^5 | ^5 ^5 ^6 ^5 ^4 ^3 ^3 ^2

// 7. 时光时光慢些吧 不要再让你变老了
6 7 ^1 ^1 ^1 ^1 7 | 6 7 7 7 7 ^3 ^2 ^1

// 8. 我愿用我一切 换岁月长留
6 7 ^1 ^1 ^1 ^1 ^1 | 7 6 7 5

// 9. 一生要强的爸爸 我能为你做些什么
6 7 ^1 ^1 ^1 ^1 7 | 6 7 7 7 7 ^3 7 ^1

// 10. 微不足道的关心 收下吧
6 7 ^1 ^1 ^1 ^3 ^2 7 6 6
""",
    "See You Again.txt": """BPM=90
TITLE=See You Again
// 全谱面 9 段（^ 前缀 = 高音，按住鼠标右键弹）
// ===== 第一段 =====
5 ^2 ^1 5 | ^1 ^2 ^3 ^2 ^1 ^2 | 5 ^2 ^1 5
// ===== 第二段 =====
1 3 5 6 5 | 1 2 2 1 3
// ===== 第三段 =====
3 5 6 7 6 5 3 2 2 1 2 2 3 1
// ===== 第四段 =====
1 3 5 6 5 | 1 2 2 1 3
// ===== 第五段 =====
2 3 5 6 ^1 ^2 ^3 ^2 ^1 6 ^1 ^2 ^2 ^1 ^1
// ===== 第六段 =====
6 ^1 ^2 ^2 ^1 ^1
// ===== 第七段 =====
^7 ^6 ^5 | ^7 ^6 ^7 ^6 ^5 ^3
// ===== 第八段 =====
5 6 ^1 ^2 ^3 | ^2 ^3 | ^2 ^3
// ===== 第九段 =====
^2 ^3 ^5 | ^3 ^2 ^1 6 ^1 ^2 ^1
""",
}


def ensure_data_files():
    """首次运行（含 exe）时自动生成 config.json 与示例曲谱"""
    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[config] 写入失败:", e)
    try:
        os.makedirs(SONGS_DIR, exist_ok=True)
        for name, text in SAMPLE_SONGS.items():
            path = os.path.join(SONGS_DIR, name)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
    except Exception as e:
        print("[songs] 写入失败:", e)

# ---------------------------------------------------------------- 常量

# 8 个通道对应的游戏按键（音符块上直接显示这些字符）
KEY_LABELS = ["z", "x", "c", "v", "b", "n", "m", ","]
# 默认按键绑定（config.json 的 note_keys 可改）
DEFAULT_NOTE_KEYS = ["z", "x", "c", "v", "b", "n", "m", "comma"]
# 键位字符 -> 通道下标 0~7（Dr-hydra 曲谱库的谱面用大写字母 + 逗号，解析时统一转小写）
KEY_INDEX = {k: i for i, k in enumerate("zxcvbnm,")}

# 六种音调：填充色 / 文字色
# 降调=绿、半音=紫、升调=蓝（与游戏内长按鼠标左/中/右键时灯带颜色一致）
# 半音还能和其他修饰键一起按：半音+降调=黄、半音+升调=红
STATE_STYLE = [
    dict(fill=QColor(0xF0, 0xEA, 0xDB), text=QColor(0x3B, 0x37, 0x2E)),   # 0 本音
    dict(fill=QColor(0x22, 0xC5, 0x5E), text=QColor(0xFF, 0xFF, 0xFF)),   # 1 降调（绿）
    dict(fill=QColor(0xA8, 0x55, 0xF7), text=QColor(0xFF, 0xFF, 0xFF)),   # 2 半音（紫）
    dict(fill=QColor(0x4C, 0x8D, 0xF6), text=QColor(0xFF, 0xFF, 0xFF)),   # 3 升调（蓝）
    dict(fill=QColor(0xF2, 0xC5, 0x1F), text=QColor(0x3B, 0x37, 0x2E)),   # 4 半音+降调（黄）
    dict(fill=QColor(0xE0, 0x3E, 0x3E), text=QColor(0xFF, 0xFF, 0xFF)),   # 5 半音+升调（红）
]
# 灯带颜色：本音=白、降调=绿、半音=紫、升调=蓝、半音+降调=黄、半音+升调=红
STRIP_COLORS = [QColor(0xFF, 0xFF, 0xFF), QColor(0x22, 0xC5, 0x5E),
                QColor(0xA8, 0x55, 0xF7), QColor(0x4C, 0x8D, 0xF6),
                QColor(0xF2, 0xC5, 0x1F), QColor(0xE0, 0x3E, 0x3E)]

# 谱面上的前缀记号：
#   0 本音 → ""      1 降调 → b      2 半音 → #      3 升调 → ^
#   4 半音+降调 → #b   5 半音+升调 → #^
# 解析时**两种顺序都认**（#b / b# 都等于 4），免得别人手写谱子时写反了被跳过。
STATE_TOKEN_PREFIX = {0: "", 1: "b", 2: "#", 3: "^", 4: "#b", 5: "#^"}
PREFIX_CHARS = "b#^"
MOD_ROLES = ["降调", "半音", "升调"]
STATE_NAMES = ["本音", "降调", "半音", "升调", "半音+降调", "半音+升调"]
# 面板上的短名（一行 3 个、每个最多 3 个字）
STATE_SHORT = ["本音", "降调", "半音", "升调", "半+降", "半+升"]
# 每种状态需要同时按住哪些修饰键
STATE_MODS = [[], ["降调"], ["半音"], ["升调"], ["半音", "降调"], ["半音", "升调"]]
# 面板 6 色块的视觉顺序：上排按方向（降/本/升），下排按"半音 × 方向"（半+降/半音/半+升）
# 元素 = 该位置上画的是哪个 state 的色块/短名
CHIP_LAYOUT = [1, 0, 3,   4, 2, 5]            # state 顺序：降/本/升 / 半+降/半音/半+升


def combo_state(pref):
    """把谱面上的前缀字符（如 "#b" / "^" / ""）翻译成音调状态 0~5"""
    chars = set(pref)
    if "#" in chars:                       # 带半音 → 再看方向
        if "b" in chars:
            return 4
        if "^" in chars:
            return 5
        return 2
    if "b" in chars and "^" in chars:      # 降调和升调同时写，罕见 → 按升调
        return 3
    if "b" in chars:
        return 1
    if "^" in chars:
        return 3
    return 0

# 修饰键在本界面上的显示名
KEY_DISPLAY = {
    "mouse_left": "鼠标左键", "mouse_right": "鼠标右键", "mouse_middle": "鼠标中键",
    "mouse4": "鼠标侧键1", "mouse5": "鼠标侧键2",
    "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win",
    "lctrl": "左Ctrl", "rctrl": "右Ctrl", "lalt": "左Alt", "ralt": "右Alt",
    "lshift": "左Shift", "rshift": "右Shift",
    "left": "←", "right": "→", "up": "↑", "down": "↓",
    "space": "空格", "enter": "回车", "tab": "Tab", "backspace": "退格",
}

# 面板按钮：一行一个（列表里每项是"一行按钮"，一行可放多个）
# 第一个就是"隐藏窗口"——游戏里最常用的动作，放最上面一眼能看到它的热键
PANEL_ROWS = [
    [("toggle_visible", "隐藏窗口")],
    [("editor", "✚ 添加曲谱")],
    [("toggle_adjust", "调整窗口")],
    [("toggle_play", "从头重来")],
    [("toggle_mode", "跟随演奏")],
    [("next_song", "下一首")],
    [("toggle_panel", "面板穿透")],
    [("quit", "退出程序")],
]

# 录音时每行最多写多少个音（纯粹为了好看，谱面允许任意换行）
REC_WRAP = 16
# 叠加层上"最近弹的一串音"最多留多少个（防止超长曲谱吃内存）
REC_KEEP = 200
REC_KEEP_WANT = 120

DEFAULT_CONFIG = {
    "opacity": 0.94,
    "bg_alpha": 150,
    "hit_line_offset": 10,            # 灯带距窗口底边的距离(像素)
    "panel_width": 168,               # 左侧控制面板宽度(像素)
    "panel_interactive": True,        # 面板可点击；false = 面板也鼠标穿透
    # 曲谱文件夹：留空 = 程序旁边的 songs 文件夹；也可写别的路径（如 D:\\我的曲谱）
    "songs_dir": "",
    "loop": True,
    "keyboard_monitor": True,         # false = 完全不读取键鼠（纯视觉，热键也会失效）
    "leader_strict_modifier": False,  # 是否必须同时按住修饰键才算弹对
    # 演奏模式：classic = 经典（音符堆叠消除）；follow = 跟随演奏（音符按时值下落，音游式）
    "mode": "classic",
    # —— 跟随演奏模式参数 ——
    "follow_speed": 200.0,            # 音符下落速度（像素/秒）
    "follow_lead": 2.0,               # 倒计时结束后，第一个音到判定线还要多久（秒）
    "follow_window": 0.20,            # 判定窗口（秒，太早/太晚都不算）
    # 长音（很长的矩形）：超过这个拍数就要求"按住不放"才算完成
    "hold_min_beats": 1.5,            # 1.5 拍以上算长音（想全部改成"按一下即消"就调到很大，如 999）
    "hold_grace": 0.20,               # 按住期间手指短暂松开多久以内不算断（秒）
    "countdown_seconds": 3,           # 准备倒计时秒数
    # 8 个通道绑定的按键（顺序 = 通道 1~8）。逗号键写 comma
    "note_keys": list(DEFAULT_NOTE_KEYS),
    # 游戏内：长按鼠标左键=降调、中键=半音、右键=升调
    "modifier_keys": {
        "降调": ["mouse_left"],
        "半音": ["mouse_middle"],
        "升调": ["mouse_right"],
    },
    "hotkeys": {
        # 值可以写多个备选键，用 | 隔开（任一组合按下都算）；同一个键位内用 + 表示"同时按下"
        # ⚠️ F 区热键统一加了 Shift 前缀（Shift+F3 / Shift+F5 ~ Shift+F12）：
        #    游戏里经常要用 F 键，不加修饰键容易抢键、误触发。
        # toggle_visible = 一键隐藏/恢复全部窗口（游戏中防遮挡视野）
        "toggle_visible": "shift+f6",
        "next_song": "shift+f7",
        "toggle_adjust": "shift+f8",
        "toggle_play": "shift+f9",
        "toggle_panel": "shift+f10",
        "editor": "shift+f11",
        "toggle_record": "shift+f12",
        "save_song": "shift+f3",
        "toggle_mode": "shift+f5",
        "quit": "ctrl+alt+q",
    },
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            # 旧版 config 里缺少新动作（如 editor / toggle_record）→ 从默认值补齐
            for section in ("hotkeys", "modifier_keys"):
                if isinstance(cfg.get(section), dict):
                    for k, v in DEFAULT_CONFIG[section].items():
                        cfg[section].setdefault(k, v)
            return cfg
        except Exception as e:
            print("[config] 读取失败，使用默认配置:", e)
    return json.loads(json.dumps(DEFAULT_CONFIG))


def format_combo(combo):
    """一个"组合键" -> 好看的名字。

    "ctrl+alt+q" -> "Ctrl+Alt+Q"；"shift+f6" -> "Shift+F6"
    """
    out = []
    for part in str(combo).split("+"):
        p = part.strip().lower()
        if not p:
            continue
        if p in KEY_DISPLAY:
            out.append(KEY_DISPLAY[p])
        else:
            out.append(p.upper() if len(p) <= 2 else p.title())
    return "+".join(out)


def format_hotkey(combo, joiner="/"):
    """"shift+f6|shift+f4" -> "Shift+F6/Shift+F4"（多个备选键用 joiner 连接，如 "shift+f6" -> "Shift+F6"）"""
    alts = [format_combo(a) for a in str(combo).split("|") if a.strip()]
    return joiner.join(a for a in alts if a)


def hotkey_text(cfg, action, joiner="/"):
    """取某个动作当前绑定的热键文字（给面板按钮、屏幕提示用）。

    好处：改了 config.json 里的热键，界面上显示的提示会自动跟着变，
    不会再出现"按钮写着 F6、实际要按 Shift+F6"这种对不上的情况。
    """
    combo = (cfg.get("hotkeys") or {}).get(action) if isinstance(cfg, dict) else None
    return format_hotkey(combo, joiner) if combo else ""


# ---------------------------------------------------------------- 曲谱解析

class Song:
    def __init__(self, title, bpm, notes, raw=""):
        self.title = title
        self.bpm = bpm
        self.notes = notes            # [(start_beat, dur_beat, channel0_7, state0_3)]
        self.total_beats = max((s + d for s, d, _, _ in notes), default=0)
        self.raw = raw                # 原始文本（编辑器"载入当前曲谱"用）


def parse_song(text, fallback_title="未命名"):
    meta = {"BPM": "90", "TITLE": fallback_title}
    notes = []
    t = 0.0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        head = line.split("=", 1)
        if len(head) == 2 and head[0].strip().upper() in ("BPM", "TITLE"):
            meta[head[0].strip().upper()] = head[1].strip()
            continue
        for tok in line.split():
            if tok == "|":
                continue
            if tok == "-":                 # 独立 "-"：延长前一个音 1 拍
                if notes:
                    s, d, ch, st = notes[-1]
                    notes[-1] = (s, d + 1, ch, st)
                t += 1
                continue
            pref = ""
            while tok and tok[0] in PREFIX_CHARS:   # 前缀可能是两个字符（如 #b）
                pref += tok[0]
                tok = tok[1:]
            state = combo_state(pref)
            ext = 0
            while tok.endswith("-"):       # 连写 "5-" / "5--"
                ext += 1
                tok = tok[:-1]
            if tok == "0":
                t += 1 + ext
                continue
            if tok in ("8", "i", "I"):
                ch = 7
            elif tok.isdigit() and 1 <= int(tok) <= 7:
                ch = int(tok) - 1
            else:
                print("[谱面] 无法识别的记号已跳过:", repr(tok))
                t += 1 + ext
                continue
            dur = 1 + ext
            notes.append((t, dur, ch, state))
            t += dur
    try:
        bpm = float(meta.get("BPM", 90))
    except ValueError:
        bpm = 90.0
    return Song(meta.get("TITLE", fallback_title), bpm, notes, text)


# ---------- Dr-hydra 曲谱库（Delta-Force-Harmonica）文本谱格式 ----------
# 来源 https://github.com/Dr-hydra/Delta-Force-Harmonica 的"人可演奏版文本谱"导出。
# 特征：每小节有「简谱 / 键位 / 节奏」三行，键位用 Z X C V B N M , 加修饰标记 + - #。
# 与我们自己的简谱格式（TITLE=/BPM= 头 + 数字 + 前缀 b # ^）完全不同，需单独解析。

def is_dfh_tab(text):
    """判断这段文本是不是 Dr-hydra 曲谱库的 tab 格式（而非我们自己的简谱格式）"""
    s = str(text)
    return "键位标记" in s or ("小节" in s and "键位" in s)


def rhythm_to_beats(tok):
    """把 Dr-hydra 谱面「节奏」列的记号翻译成拍数（beats）。

    这是仓库 src/score/measures.ts 里 durationLabel 的逆映射：
      1=4拍  2·=3拍  2=2拍  4·=1.5拍  4=1拍
      8·=0.75拍  8=0.5拍  16·=0.375拍  16=0.25拍  32=0.125拍
    其它（如 2.5b / 4.25b / 1.25b / 5b）是"非标准拍数"，b 后缀直接读数字。
    """
    tok = str(tok).strip()
    if tok.endswith("b"):
        try:
            return float(tok[:-1])
        except ValueError:
            return 1.0
    table = {
        "1": 4.0, "2·": 3.0, "2": 2.0, "4·": 1.5, "4": 1.0,
        "8·": 0.75, "8": 0.5, "16·": 0.375, "16": 0.25, "32": 0.125,
    }
    return table.get(tok, 1.0)


def dfh_key_state(mods):
    """把键位后面的修饰标记字符（+ - # 任意组合）翻译成音调状态 0~5。

    语义与我们的谱面完全一致：+ 升调 / - 降调 / # 半音，半音可与方向键组合。
    """
    s = set(str(mods))
    if "#" in s:
        if "-" in s:
            return 4          # 半音 + 降调（黄）
        if "+" in s:
            return 5          # 半音 + 升调（红）
        return 2              # 半音（紫）
    if "-" in s:
        return 1              # 降调（绿）
    if "+" in s:
        return 3              # 升调（蓝）
    return 0                  # 本音（白）


def dfh_key_token(tok):
    """解析一个键位 token（如 "N-#"、"X+"、",-"），返回 (通道 0~7, 音调 0~5)。"""
    tok = str(tok).strip()
    if not tok:
        return 0, 0
    idx = KEY_INDEX.get(tok[0].lower(), None)
    if idx is None:
        return 0, 0
    return idx, dfh_key_state(tok[1:])


def parse_dfh_tab(text, fallback_title="未命名"):
    """解析 Dr-hydra 曲谱库的文本谱，产出与 parse_song 相同的 Song 结构。

    注意：节奏列只含"音符持续拍数"，不含"音符之间的休止"，所以小节内音符按
    连续紧挨的方式排布、休止被忽略；但小节边界是精确的，误差不会跨小节累积。
    对主旋律谱来说这个近似足够，也是该文本格式能还原出的最佳时间轴。
    """
    title = fallback_title
    bpm = 90.0
    notes = []
    cur_beat = 0.0               # 绝对拍（从曲首算起）
    measure_len = 0.0
    in_measure = False
    keys = []                    # 当前小节的键位 token 列表
    rhythms = []                 # 当前小节的节奏 token 列表

    def flush_measure():
        nonlocal cur_beat, keys, rhythms, in_measure
        if keys:
            offset = 0.0
            for ktok, rtok in zip(keys, rhythms):
                ch, st = dfh_key_token(ktok)
                dur = rhythm_to_beats(rtok)
                notes.append((cur_beat + offset, dur, ch, st))
                offset += dur
        cur_beat += measure_len
        keys = []
        rhythms = []
        in_measure = False

    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        if "键位标记" in line:
            continue
        if "三角洲口琴谱" in line and not line.startswith("BPM"):
            title = line.split("—")[0].strip() or fallback_title
            continue
        m = re.match(r"^BPM\s+([\d.]+)", line)
        if m:
            bpm = float(m.group(1))
            continue
        m = re.match(r"^小节\s+\d+\s*\((\d+)/(\d+)\)(.*)$", line)
        if m:
            if in_measure:
                flush_measure()
            num, den = int(m.group(1)), int(m.group(2))
            measure_len = num * 4.0 / den
            rest = m.group(3)
            if "—" in rest:        # 空小节：直接推进整小节拍数
                cur_beat += measure_len
                in_measure = False
            else:
                in_measure = True
            continue
        if not in_measure:
            continue
        if line.startswith("键位"):
            keys = line[2:].strip().split()
        elif line.startswith("节奏"):
            rhythms = line[2:].strip().split()

    if in_measure:
        flush_measure()
    return Song(title, bpm, notes, text)


def safe_filename(name):
    """把曲名变成合法文件名（去掉 Windows 不允许的字符）"""
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", str(name)).strip(" .")
    return s or "未命名"


def note_token(ch, state):
    """(通道 0~7, 音调 0~5) -> 曲谱记号：如 state=3 ch=1 -> "^2"、state=5 ch=0 -> "#^1" """
    state = max(0, min(len(STATE_NAMES) - 1, int(state)))
    prefix = STATE_TOKEN_PREFIX[state]
    digit = str(int(ch) + 1) if 0 <= int(ch) < 7 else "8"
    return prefix + digit


def clean_song_body(text):
    """去掉 BPM=/TITLE= 头，只留注释与音符行"""
    out = []
    for line in str(text).splitlines():
        head = line.split("=", 1)
        if len(head) == 2 and head[0].strip().upper() in ("BPM", "TITLE"):
            continue
        out.append(line)
    return "\n".join(out).strip()


def load_songs():
    songs = []
    if os.path.isdir(SONGS_DIR):
        for name in sorted(os.listdir(SONGS_DIR)):
            if name.lower().endswith(".txt"):
                path = os.path.join(SONGS_DIR, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # 自动识别两种曲谱格式：Dr-hydra 曲谱库 tab 格式 / 我们自己的简谱格式
                    if is_dfh_tab(content):
                        songs.append(parse_dfh_tab(content, os.path.splitext(name)[0]))
                    else:
                        songs.append(parse_song(content, os.path.splitext(name)[0]))
                except Exception as e:
                    print("[曲谱] 读取失败:", path, e)
    if not songs:
        songs.append(parse_song("TITLE=内置示例\n1 1 5 5 6 6 5 -\n", "内置示例"))
    return songs


# ---------------------------------------------------------------- 按键（无钩子方案）

VK_NAMES = {
    "mouse_left": 0x01, "mouse_right": 0x02, "mouse_middle": 0x04,
    "mouse4": 0x05, "mouse5": 0x06, "xbutton1": 0x05, "xbutton2": 0x06,
    "ctrl": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B,
    "lctrl": 0xA2, "rctrl": 0xA3, "lalt": 0xA4, "ralt": 0xA5,
    "lshift": 0xA6, "rshift": 0xA7, "lwin": 0x5B, "rwin": 0x5C,
    "space": 0x20, "enter": 0x0D, "tab": 0x09, "backspace": 0x08,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "comma": 0xBC, "period": 0xBE, "slash": 0xBF, "semicolon": 0xBA,
    "minus": 0xBD, "plus": 0xBB,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}

# 单个字符按键的友好名（用于面板上的"输入检测"显示）
CHAR_NAMES = {0xBC: "，", 0xBE: "。", 0xBF: "/", 0xBA: "；", 0xBD: "-", 0xBB: "="}


def vk_of(name):
    name = str(name).strip().lower()
    if name in VK_NAMES:
        return VK_NAMES[name]
    if name == ",":
        return 0xBC
    if name == ".":
        return 0xBE
    if len(name) == 1 and name.isalnum():
        return ord(name.upper())
    return None


def vk_name(vk):
    if vk in CHAR_NAMES:
        return CHAR_NAMES[vk]
    for k, v in VK_NAMES.items():
        if v == vk and k not in ("xbutton1", "xbutton2", "period"):
            return KEY_DISPLAY.get(k, k.upper() if len(k) <= 2 else k.title())
    return "0x%02X" % vk


# ---------------------------------------------------------------- Win32

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000

user32 = ctypes.windll.user32


# ---------------------------------------------------------------- 左侧控制面板（独立小窗，可点击）

class PanelWindow(QWidget):
    def __init__(self, overlay):
        super().__init__(None,
                         Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.ov = overlay
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(float(overlay.cfg.get("opacity", 0.94)))   # 与音符层一致
        self.setMouseTracking(True)
        self.hover_action = None
        self._hit_buttons = []        # [(QRectF, action)]
        self._hit_songs = []          # [(idx, QRectF)]
        self._hit_scrollbar = None    # {"track": QRectF, "thumb": QRectF}
        self._sb_drag = None          # (按下时的光标 y, 按下时的 song_scroll)
        self._scrollbar_hot = False
        self._list_rows = 6
        self.song_scroll = 0
        self._drag = None
        self._resize_dir = None
        self._drag_origin = None

    @property
    def cfg(self):
        return self.ov.cfg

    # ---- Win32 样式：可点击 / 穿透 ----
    def apply_style(self):
        try:
            hwnd = int(self.winId())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_LAYERED | WS_EX_NOACTIVATE
            if self.cfg.get("panel_interactive", True):
                style &= ~WS_EX_TRANSPARENT
            else:
                style |= WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception as e:
            print("[panel] 设置窗口样式失败:", e)

    # ---- 曲谱列表滚动 ----
    def ensure_visible(self):
        self._compute_layout()                # 刷新可见行数（避免用到过期值）
        cap = max(1, self._list_rows)
        idx = self.ov.song_idx
        if idx < self.song_scroll:
            self.song_scroll = idx
        elif idx >= self.song_scroll + cap:
            self.song_scroll = idx - cap + 1
        self.song_scroll = max(0, min(self.song_scroll,
                                      max(0, len(self.ov.songs) - cap)))

    # ---- 布局 ----
    LIST_ROW_H = 22.0                 # 曲谱列表每行高度
    BTN_H_MAX = 25.0                  # 按钮理想高度（面板够高时用这个）
    BTN_H_MIN = 16.0                  # 面板被压扁时的硬下限（再矮会看不见字）；之前 19，但 chips 变两行后空间不够
    BTN_GAP = 3.0
    BTN_HEAD_H = 18.0
    BOTTOM_M = 10.0

    def _compute_layout(self):
        """算出各区块位置。

        关键：底部按钮区**从面板底边往上排**，列表区占中间剩下的空间。
        面板被改小的时候按钮会自动变矮（25→19px），列表最少保留 1 行，
        所以永远不会出现"按钮被挤出面板"或"列表和按钮重叠"的情况。
        """
        w, h = float(self.width()), float(self.height())
        pad = 10.0
        iw = max(40.0, w - 2 * pad)
        lay = {"pad": pad, "iw": iw, "w": w, "h": h}
        y = 12.0
        lay["title"] = QRectF(pad, y, iw, 16); y += 20
        lay["song"] = QRectF(pad, y, iw, 15); y += 17
        lay["info"] = QRectF(pad, y, iw, 13); y += 16
        lay["chips"] = QRectF(pad, y, iw, 38); y += 42      # 6 色 = 2 行 × 3（v8 升 v8.1 加 2 色）
        lay["modhint"] = QRectF(pad, y, iw, 13); y += 16
        lay["input"] = QRectF(pad, y, iw, 13); y += 17
        lay["list_header"] = QRectF(pad, y, iw, 14)
        list_top = y + 16.0

        n_btn = len(PANEL_ROWS)

        def block(bh):
            return self.BTN_HEAD_H + n_btn * (bh + self.BTN_GAP) - self.BTN_GAP

        # 空间不够就让按钮变矮，同时保证按钮块也不会撑出面板底边（chips 变两行后这点很关键）
        bh = self.BTN_H_MAX
        while bh > self.BTN_H_MIN and (
                (h - self.BOTTOM_M - block(bh)) - list_top < self.LIST_ROW_H
                or list_top + self.LIST_ROW_H + block(bh) > h - self.BOTTOM_M):
            bh -= 1.0
        bb = block(bh)
        list_h = (h - self.BOTTOM_M - bb) - list_top
        btn_head_y = max(list_top + self.LIST_ROW_H, h - self.BOTTOM_M - bb)
        # 列表区不能顶到按钮头（保留 4px 间隙，画布裁剪框再多 4px）——
        # 否则面板被压扁时 list_clip 会和按钮头只差 1px，测试断言"buttons_out=1"。
        list_h = min(list_h, btn_head_y - list_top - 4)
        rows = max(1, int(list_h // self.LIST_ROW_H))

        lay["list_top"] = list_top
        lay["list_rows"] = rows
        lay["list_h"] = list_h                                 # 真实高度（可能 < LIST_ROW_H，画布自动裁掉）
        lay["list_clip"] = QRectF(0.0, list_top - 2.0, w, list_h + 4.0)
        lay["btn_h"] = bh
        lay["btn_header"] = QRectF(pad, btn_head_y, iw, 15)
        lay["btn_top"] = btn_head_y + self.BTN_HEAD_H
        self._list_rows = rows
        return lay

    # ---- 绘制 ----
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        lay = self._compute_layout()
        self._draw(p, lay)

    def _elide(self, p, text, width):
        fm = QFontMetrics(p.font())
        return fm.elidedText(text, Qt.ElideRight, int(max(8.0, width)))

    def _button_label(self, action):
        if action == "editor":
            # 录音时按钮变成醒目状态（点它 = 打开编辑器看正在录的内容）
            return ("● 录音中" if self.ov.recording else "添加曲谱",
                    bool(self.ov.recording))
        if action == "toggle_adjust":
            return ("调整窗口", self.ov.adjust_mode)
        if action == "toggle_play":
            return ("从头重来", False)
        if action == "toggle_panel":
            # 穿透后面板本身也点不动了，必须让玩家一眼看到恢复方式：
            # 按钮文字写"已穿透"，右边照常显示热键（如 Shift+F10）
            if self.cfg.get("panel_interactive", True):
                return ("面板穿透", False)
            return ("已穿透", True)
        if action == "toggle_visible":
            return ("隐藏窗口", False)
        if action == "next_song":
            return ("下一首", False)
        if action == "toggle_mode":
            # 显示"切过去"的目标模式名，激活态 = 当前就是跟随演奏模式
            follow = (self.ov.mode == "follow")
            return ("经典模式" if follow else "跟随演奏", follow)
        if action == "quit":
            return ("退出程序", False)
        return (action, False)

    def _hotkey_hint(self, action):
        # 一律从 config 里现取 → 改了热键，面板上显示的提示自动跟着变
        return hotkey_text(self.cfg, action, "/")

    def _draw(self, p, lay):
        pad, iw = lay["pad"], lay["iw"]
        w, h = lay["w"], lay["h"]
        ov = self.ov

        # 面板底（左圆角、右边直角，与整块背景板拼成一体）
        path = QPainterPath()
        path.addRoundedRect(QRectF(1.0, 1.0, w - 1.0, h - 2.0), 11, 11)
        path.addRect(QRectF(w - 12.0, 1.0, 12.0, h - 2.0))
        p.setClipPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 62))
        p.drawRect(QRectF(0, 0, w, h))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 26), 1))
        p.drawLine(QPointF(w - 1.5, 10), QPointF(w - 1.5, h - 10))

        # 标题
        p.setPen(QColor(255, 255, 255, 245))
        p.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
        p.drawText(lay["title"], Qt.AlignLeft | Qt.AlignVCenter, "口琴曲谱")

        # 曲名 + 信息
        p.setPen(QColor(255, 255, 255, 235))
        p.setFont(QFont("Microsoft YaHei UI", 11, QFont.DemiBold))
        p.drawText(lay["song"], Qt.AlignLeft | Qt.AlignVCenter,
                   self._elide(p, "♪ " + ov.song.title, iw))
        p.setPen(QColor(255, 255, 255, 130))
        p.setFont(QFont("Microsoft YaHei UI", 9))
        info = "剩余 %d / %d 音" % (max(0, len(ov.song.notes) - ov.cursor),
                                   len(ov.song.notes))
        p.drawText(lay["info"], Qt.AlignLeft | Qt.AlignVCenter, info)

        # 六色音调指示（2 行 × 3 个：上排按方向 降/本/升，下排 半+降/半音/半+升）
        chip = lay["chips"]
        st_now = ov.current_state()
        cols = 3
        cw = (iw - (cols - 1) * 3.0) / cols
        for pos in range(6):
            st = CHIP_LAYOUT[pos]              # 这个位置上画的是哪个 state
            row, col = pos // cols, pos % cols
            r = QRectF(chip.left() + col * (cw + 3.0),
                       chip.top() + row * (chip.height() / 2 + 1.0),
                       cw, chip.height() / 2 - 1.0)
            active = (st == st_now)
            col_c = QColor(STRIP_COLORS[st])
            if not active:
                col_c.setAlpha(70)
            p.setPen(QPen(QColor(255, 255, 255, 230 if active else 40), 1))
            p.setBrush(col_c)
            p.drawRoundedRect(r, 5, 5)
            p.setPen(QColor(20, 20, 20, 230) if (active and st == 0)
                     else QColor(255, 255, 255, 235 if active else 150))
            p.setFont(QFont("Microsoft YaHei UI", 8, QFont.DemiBold))
            p.drawText(r, Qt.AlignCenter, STATE_SHORT[st])

        # 当前修饰键提示（组合音调把两个角色拼起来）
        p.setFont(QFont("Microsoft YaHei UI", 9))
        if st_now == 0:
            hint = "本音：不用按修饰键"
        else:
            parts = []
            for role in STATE_MODS[st_now]:
                mods = [KEY_DISPLAY.get(n, n)
                        for n in self.cfg["modifier_keys"].get(role, ["?"])]
                parts.append("%s+%s" % (role, "+".join(mods)))
            hint = " + ".join(parts) + "  →  %s" % STATE_NAMES[st_now]
        p.setPen(QColor(255, 255, 255, 165))
        p.drawText(lay["modhint"], Qt.AlignLeft | Qt.AlignVCenter,
                   self._elide(p, hint, iw))

        # 输入检测指示灯
        if not ov._input_ok:
            txt, col = "输入：已关闭（config）", QColor(0xE2, 0x6D, 0x6D, 200)
        elif ov._last_detect and time.monotonic() - ov._last_detect[0] < 2.5:
            txt, col = "检测到：%s" % ov._last_detect[1], QColor(0x6D, 0xE2, 0x9B, 235)
        else:
            txt, col = "输入检测：正常待命", QColor(255, 255, 255, 120)
        p.setPen(col)
        p.setFont(QFont("Microsoft YaHei UI", 9))
        p.drawText(lay["input"], Qt.AlignLeft | Qt.AlignVCenter, txt)

        # 曲谱列表
        n_songs = len(ov.songs)
        cap = lay["list_rows"]
        need_sb = n_songs > cap                       # 放不下 → 右侧出现滚动条
        sb_w = 7.0 if need_sb else 0.0
        p.setPen(QColor(255, 255, 255, 120))
        p.setFont(QFont("Microsoft YaHei UI", 9))
        p.drawText(lay["list_header"], Qt.AlignLeft | Qt.AlignVCenter,
                   "曲谱列表（%d）%s" % (n_songs, "　滚轮/拖条翻页" if need_sb else ""))
        self._hit_songs = []
        self.song_scroll = max(0, min(self.song_scroll, max(0, n_songs - cap)))

        # 列表区域裁剪：面板再矮也不会把字画到下面的按钮上
        p.save()
        p.setClipRect(lay["list_clip"])
        for k in range(cap):
            idx = self.song_scroll + k
            if idx >= n_songs:
                break
            r = QRectF(pad - 4.0, lay["list_top"] + k * self.LIST_ROW_H, iw + 8.0, 20.0)
            self._hit_songs.append((idx, r))
            cur = (idx == ov.song_idx)
            if cur:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, 34))
                p.drawRoundedRect(r, 5, 5)
                p.setBrush(QColor(STRIP_COLORS[st_now]))
                p.drawRoundedRect(QRectF(r.left() + 1.0, r.top() + 3.5,
                                         2.5, r.height() - 7.0), 1.2, 1.2)
            p.setPen(QColor(255, 255, 255, 240 if cur else 150))
            p.setFont(QFont("Microsoft YaHei UI", 9,
                            QFont.DemiBold if cur else QFont.Normal))
            tw = r.width() - 14.0 - sb_w
            p.drawText(QRectF(r.left() + 9.0, r.top(), tw, r.height()),
                       Qt.AlignLeft | Qt.AlignVCenter,
                       self._elide(p, "%d. %s" % (idx + 1, ov.songs[idx].title), tw))
        p.restore()

        # 滚动条（轨道 + 滑块）
        self._hit_scrollbar = None
        if need_sb:
            track = QRectF(w - pad - 5.0, lay["list_top"] + 1.0,
                           5.0, max(20.0, lay["list_h"] - 2.0))
            span = max(0, n_songs - cap)
            thumb_h = max(26.0, track.height() * cap / float(n_songs))
            t = (self.song_scroll / float(span)) if span else 0.0
            thumb = QRectF(track.left(), track.top() + (track.height() - thumb_h) * t,
                           track.width(), thumb_h)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 30))
            p.drawRoundedRect(track, 2.5, 2.5)
            hot = bool(self._sb_drag) or self._scrollbar_hot
            p.setBrush(QColor(255, 255, 255, 190 if hot else 120))
            p.drawRoundedRect(thumb, 2.5, 2.5)
            self._hit_scrollbar = {"track": track, "thumb": thumb}

        # 热键按钮
        p.setPen(QColor(255, 255, 255, 120))
        p.setFont(QFont("Microsoft YaHei UI", 9))
        p.drawText(lay["btn_header"], Qt.AlignLeft | Qt.AlignVCenter, "热键（都要按住 Shift）")
        self._hit_buttons = []
        y = lay["btn_top"]
        for row in PANEL_ROWS:
            n = len(row)
            gap = 4.0 if n > 1 else 0.0
            bw = (iw - gap * (n - 1)) / n
            for j, (action, _label) in enumerate(row):
                r = QRectF(pad + j * (bw + gap), y, bw, lay["btn_h"])
                label, active = self._button_label(action)
                hover = (self.hover_action == action)
                base = QColor(255, 255, 255, 26 if not active else 70)
                if hover:
                    base = QColor(255, 255, 255, 52 if not active else 96)
                p.setPen(QPen(QColor(255, 255, 255, 90 if active else 45), 1))
                p.setBrush(base)
                p.drawRoundedRect(r, 6, 6)
                p.setPen(QColor(255, 255, 255, 250 if active else 225))
                p.setFont(QFont("Microsoft YaHei UI", 9, QFont.DemiBold))
                hint = self._hotkey_hint(action)
                hint_w = 0.0
                if hint:
                    fm8 = QFontMetrics(QFont("Microsoft YaHei UI", 8))
                    hint_w = fm8.horizontalAdvance(hint) + 10.0
                    # 有多个备选键时（Shift+F6/Shift+F4 这类）先只留第一个，还是太挤就整个不显示
                    while "/" in hint and r.width() - 16.0 - hint_w < 42.0:
                        hint = hint.rsplit("/", 1)[0]
                        hint_w = fm8.horizontalAdvance(hint) + 10.0
                    if r.width() - 16.0 - hint_w < 42.0:      # 太挤就不显示键位提示
                        hint, hint_w = "", 0.0
                p.drawText(QRectF(r.left() + 8.0, r.top(),
                                  max(10.0, r.width() - 16.0 - hint_w), r.height()),
                           Qt.AlignLeft | Qt.AlignVCenter,
                           self._elide(p, label, r.width() - 16.0 - hint_w))
                if hint:
                    p.setPen(QColor(255, 255, 255, 130))
                    p.setFont(QFont("Microsoft YaHei UI", 8))
                    p.drawText(QRectF(r.left(), r.top(), r.width() - 8.0, r.height()),
                               Qt.AlignRight | Qt.AlignVCenter,
                               self._elide(p, hint, r.width() * 0.5))
                self._hit_buttons.append((r, action))
            y += lay["btn_h"] + self.BTN_GAP

    # ---- 鼠标交互 ----
    def _button_at(self, pos):
        for r, action in self._hit_buttons:
            if r.contains(pos):
                return action
        return None

    def _song_at(self, pos):
        for idx, r in self._hit_songs:
            if r.contains(pos):
                return idx
        return None

    # ---- 滚动条（曲谱太多时出现）----

    def _scroll_to(self, value):
        cap = max(1, self._list_rows)
        self.song_scroll = max(0, min(int(value),
                                      max(0, len(self.ov.songs) - cap)))
        self.update()

    def _scrollbar_press(self, pos):
        """点/拖滚动条 → 返回 True 表示事件已被滚动条吃掉"""
        sb = self._hit_scrollbar
        if not sb:
            return False
        track, thumb = sb["track"], sb["thumb"]
        grab = QRectF(track.left() - 3.0, track.top(), track.width() + 6.0,
                      track.height())              # 判定放宽一点，好点
        if not grab.contains(pos):
            return False
        cap = max(1, self._list_rows)
        span = max(0, len(self.ov.songs) - cap)
        if thumb.contains(pos):
            self._sb_drag = (pos.y(), self.song_scroll)
        else:
            # 点轨道空白 = 往上/下一页
            self._scroll_to(self.song_scroll + (-cap if pos.y() < thumb.top() else cap))
        self.update()
        return True

    def _scrollbar_drag(self, pos):
        if not self._sb_drag:
            return False
        sb = self._hit_scrollbar
        if not sb:
            return False
        track, thumb = sb["track"], sb["thumb"]
        travel = max(1.0, track.height() - thumb.height())
        cap = max(1, self._list_rows)
        span = max(0, len(self.ov.songs) - cap)
        dy = pos.y() - self._sb_drag[0]
        self._scroll_to(self._sb_drag[1] + dy * span / travel)
        return True

    def _edge_at(self, pos):
        m = 9
        w, h = self.width(), self.height()
        l, r = pos.x() <= m, pos.x() >= w - m
        t, b = pos.y() <= m, pos.y() >= h - m
        if l and t: return "lt"
        if l and b: return "lb"
        if l: return "l"
        if r and t: return "rt"
        if r and b: return "rb"
        if r: return "r"
        if t: return "t"
        if b: return "b"
        return None

    def mousePressEvent(self, e):
        pos = e.position()
        action = self._button_at(pos)
        if action:
            if action == "toggle_visible":
                # 「隐藏窗口」按钮会把自己也收起来 —— 误点一下就"找不回来"了。
                # 所以先在屏幕上停 0.8 秒、把恢复方式写进提示条，再真的收起来。
                self.ov._say("窗口已隐藏 · 按 %s 叫回来"
                             % hotkey_text(self.cfg, "toggle_visible", " 或 "))
                self.ov.update()
                QTimer.singleShot(800, self._delayed_hide)
            else:
                self.ov.do_action(action)
            return
        if not self.ov.adjust_mode:
            if self._scrollbar_press(pos):
                return
            idx = self._song_at(pos)
            if idx is not None and idx != self.ov.song_idx:
                self.ov.select_song(idx)
            return
        # 调整模式：面板空白处拖动整体移动，边缘缩放
        self._resize_dir = self._edge_at(pos)
        g = e.globalPosition().toPoint()
        self._drag = g
        if not self._resize_dir:
            self._drag_origin = self.ov.pos()

    def _delayed_hide(self):
        """配合「隐藏窗口」按钮：0.8 秒后真正收起。

        期间用户可能已经按热键收起来了 → 那就什么都别做，
        否则 do_action 是"切换"，会把窗口又反过来显示出来。
        """
        if self.ov.isVisible():
            self.ov.do_action("toggle_visible")

    def mouseMoveEvent(self, e):
        pos = e.position()
        g = e.globalPosition().toPoint()
        if self.ov.adjust_mode:
            if self._drag is None:
                edge = self._edge_at(pos)
                cursors = {"l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor,
                           "t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor,
                           "lt": Qt.SizeFDiagCursor, "rb": Qt.SizeFDiagCursor,
                           "rt": Qt.SizeBDiagCursor, "lb": Qt.SizeBDiagCursor}
                self.setCursor(cursors.get(edge, Qt.ArrowCursor))
                return
            geo = self.ov.frameGeometry()
            nx, ny, nw, nh = geo.x(), geo.y(), geo.width(), geo.height()
            if self._resize_dir:
                d = self._resize_dir
                if "l" in d:
                    dx = g.x() - self._drag.x()
                    nx, nw = geo.x() + dx, geo.width() - dx
                if "r" in d:
                    nw = geo.width() + (g.x() - self._drag.x())
                if "t" in d:
                    dy = g.y() - self._drag.y()
                    ny, nh = geo.y() + dy, geo.height() - dy
                if "b" in d:
                    nh = geo.height() + (g.y() - self._drag.y())
                if nw >= 420 and nh >= 360:
                    self.ov.setGeometry(nx, ny, nw, nh)
                    self._drag = g
            elif self._drag_origin is not None:
                delta = g - self._drag
                self.ov.move(self._drag_origin + delta)
            return
        if self._sb_drag is not None and self._scrollbar_drag(pos):
            return
        hot = bool(self._hit_scrollbar and QRectF(
            self._hit_scrollbar["track"].left() - 3.0,
            self._hit_scrollbar["track"].top(),
            self._hit_scrollbar["track"].width() + 6.0,
            self._hit_scrollbar["track"].height()).contains(pos))
        if hot != self._scrollbar_hot:
            self._scrollbar_hot = hot
            self.update()
        act = self._button_at(pos)
        if act != self.hover_action:
            self.hover_action = act
            self.setCursor(Qt.PointingHandCursor if act else Qt.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, e):
        if self.ov.adjust_mode and (self._drag is not None or self._resize_dir):
            self.ov.save_geometry()
        self._drag = None
        self._resize_dir = None
        self._drag_origin = None
        self._sb_drag = None
        self.update()

    def wheelEvent(self, e):
        self._compute_layout()
        cap = max(1, self._list_rows)
        if len(self.ov.songs) <= cap:
            return
        delta = -1 if e.angleDelta().y() > 0 else 1
        self.song_scroll = max(0, min(self.song_scroll + delta,
                                      max(0, len(self.ov.songs) - cap)))
        self.update()


# ---------------------------------------------------------------- 音符叠加层（全宽，永远鼠标穿透）

class Overlay(QWidget):
    def __init__(self, cfg, songs, panel=None):
        super().__init__(None,
                         Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.cfg = cfg
        self.songs = songs
        self.song_idx = 0
        self.panel = panel

        # 主导模式状态
        self.cursor = 0               # 下一个要弹的音符下标
        self.slide = None             # (t0, 让位距离) 消除后的缓动
        self.ghost = None             # (t0, ch, state, height) 消除时的飞散残影
        self.finished_at = None

        # 演奏模式：classic = 经典（堆叠消除）/ follow = 跟随演奏（按时值下落）
        self.mode = cfg.get("mode", "classic")
        if self.mode not in ("classic", "follow"):
            self.mode = "classic"
        # 跟随演奏模式状态机：idle(待命) → countdown(倒计时) → playing(演奏) → done(完成)
        self.follow_state = "idle"
        self.follow_t0 = None         # 演奏开始时刻（monotonic），playing 时用
        self.follow_next = 0          # 下一个待弹的音符下标
        self.follow_missed = set()    # 已经 miss 的音符下标（绘制时变暗）
        # 长音（v8.3）：按下只算"接住"，要一直按住，矩形被判定线一点点吃掉，
        # 按满整个时值才算完成；中途松手剩下的漏过。
        self.follow_hold = None       # {"idx","ch","state","start","dur","released"}；None = 没在按
        self.follow_fade = set()      # 中断 / 漏掉的长音下标（剩余部分继续变暗落走）
        self.key_down = {}            # ch -> 该通道按键当前是否按住（长音判定用）
        self.countdown_deadline = None

        self.flashes = {}             # channel -> (monotonic, state)
        self.impacts = []             # [(monotonic, ch, state, y)] 消除碰撞特效（音符×灯带的淡色光晕）
        self.wrong = {}               # channel -> monotonic
        self.held_mods = []           # 按下的修饰键（末位=最近按下，用于灯带配色）
        self.adjust_mode = False
        self._drag = None
        self._resize_dir = None
        self._toast = None            # (monotonic, 文本)

        # 曲谱编辑器 / 录音（v7）
        self.editor = None            # 由 main() 注入
        self._editor_was_visible = False   # 按"隐藏"时编辑器是不是开着（恢复时原样还回来）
        self.recording = False
        self.rec_log = []             # [(ch, state)] 最近录下的音（叠加层上显示这一串）
        self.rec_count = 0            # 本次录音总共录了几个音（撤销后会跟着减）

        # 8 个通道绑定的按键（config.note_keys，默认 z x c v b n m ,）
        self.note_vks = []
        keys = cfg.get("note_keys") or DEFAULT_NOTE_KEYS
        for i in range(8):
            name = keys[i] if i < len(keys) else DEFAULT_NOTE_KEYS[i]
            self.note_vks.append(vk_of(name) or vk_of(DEFAULT_NOTE_KEYS[i]))

        # 修饰键轮询
        self.mod_vk = {}
        for role, names in cfg["modifier_keys"].items():
            vks = [v for v in (vk_of(n) for n in names) if v]
            self.mod_vk[role] = vks or [0x11]
        self.hotkey_vks = {}
        for action, combo in cfg["hotkeys"].items():
            # 一个动作可以给多个"备选组合键"，用 | 隔开（如 "f6|f4"：F6 或 F4 都能触发）
            combos = []
            for alt in str(combo).split("|"):
                vks = tuple(v for v in (vk_of(p) for p in alt.split("+")) if v)
                if vks:
                    combos.append(vks)
            if combos:
                self.hotkey_vks[action] = combos
        self._watched = (set(self.note_vks)
                         | {v for vs in self.mod_vk.values() for v in vs}
                         | {v for combos in self.hotkey_vks.values() for c in combos for v in c})
        self._prev = {}
        self._prev_mod = {}
        self._prev_hot = {}
        self._input_ok = bool(cfg.get("keyboard_monitor", True))
        self._last_detect = None      # (monotonic, 键名)

        self.setWindowTitle("口琴可视化曲谱")
        self.setAttribute(Qt.WA_TranslucentBackground)
        scr = QApplication.primaryScreen().availableGeometry()
        geo = cfg.get("geometry")
        # 高度太小的旧几何值会让面板挤成一团 → 直接回退到默认大小
        if (isinstance(geo, (list, tuple)) and len(geo) == 4
                and 300 < geo[2] <= scr.width() and 360 <= geo[3] <= scr.height()):
            self.setGeometry(int(geo[0]), int(geo[1]), int(geo[2]), int(geo[3]))
        else:
            self.resize(760, 560)
            self.move(scr.center().x() - 380, scr.bottom() - 580)
        self.setWindowOpacity(float(cfg.get("opacity", 0.94)))

        self._last = time.monotonic()
        self._panel_next = 0.0        # 面板刷新节流
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    # ---------- 曲谱 ----------

    @property
    def song(self):
        return self.songs[self.song_idx]

    def select_song(self, idx):
        self.song_idx = max(0, min(idx, len(self.songs) - 1))
        self.reset_playback()
        self._say("曲谱：" + self.song.title)

    def reset_playback(self):
        self.cursor = 0
        self.slide = None
        self.ghost = None
        self.finished_at = None
        self.flashes.clear()
        self.impacts.clear()
        self.wrong.clear()
        # 跟随演奏模式：回到"待命"，等玩家点第一个音再开始
        self.follow_state = "idle"
        self.follow_t0 = None
        self.follow_next = 0
        self.follow_missed.clear()
        self.follow_hold = None
        self.follow_fade.clear()
        self.countdown_deadline = None
        if self.panel:
            self.panel.ensure_visible()

    def reload_songs(self, select_title=None):
        """重新扫描 songs 文件夹（保存 / 删除曲谱后调用），尽量停留在同一首"""
        songs = load_songs()
        if not songs:
            return
        want = select_title or (self.song.title if self.songs else None)
        self.songs = songs
        idx = 0
        for i, s in enumerate(songs):
            if s.title == want:
                idx = i
                break
        self.song_idx = idx
        self.reset_playback()
        if self.panel:
            self.panel.song_scroll = 0
            self.panel.ensure_visible()
            self.panel.update()
        self._say("曲谱已更新：%s（共 %d 首）" % (self.song.title, len(songs)))

    # ---------- 窗口几何 / 穿透 ----------

    def _panel_width(self):
        w = float(self.width())
        want = float(self.cfg.get("panel_width", 168))
        return max(126.0, min(want, w * 0.46))

    def sync_panel(self):
        """面板窗口始终贴在叠加层左侧，同高"""
        if not self.panel:
            return
        self.panel.setGeometry(self.x(), self.y(),
                               int(self._panel_width()), self.height())

    def moveEvent(self, e):
        self.sync_panel()
        super().moveEvent(e)

    def resizeEvent(self, e):
        self.sync_panel()
        super().resizeEvent(e)

    def _apply_clickthrough(self):
        """音符层：调整模式下可交互（拖动/缩放），其余时候整窗鼠标穿透"""
        try:
            hwnd = int(self.winId())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_LAYERED | WS_EX_NOACTIVATE
            if self.adjust_mode:
                style &= ~WS_EX_TRANSPARENT
            else:
                style |= WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception as e:
            print("[overlay] 设置窗口样式失败:", e)

    def set_adjust_mode(self, on):
        self.adjust_mode = on
        self._apply_clickthrough()
        if on:
            self.show()
            self.raise_()
        if self.panel:
            self.panel.raise_()
        self.update()

    # ---------- 输入轮询（GetAsyncKeyState，无钩子） ----------

    def _poll_input(self):
        if not self._input_ok:
            return
        st = {vk: bool(user32.GetAsyncKeyState(vk) & 0x8000) for vk in self._watched}

        for i, vk in enumerate(self.note_vks):
            down, was = st.get(vk, False), self._prev.get(vk, False)
            self.key_down[i] = down          # 长音要看"是不是还按着"，不能只看边沿
            if down and not was:
                if self.recording:
                    self._record_note(i)      # 录音时不判定游戏，只记录
                else:
                    self._on_note_press(i)

        for role, vks in self.mod_vk.items():
            any_down = any(st.get(v, False) for v in vks)
            if any_down and not self._prev_mod.get(role, False):
                if role in self.held_mods:
                    self.held_mods.remove(role)
                self.held_mods.append(role)          # 最近按下者排在末位
            elif not any_down and self._prev_mod.get(role, False):
                if role in self.held_mods:
                    self.held_mods.remove(role)
            self._prev_mod[role] = any_down

        mono = time.monotonic()
        for action, combos in self.hotkey_vks.items():
            # 多个备选键里任意一组按下都算（如 F6 或 F4）
            all_down = any(all(st.get(v, False) for v in c) for c in combos)
            if all_down and not self._prev_hot.get(action, False):
                self.do_action(action)
            self._prev_hot[action] = all_down

        # 记录最近检测到的输入（面板上的"输入检测"指示灯）
        for vk, down in st.items():
            if down and not self._prev.get(vk, False):
                self._last_detect = (mono, vk_name(vk))
                break

        self._prev = st

    def _mod_ok(self, state):
        """该状态要求的修饰键是否都按住了（只有 leader_strict_modifier 打开时才强制）"""
        need = STATE_MODS[state] if 0 <= state < len(STATE_MODS) else []
        return all(role in self.held_mods for role in need)

    def current_state(self):
        """当前实际音调状态：0 本音 / 1 降调 / 2 半音 / 3 升调 / 4 半音+降调 / 5 半音+升调

        半音可以和其他修饰键一起按（中键+左键=黄、中键+右键=红）——
        组合优先于单键；三个都按住时按"最近按下的那个方向键"算。
        """
        held = [r for r in self.held_mods if r in MOD_ROLES]
        if not held:
            return 0
        hset = set(held)
        if "半音" in hset:
            dirs = [r for r in reversed(held) if r in ("降调", "升调")]
            if "降调" in hset and "升调" in hset:
                return 4 if (dirs and dirs[0] == "降调") else 5
            if "降调" in hset:
                return 4
            if "升调" in hset:
                return 5
            return 2
        return MOD_ROLES.index(held[-1]) + 1        # 只有方向键 → 1 降调 / 3 升调

    def _on_note_press(self, ch):
        """按键判定入口：跟随演奏模式走时间轴判定，经典模式走堆叠消除"""
        if not 0 <= ch <= 7:
            return
        now = time.monotonic()
        if self.mode == "follow":
            self._follow_press(ch, now)
            return
        """只有"最靠近底部的那一个"块能被消除；按错键则该通道红闪"""
        if self.finished_at is not None or self.cursor >= len(self.song.notes):
            return
        note = self.song.notes[self.cursor]
        if note[2] != ch:
            self.wrong[ch] = now
            return
        if self.cfg.get("leader_strict_modifier", False) and not self._mod_ok(note[3]):
            self.wrong[ch] = now
            return
        h = self._leader_unit() * note[1]
        self.ghost = (now, ch, note[3], h)
        self.slide = (now, h + 6.0)
        self.flashes[ch] = (now, note[3])
        self.impacts.append((now, ch, note[3]))      # 消除碰撞特效
        self.cursor += 1
        if self.cursor >= len(self.song.notes):
            self.finished_at = now

    # ---------- 跟随演奏模式 ----------

    def _follow_spb(self):
        """每秒多少拍 → 反过来：每拍多少秒"""
        return 60.0 / max(1.0, self.song.bpm)

    def _follow_lead(self):
        return float(self.cfg.get("follow_lead", 2.0))

    def _follow_window(self):
        return float(self.cfg.get("follow_window", 0.20))

    def _follow_play_time(self, now):
        """当前"播放时间"（秒，相对曲首）。idle/countdown 时固定把第一个音对齐到
        判定线上方 lead 秒处，让玩家能看清待弹的第一个音。"""
        if self.follow_state == "playing" and self.follow_t0 is not None:
            return (now - self.follow_t0) - self._follow_lead()
        if self.song and self.song.notes:
            return self.song.notes[0][0] * self._follow_spb() - self._follow_lead()
        return -self._follow_lead()

    def _follow_press(self, ch, now):
        notes = self.song.notes
        # 待命：点击第一个音 = "准备开始"，这次点击不消除任何矩形
        if self.follow_state == "idle":
            if not notes:
                return
            n = notes[0]
            if n[2] != ch:
                self.wrong[ch] = now
                return
            secs = int(self.cfg.get("countdown_seconds", 3))
            self.follow_state = "countdown"
            self.countdown_deadline = now + secs
            self._say("准备就绪，%d 秒后开始…" % secs)
            self.update()
            return
        if self.follow_state == "countdown":
            return                       # 倒计时期间按键不判定
        if self.follow_state != "playing":
            return
        if self.follow_next >= len(notes):
            return
        n = notes[self.follow_next]
        if n[2] != ch:
            self.wrong[ch] = now
            return
        hit = n[0] * self._follow_spb()
        play = self._follow_play_time(now)
        if abs(play - hit) > self._follow_window():
            self.wrong[ch] = now          # 时机不对（太早/太晚）
            return
        # 命中
        self.flashes[ch] = (now, n[3])
        self.impacts.append((now, ch, n[3]))          # 消除碰撞特效
        if float(n[1]) >= self._hold_min_beats():
            # 长音：这次按下只算"接住"，矩形不消失 —— 要一直按住，
            # 它会被判定线一点点吃掉；按满整个时值才算完成，中途松手剩下的漏过。
            self.follow_hold = {"idx": self.follow_next, "ch": ch, "state": n[3],
                                "start": play, "dur": float(n[1]), "released": None}
            self.update()
            return
        self.follow_next += 1
        self._follow_check_done(now)
        self.update()

    # ---------- 长音（按住不放才算完成） ----------

    def _hold_min_beats(self):
        """多长的音算"长音"：默认 1.5 拍。调大了就退回"按一下即消"。"""
        try:
            return float(self.cfg.get("hold_min_beats", 1.5))
        except Exception:
            return 1.5

    def _follow_check_done(self, now):
        if self.follow_next >= len(self.song.notes):
            self.follow_state = "done"
            self.finished_at = now

    def _follow_hold_progress(self, now):
        """正在按住的长音：已经按住的比例 0~1（绘制"被吃掉"用）"""
        h = self.follow_hold
        if not h:
            return 0.0
        total = max(0.05, h["dur"] * self._follow_spb())
        return max(0.0, min(1.0, (self._follow_play_time(now) - h["start"]) / total))

    def _follow_hold_tick(self, now):
        """长音：按住期间矩形被判定线一点点吃掉；按满 → 完成；松手太久 → 漏过。

        返回 True 表示这一帧有变化（调用方需要重绘）。
        """
        h = self.follow_hold
        if not h:
            return False
        total = max(0.05, h["dur"] * self._follow_spb())
        play = self._follow_play_time(now)
        # 关掉输入读取时无法判断松手 → 一律当作按住，免得长音永远完不成
        held = self.key_down.get(h["ch"], False) or not self._input_ok

        if held:
            h["released"] = None                      # 按着 → 清掉松手计时
        elif h["released"] is None:
            h["released"] = now                       # 刚松手，先进宽限期
        elif now - h["released"] > float(self.cfg.get("hold_grace", 0.20)):
            # 松手太久 → 长音没按满，剩下的漏过（变暗落走）
            self.follow_fade.add(h["idx"])
            self.follow_next = h["idx"] + 1
            self.follow_hold = None
            self.wrong[h["ch"]] = now                 # 红闪一下：这里断了
            self._say("长音没按住，漏过")
            self._follow_check_done(now)
            return True

        if play - h["start"] >= total:
            # 按满了 → 真正消除
            self.flashes[h["ch"]] = (now, h["state"])
            self.impacts.append((now, h["ch"], h["state"]))
            self.follow_next = h["idx"] + 1
            self.follow_hold = None
            self._say("长音完成")
            self._follow_check_done(now)
            return True
        return False

    def _follow_advance_missed(self, now):
        """把已经错过判定窗口的音符标记为 miss 并跳过"""
        spb = self._follow_spb()
        play = self._follow_play_time(now)
        win = self._follow_window()
        changed = False
        while self.follow_next < len(self.song.notes):
            if self.follow_hold is not None and self.follow_hold["idx"] == self.follow_next:
                break                       # 正被按住的长音不判 miss
            n = self.song.notes[self.follow_next]
            if n[0] * spb + win < play:
                self.follow_missed.add(self.follow_next)
                self.follow_fade.add(self.follow_next)   # 让它继续变暗落走，不凭空消失
                self.follow_next += 1
                changed = True
                if self.follow_next >= len(self.song.notes):
                    self.follow_state = "done"
                    self.finished_at = now
            else:
                break
        return changed

    # ---------- 录音（添加曲谱） ----------

    def set_recording(self, on):
        """开始 / 结束录音。录音中按键只记录，不做游戏判定"""
        on = bool(on)
        if on and not self._input_ok:
            self._say("输入读取已在 config.json 里关闭，无法录音")
            return
        if on == self.recording:
            return
        self.recording = on
        if on:
            self.rec_log = []
            self.rec_count = 0
            self._say("● 录音中：按顺序弹一遍（z x c v b n m ,），%s 结束" % self.hk("toggle_record"))
        else:
            n = len(self.editor.recorded_tokens()) if self.editor else 0
            self._say("录音结束：共 %d 个音 ｜ 按 %s 直接保存，或 %s 打开编辑器"
                      % (n, self.hk("save_song"), self.hk("editor")))
        if self.editor:
            self.editor.set_recording_ui(on)
        if self.panel:
            self.panel.update()
        self.update()

    def _record_note(self, ch):
        st = self.current_state()
        self.flashes[ch] = (time.monotonic(), st)
        self.rec_log.append((ch, st))
        self.rec_count += 1
        if len(self.rec_log) > REC_KEEP:
            del self.rec_log[:-REC_KEEP_WANT]
        if self.editor:
            self.editor.rec_append(note_token(ch, st))

    def truncate_rec(self, n):
        """编辑器里"撤销一个音 / 清空"之后，把录音记录裁到 n 个音。

        这样叠加层上那一串音符块（红圈里那几个）才会跟着一起消失 ——
        以前只改了右边文本框，主窗口还留着已经撤销的音。
        """
        if not self.recording:
            return
        n = max(0, int(n))
        drop = self.rec_count - n
        if drop > 0 and self.rec_log:
            cut = max(0, len(self.rec_log) - drop)
            for ch, _st in self.rec_log[cut:]:
                self.flashes.pop(ch, None)      # 顺带清掉那几个通道的闪烁
            del self.rec_log[cut:]
        self.rec_count = n
        self.update()
        if self.panel:
            self.panel.update()

    def toggle_editor(self):
        if not self.editor:
            return
        if self.editor.isVisible():
            self.editor.hide()
        else:
            self.editor.show_editor()

    # ---------- 动作 ----------

    def do_action(self, action):
        """action 是 config.hotkeys 里的"动作名"（如 toggle_adjust），与按键值无关"""
        if action == "toggle_adjust":
            self.set_adjust_mode(not self.adjust_mode)
            self._say("调整模式：拖动 / 缩放对齐，再按一次锁定" if self.adjust_mode
                      else "已锁定窗口")
        elif action == "toggle_visible":
            # 一键隐藏 / 恢复「所有窗口」（游戏中临时让开视野用）
            if self.isVisible():
                # 编辑器也要一起藏起来，否则开着编辑器按这个键，编辑器还挡在游戏画面上
                ev = bool(self.editor and self.editor.isVisible())
                self._editor_was_visible = ev
                if ev:
                    self.editor.hide()
                self.hide()
                if self.panel:
                    self.panel.hide()
            else:
                self.show()
                self.raise_()
                if self.panel:
                    self.panel.show()
                    self.panel.raise_()
                if self._editor_was_visible and self.editor:
                    # 用 show() 不用 show_editor()：后者会抢焦点，从游戏里切出来会打断游戏
                    self.editor.show()
                    self.editor.raise_()
                self._editor_was_visible = False
        elif action == "toggle_play":
            self.reset_playback()
            self._say("从头重来")
        elif action == "toggle_mode":
            self.mode = "classic" if self.mode == "follow" else "follow"
            self.reset_playback()
            self._save_config({"mode": self.mode})
            if self.mode == "follow":
                self._say("已切到【跟随演奏】：弹对第一个音开始，之后音符按时值下落")
            else:
                self._say("已切到【经典模式】：音符堆叠，按顺序逐个消除")
        elif action == "next_song":
            self.select_song((self.song_idx + 1) % len(self.songs))
        elif action == "prev_song":
            self.select_song((self.song_idx - 1) % len(self.songs))
        elif action == "toggle_panel":
            on = not self.cfg.get("panel_interactive", True)
            self.cfg["panel_interactive"] = on
            if self.panel:
                self.panel.apply_style()
            self._save_config({"panel_interactive": on})
            self._say("面板可点击" if on else "面板已穿透（按 %s 恢复）" % self.hk("toggle_panel"))
        elif action == "editor":
            self.toggle_editor()
        elif action == "toggle_record":
            self.set_recording(not self.recording)
        elif action == "save_song":
            # 走全局轮询热键（不依赖窗口焦点）：游戏在前台时按 F3 也能把刚录的曲谱存下来
            if self.editor:
                self.editor.save_quick()
        elif action == "quit":
            self.save_geometry()
            QApplication.quit()
        if self.panel:
            self.panel.update()
        self.update()

    def _say(self, text):
        self._toast = (time.monotonic(), text)

    def hk(self, action, joiner="/"):
        """取某个动作当前绑定的热键文字。

        屏幕提示一律走这里 → 以后改 config.json 里的热键，提示会自动跟着变，
        不会留下"提示还写着 F12、其实要按 Shift+F12"的死文字。
        """
        return hotkey_text(self.cfg, action, joiner)

    # ---------- 主循环 ----------

    def _tick(self):
        mono = time.monotonic()
        self._last = mono
        self._poll_input()

        # 跟随演奏模式：倒计时推进 + miss 检查
        if self.mode == "follow":
            if self.follow_state == "countdown" and self.countdown_deadline is not None:
                if mono >= self.countdown_deadline:
                    # 倒计时结束：进入演奏。follow_t0 这样设，能让第一个音
                    # 从判定线上方 lead 秒处开始下落（与 idle 时的静止位置平滑衔接）
                    first = (self.song.notes[0][0] * self._follow_spb()
                             if self.song.notes else 0.0)
                    self.follow_t0 = mono - first
                    self.follow_state = "playing"
                    self._say("开始！")
            elif self.follow_state == "playing":
                self._follow_hold_tick(mono)      # 长音：按住 → 被吃掉 → 按满才消
                self._follow_advance_missed(mono)

        if self.finished_at and self.cfg.get("loop", True) and mono - self.finished_at > 1.2:
            self.reset_playback()

        self.update()
        # 面板上的音调指示 / 检测提示 / 剩余音数也要跟着刷新（约 12fps 足够）
        if self.panel and self.panel.isVisible() and mono >= self._panel_next:
            self._panel_next = mono + 0.08
            self.panel.update()

    # ---------- 绘制 ----------

    def _note_geometry(self):
        """音符下落区（面板右侧）的起点与通道宽度"""
        w = float(self.width())
        pad = 8.0
        x0 = self._panel_width() + pad
        ch_w = max(12.0, (w - x0 - pad) / 8.0)
        return x0, ch_w, pad

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = float(self.width()), float(self.height())
        x0, ch_w, pad = self._note_geometry()
        hit_y = h - float(self.cfg.get("hit_line_offset", 10))

        p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.setBrush(QColor(24, 22, 19, int(self.cfg.get("bg_alpha", 150))))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 12, 12)

        # 通道分隔线
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        for i in range(1, 8):
            x = x0 + i * ch_w
            p.drawLine(QPointF(x, 8), QPointF(x, hit_y))

        # 音符区
        p.save()
        p.setClipRect(QRectF(x0 - 3, 0, w - x0 + 3, hit_y))
        if self.recording:
            self._draw_recording(p, x0, ch_w, hit_y)
        elif self.mode == "follow":
            self._draw_follow(p, x0, ch_w, hit_y)
        else:
            self._draw_leader(p, x0, ch_w, hit_y)
        p.restore()

        self._draw_strip(p, x0, w, hit_y)
        self._draw_wrong(p, x0, ch_w, hit_y)
        self._draw_toast(p, x0, w)
        self._draw_adjust_hint(p, x0, w, h, hit_y)

    def _draw_wrong(self, p, x0, ch_w, hit_y):
        """按错键：该通道灯带上方闪一道红，300ms 淡出"""
        now = time.monotonic()
        for ch, t0 in list(self.wrong.items()):
            age = now - t0
            if age > 0.3:
                self.wrong.pop(ch, None)
                continue
            c = QColor(0xE2, 0x3B, 0x3B)
            c.setAlpha(int(190 * (1 - age / 0.3)))
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x0 + ch * ch_w + 3, hit_y - 9, ch_w - 6, 14), 4, 4)

    # ---- 音符块（圆角药丸 + 按键字母） ----

    def _draw_block(self, p, rect, state, ch, highlight=False):
        style = STATE_STYLE[state]
        r = min(12.0, rect.height() / 2.0, rect.width() / 2.0)
        p.setPen(Qt.NoPen)
        p.setBrush(style["fill"])
        p.drawRoundedRect(rect, r, r)
        # 顶部一道高光，显得有厚度
        if rect.height() > 10.0:
            p.setPen(QPen(QColor(255, 255, 255, 70), 1))
            p.drawLine(QPointF(rect.left() + r, rect.top() + 1.0),
                       QPointF(rect.right() - r, rect.top() + 1.0))
        if highlight:
            p.setPen(QPen(QColor(255, 255, 255, 235), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), r + 2, r + 2)
            p.setPen(Qt.NoPen)

        # 只画按键字母（z x c v b n m ,）
        fsize = int(max(10.0, min(rect.width() * 0.62, rect.height() * 0.5, 30.0)))
        p.setPen(style["text"])
        p.setFont(QFont("Consolas", fsize, QFont.Bold))
        p.drawText(rect, Qt.AlignCenter, KEY_LABELS[ch])

    def _leader_unit(self):
        return max(22.0, min(36.0, self.height() * 0.06))

    def _draw_leader(self, p, x0, ch_w, hit_y):
        unit = self._leader_unit()
        gap = 6.0
        shift = 0.0
        if self.slide:
            t0, dist = self.slide
            prog = min(1.0, (time.monotonic() - t0) / 0.16)
            ease = 1 - (1 - prog) ** 3
            shift = -dist * (1 - ease)
            if prog >= 1.0:
                self.slide = None

        y = hit_y - 4.0 + shift
        for idx, (start, dur, ch, st) in enumerate(self.song.notes[self.cursor:]):
            bh = unit * dur
            rect = QRectF(x0 + ch * ch_w + ch_w * 0.22, y - bh, ch_w * 0.56, bh)
            if rect.bottom() < 0:
                break
            self._draw_block(p, rect, st, ch, highlight=(idx == 0))
            y -= bh + gap

        if self.ghost:
            t0, ch, st, gh = self.ghost
            age = time.monotonic() - t0
            if age > 0.24:
                self.ghost = None
            else:
                k = age / 0.24
                fill = QColor(STATE_STYLE[st]["fill"])
                fill.setAlpha(int(180 * (1 - k)))
                p.setPen(Qt.NoPen)
                p.setBrush(fill)
                bw = ch_w * 0.56
                bx = x0 + ch * ch_w + ch_w * 0.22
                p.drawRoundedRect(QRectF(bx, hit_y - 4 - gh * (1 - k), bw, gh * (1 - k)),
                                  min(12.0, gh / 2), min(12.0, gh / 2))

        now = time.monotonic()
        for ch, (t0, st) in list(self.flashes.items()):
            age = now - t0
            if age > 0.35:
                self.flashes.pop(ch, None)
                continue
            c = QColor(STATE_STYLE[st]["fill"])
            c.setAlpha(int(150 * (1 - age / 0.35)))
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x0 + ch * ch_w + 2, hit_y - 5, ch_w - 4, 10), 4, 4)

        self._draw_impacts(p, x0, ch_w, hit_y)

        if self.finished_at is not None:
            p.setPen(QColor(255, 255, 255, 220))
            p.setFont(QFont("Microsoft YaHei UI", 14, QFont.DemiBold))
            p.drawText(QRectF(x0, hit_y * 0.42, self.width() - x0, 30),
                       Qt.AlignCenter, "演奏完成")

    def _draw_recording(self, p, x0, ch_w, hit_y):
        """录音视图：提示 + 最近弹的一串音（左→右），当前按下的通道闪一下"""
        w = float(self.width())
        now = time.monotonic()

        # 指示：闪烁的红点 + 文案
        pulse = 0.55 + 0.45 * abs(((now * 1.6) % 2.0) - 1.0)
        p.setPen(Qt.NoPen)
        top = 14.0
        p.setBrush(QColor(255, 255, 255, 26))
        p.drawRoundedRect(QRectF(x0, top, w - x0 - 8.0, 62.0), 10, 10)
        p.setBrush(QColor(0xE2, 0x4B, 0x4B, int(60 + 195 * pulse)))
        p.drawEllipse(QPointF(x0 + 22.0, top + 21.0), 6.0, 6.0)
        p.setPen(QColor(255, 255, 255, 240))
        p.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
        p.drawText(QRectF(x0 + 36.0, top + 8.0, w - x0 - 50.0, 26.0),
                   Qt.AlignLeft | Qt.AlignVCenter, "录音中")
        p.setPen(QColor(255, 255, 255, 175))
        p.setFont(QFont("Microsoft YaHei UI", 9))
        p.drawText(QRectF(x0 + 12.0, top + 34.0, w - x0 - 24.0, 22.0),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   "按顺序弹一遍按键（z x c v b n m ,）· 鼠标左=绿 中=紫 右=蓝 中+左=黄 中+右=红 · "
                   "已录 %d 个音 · %s 结束" % (self.rec_count, self.hk("toggle_record")))

        # 最近弹的音：从右往左排（最新的在最右）
        unit = 30.0
        gap = 4.0
        avail = max(60.0, w - x0 - 16.0)
        cap = max(1, int((avail + gap) // (unit + gap)))
        tail = self.rec_log[-cap:] if self.rec_log else []
        ty = hit_y - 46.0
        bx = w - 8.0 - len(tail) * (unit + gap) + gap
        for i, (ch, st) in enumerate(tail):
            r = QRectF(bx + i * (unit + gap), ty, unit, unit)
            style = STATE_STYLE[st]
            p.setPen(QPen(QColor(255, 255, 255, 90), 1))
            p.setBrush(QColor(style["fill"]))
            p.drawRoundedRect(r, 8, 8)
            p.setPen(QColor(style["text"]))
            p.setFont(QFont("Microsoft YaHei UI", 10, QFont.DemiBold))
            p.drawText(r, Qt.AlignCenter, KEY_LABELS[ch])

        # 当前按下的通道：在该通道位置闪一道色
        for ch, (t0, st) in list(self.flashes.items()):
            age = now - t0
            if age > 0.35:
                self.flashes.pop(ch, None)
                continue
            c = QColor(STATE_STYLE[st]["fill"])
            c.setAlpha(int(170 * (1 - age / 0.35)))
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x0 + ch * ch_w + 2, hit_y - 5, ch_w - 4, 10), 4, 4)

        if not self.rec_count:
            p.setPen(QColor(255, 255, 255, 120))
            p.setFont(QFont("Microsoft YaHei UI", 10))
            p.drawText(QRectF(x0, ty - 40.0, avail, 24.0), Qt.AlignCenter,
                       "还没有录到音… 直接按 z x c v b n m , 试试")

    def _draw_follow(self, p, x0, ch_w, hit_y):
        """跟随演奏模式：音符按时值从上方下落，到达底部判定线（灯带）时按键。

        状态机：idle 待命（点第一个音）→ countdown 倒计时 → playing 下落判定 → done。
        """
        now = time.monotonic()
        song = self.song
        spb = self._follow_spb()
        speed = max(40.0, float(self.cfg.get("follow_speed", 200)))
        play = self._follow_play_time(now)
        w = float(self.width())

        # 判定线：一道高亮线，让玩家知道该在哪按键
        p.setPen(QPen(QColor(255, 255, 255, 110), 1))
        p.drawLine(QPointF(x0, hit_y), QPointF(w - 8.0, hit_y))

        # 下落中的音符（从 follow_next 起，还没被消除的；fade 的音继续画到落走为止）
        draw_from = self.follow_next
        if self.follow_fade:
            draw_from = min(draw_from, min(self.follow_fade))
        for i in range(draw_from, len(song.notes)):
            start, dur, ch, st = song.notes[i]
            hit = start * spb
            y_end = hit_y - (hit - play) * speed
            bh = max(6.0, dur * spb * speed)
            y_start = y_end - bh
            if y_end < -4.0:
                continue                     # 还在屏幕上方很远，先不画
            if y_start > hit_y + 6.0:
                self.follow_fade.discard(i)  # 已经整个穿过判定线（落走），不用再留
                continue
            rect = QRectF(x0 + ch * ch_w + ch_w * 0.22, y_start, ch_w * 0.56, bh)
            holding = bool(self.follow_hold and self.follow_hold["idx"] == i)
            self._draw_block(p, rect, st, ch,
                             highlight=(i == self.follow_next and not holding))
            if holding:
                # 长音正被按住：亮描边 + 判定线上一条随进度收缩的同色光带，
                # 让"这块正在被判定线一点点吃掉"看得见
                prog = self._follow_hold_progress(now)
                p.setPen(QPen(QColor(255, 255, 255, int(210 - 110 * prog)), 2))
                p.setBrush(Qt.NoBrush)
                rad = min(12.0, max(3.0, rect.width() / 2.0))
                p.drawRoundedRect(rect.adjusted(-2.0, -2.0, 2.0, 2.0), rad, rad)
                bw = max(4.0, ch_w * 0.56 * (1.0 - prog))
                c = QColor(STATE_STYLE[st]["fill"])
                c.setAlpha(180)
                p.setPen(Qt.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(QRectF(x0 + ch * ch_w + (ch_w - bw) / 2.0,
                                         hit_y - 9.0, bw, 9.0), 4, 4)
            if i in self.follow_fade or i in self.follow_missed:
                # miss / 长音断掉：盖一层半透明黑，让玩家知道这部分漏了
                r = min(12.0, rect.height() / 2.0, rect.width() / 2.0)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, 150))
                p.drawRoundedRect(rect, r, r)

        # 消除碰撞特效（命中音符在判定线上泛起的光晕）
        self._draw_impacts(p, x0, ch_w, hit_y)

        # 待命提示
        if self.follow_state == "idle":
            first = song.notes[0] if song.notes else None
            p.setPen(QColor(255, 255, 255, 240))
            p.setFont(QFont("Microsoft YaHei UI", 13, QFont.DemiBold))
            p.drawText(QRectF(x0, hit_y * 0.30, w - x0, 30), Qt.AlignCenter,
                       "跟随演奏模式")
            p.setPen(QColor(255, 255, 255, 175))
            p.setFont(QFont("Microsoft YaHei UI", 10))
            if first is not None:
                p.drawText(QRectF(x0, hit_y * 0.30 + 30, w - x0, 24), Qt.AlignCenter,
                           "弹对第一个音「%s」开始" % KEY_LABELS[first[2]])
            p.drawText(QRectF(x0, hit_y * 0.30 + 54, w - x0, 24), Qt.AlignCenter,
                       "开始前倒计时 %d 秒 · 长条要按住不放"
                       % int(self.cfg.get("countdown_seconds", 3)))

        # 倒计时大数字
        if self.follow_state == "countdown" and self.countdown_deadline is not None:
            remain = self.countdown_deadline - now
            n = max(1, int(math.ceil(remain)))
            p.setPen(QColor(255, 255, 255, 235))
            p.setFont(QFont("Microsoft YaHei UI", 54, QFont.Bold))
            p.drawText(QRectF(x0, hit_y * 0.30, w - x0, 64), Qt.AlignCenter, str(n))
            p.setPen(QColor(255, 255, 255, 160))
            p.setFont(QFont("Microsoft YaHei UI", 11))
            p.drawText(QRectF(x0, hit_y * 0.30 + 66, w - x0, 24), Qt.AlignCenter,
                       "准备…")

        # 完成
        if self.follow_state == "done":
            p.setPen(QColor(255, 255, 255, 220))
            p.setFont(QFont("Microsoft YaHei UI", 14, QFont.DemiBold))
            p.drawText(QRectF(x0, hit_y * 0.42, w - x0, 30), Qt.AlignCenter,
                       "演奏完成")

    def _draw_impacts(self, p, x0, ch_w, hit_y):
        """消除碰撞特效：命中音符时，在灯带/判定线上泛起一圈淡色光晕并扩散淡出，
        让玩家明确看到「这块矩形被消掉了」，而不是瞬间凭空消失。"""
        now = time.monotonic()
        for it in list(self.impacts):
            t0, ch, st = it
            age = now - t0
            if age > 0.32:
                self.impacts.remove(it)
                continue
            k = age / 0.32
            base = QColor(STATE_STYLE[st]["fill"])
            cx = x0 + ch * ch_w + ch_w * 0.5
            cy = hit_y - 2.0
            max_r = ch_w * 0.62
            r = max_r * (0.35 + 0.65 * k)
            # 中心亮、向外淡出的软光晕
            grad = QRadialGradient(cx, cy, max(1.0, r))
            inner = QColor(base); inner.setAlpha(int(150 * (1 - k)))
            outer = QColor(base); outer.setAlpha(0)
            grad.setColorAt(0.0, inner)
            grad.setColorAt(1.0, outer)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(QPointF(cx, cy), r, r)
            # 一圈扩散的细环（"碰撞涟漪"）
            ring = QColor(base); ring.setAlpha(int(110 * (1 - k)))
            p.setPen(QPen(ring, 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_strip(self, p, x0, w, hit_y):
        """底部灯带：对齐游戏口琴按键上沿；颜色随当前按住的修饰键变化
        白=本音、绿=降调(鼠标左键)、紫=半音(鼠标中键)、蓝=升调(鼠标右键)"""
        st = self.current_state()
        color = QColor(STRIP_COLORS[st])
        left, width = x0, w - x0 - 8.0
        p.setPen(Qt.NoPen)
        glow = QColor(color)
        glow.setAlpha(70)
        p.setBrush(glow)
        p.drawRoundedRect(QRectF(left, hit_y - 5.0, width, 12.0), 6, 6)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(left, hit_y - 2.0, width, 4.0), 2, 2)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(QRectF(left, hit_y + 3.0, width, 3.0), 1.5, 1.5)

    def _draw_toast(self, p, x0, w):
        """点击按钮 / 按热键后的短提示（音符区右上角的小气泡）"""
        if not self._toast:
            return
        age = time.monotonic() - self._toast[0]
        if age >= 2.2:
            self._toast = None
            return
        alpha = max(0, min(255, int(255 * (1.0 if age < 1.6 else (2.2 - age) / 0.6))))
        text = self._toast[1]
        fm = QFontMetrics(QFont("Microsoft YaHei UI", 9))
        tw = min(float(fm.horizontalAdvance(text) + 24), max(80.0, w - x0 - 20.0))
        rect = QRectF(w - 10.0 - tw, 10.0, tw, 24.0)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(18, 16, 14, min(205, alpha)))
        p.drawRoundedRect(rect, 12, 12)
        p.setPen(QColor(0xFF, 0xE0, 0x9A, alpha))
        p.setFont(QFont("Microsoft YaHei UI", 9))
        p.drawText(rect, Qt.AlignCenter, fm.elidedText(text, Qt.ElideRight,
                                                       int(max(10.0, tw - 18.0))))

    def _draw_adjust_hint(self, p, x0, w, h, hit_y):
        if not self.adjust_mode:
            return
        p.setPen(QPen(QColor(0xF0, 0xA3, 0x3C, 200), 2, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 12, 12)
        p.setPen(QColor(0xF0, 0xA3, 0x3C, 235))
        p.setFont(QFont("Microsoft YaHei UI", 11))
        p.drawText(QRectF(x0, hit_y * 0.38, max(80.0, w - x0 - 8), 24), Qt.AlignHCenter,
                   "调整模式：拖动移动 · 拖边缘缩放 · 让 8 条竖线对准琴键、灯带贴住琴键上沿 · %s 锁定"
                   % self.hk("toggle_adjust"))

    # ---------- 交互（仅调整模式下窗口可交互） ----------

    def save_geometry(self):
        self._save_config({"geometry": [self.x(), self.y(), self.width(), self.height()]})

    def _save_config(self, updates):
        try:
            data = {}
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data.update(updates)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[config] 保存失败:", e)

    def _edge_at(self, pos):
        m = 10
        w, h = self.width(), self.height()
        l, r = pos.x() <= m, pos.x() >= w - m
        t, b = pos.y() <= m, pos.y() >= h - m
        if l and t: return "lt"
        if r and t: return "rt"
        if l and b: return "lb"
        if r and b: return "rb"
        if l: return "l"
        if r: return "r"
        if t: return "t"
        if b: return "b"
        return None

    def mousePressEvent(self, e):
        if not self.adjust_mode:
            return
        pos = e.position()
        self._resize_dir = self._edge_at(pos)
        g = e.globalPosition().toPoint()
        self._drag = g if self._resize_dir else g - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if not self.adjust_mode:
            return
        g = e.globalPosition().toPoint()
        if self._drag is None:
            edge = self._edge_at(e.position())
            cursors = {"l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor,
                       "t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor,
                       "lt": Qt.SizeFDiagCursor, "rb": Qt.SizeFDiagCursor,
                       "rt": Qt.SizeBDiagCursor, "lb": Qt.SizeBDiagCursor}
            self.setCursor(cursors.get(edge, Qt.ArrowCursor))
            return
        if self._resize_dir:
            geo = self.frameGeometry()
            nx, ny, nw, nh = geo.x(), geo.y(), geo.width(), geo.height()
            d = self._resize_dir
            if "l" in d:
                dx = g.x() - self._drag.x()
                nx, nw = geo.x() + dx, geo.width() - dx
            if "r" in d:
                nw = geo.width() + (g.x() - self._drag.x())
            if "t" in d:
                dy = g.y() - self._drag.y()
                ny, nh = geo.y() + dy, geo.height() - dy
            if "b" in d:
                nh = geo.height() + (g.y() - self._drag.y())
            if nw >= 420 and nh >= 360:
                self.setGeometry(nx, ny, nw, nh)
            self._drag = g
        else:
            self.move(g - self._drag)

    def mouseReleaseEvent(self, e):
        if self.adjust_mode and (self._drag is not None or self._resize_dir):
            self.save_geometry()
        self._drag = None
        self._resize_dir = None


# ---------------------------------------------------------------- 曲谱编辑器（添加 / 录制 / 编辑）

NOTE_RE = re.compile(r"^[b#^]{0,2}(?:[1-8]|[iI])-*$")


class SongTextEdit(QPlainTextEdit):
    """Ctrl+Z 交给编辑器自己的"撤销一个音"（QPlainTextEdit 自带撤销会抢走这个键）"""

    def __init__(self, editor):
        super().__init__()
        self.editor = editor

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Z and (e.modifiers() & Qt.ControlModifier):
            self.editor.undo_one()
            return
        super().keyPressEvent(e)


class SongEditor(QWidget):
    """添加 / 编辑曲谱：录音、撤销、保存到曲谱库、导入导出、直接改文本"""

    def __init__(self, overlay):
        super().__init__(None, Qt.Window | Qt.WindowStaysOnTopHint)
        self.ov = overlay
        self.recording = False
        self.setWindowTitle("添加 / 编辑曲谱 — 口琴曲谱")
        self.resize(600, 620)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("给这首曲谱起个名字（例如：小星星）")
        self.name_edit.setMaxLength(40)
        lay.addWidget(self.name_edit)

        self.focus_hint = QLabel("提示：窗口没拿到焦点时打不了字 —— 先点一下这个窗口（标题栏或输入框）再输入。")
        self.focus_hint.setWordWrap(True)
        self.focus_hint.setStyleSheet("color:#c60; font-weight:600;")
        self.focus_hint.hide()
        lay.addWidget(self.focus_hint)

        tip = QLabel(
            "音符写法：1 2 3 4 5 6 7 8 = 按键 z x c v b n m ,（8 是逗号键）　"
            "前缀 ^ = 高音（按住鼠标右键）　b = 低音（左键）　# = 半音（中键）\n"
            "录音：点下面的「开始录音」（或按 %s），然后在游戏里照着弹一遍即可，"
            "录错了就点「撤销一个音」。\n"
            "保存：点「保存到曲谱库」；游戏在前台时也可以直接按 %s 保存（不用切窗口）。\n"
            "曲谱文件夹：默认在程序旁边的 songs 里（换电脑/分享只需整个文件夹一起拷）。"
            "想放到别处就点「曲谱文件夹…」。"
            % (self.ov.hk("toggle_record"), self.ov.hk("save_song")))
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#666;")
        lay.addWidget(tip)

        self.text = SongTextEdit(self)
        f = QFont("Consolas")
        f.setStyleHint(QFont.Monospace)
        f.setPointSize(12)
        self.text.setFont(f)
        self.text.setPlaceholderText("这里会显示音符…（也可以直接手动输入 / 粘贴）")
        self.text.setTabChangesFocus(True)
        self.text.textChanged.connect(self._refresh_status)
        lay.addWidget(self.text, 1)

        self.rec_btn = QPushButton("● 开始录音（%s）" % self.ov.hk("toggle_record"))
        self.undo_btn = QPushButton("撤销一个音（Ctrl+Z）")
        self.clear_btn = QPushButton("清空")
        self.load_btn = QPushButton("载入当前曲谱")
        self.import_btn = QPushButton("从文件导入…")
        self.save_btn = QPushButton("保存到曲谱库（Ctrl+S / %s）" % self.ov.hk("save_song"))
        self.export_btn = QPushButton("导出为文件…")
        self.folder_btn = QPushButton("曲谱文件夹…")
        self.open_btn = QPushButton("打开文件夹")
        self.rec_btn.setStyleSheet("font-weight:600;")

        lay.addLayout(self._row(self.rec_btn, self.undo_btn, self.clear_btn))
        lay.addLayout(self._row(self.load_btn, self.import_btn))
        lay.addLayout(self._row(self.save_btn, self.export_btn))
        lay.addLayout(self._row(self.folder_btn, self.open_btn))

        self.status = QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        self.rec_btn.clicked.connect(self.toggle_record)
        self.undo_btn.clicked.connect(self.undo_one)
        self.clear_btn.clicked.connect(self.clear_all)
        self.load_btn.clicked.connect(self.load_current)
        self.import_btn.clicked.connect(self.import_file)
        self.save_btn.clicked.connect(self.save_to_library)
        self.export_btn.clicked.connect(self.export_file)
        self.folder_btn.clicked.connect(self.choose_folder)
        self.open_btn.clicked.connect(self.open_folder)

        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_to_library)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self.export_file)
        QShortcut(QKeySequence("Escape"), self, activated=self.hide)
        self._refresh_status()

    @staticmethod
    def _row(*widgets):
        h = QHBoxLayout()
        h.setSpacing(6)
        for w in widgets:
            h.addWidget(w)
        return h

    # ---- 工具 ----

    def note_tokens(self):
        """文本里所有合法音符记号（含前缀，不含延长号/小节线）"""
        out = []
        for line in clean_song_body(self.text.toPlainText()).splitlines():
            for t in line.split("//")[0].split():
                if NOTE_RE.match(t):
                    out.append(t)
        return out

    def recorded_tokens(self):
        return self.note_tokens()

    def _cursor_to_end(self):
        c = self.text.textCursor()
        c.movePosition(QTextCursor.End)
        self.text.setTextCursor(c)

    def _refresh_status(self, *_):
        n = len(self.note_tokens())
        name = self.name_edit.text().strip() or "（还没起名字）"
        self.status.setText("曲名：%s ｜ 共 %d 个音 ｜ 保存位置：%s"
                            % (name, n, SONGS_DIR))
        self.status.setStyleSheet("color:#2a7; font-weight:600;" if n
                                  else "color:#999;")

    # ---- 录音 ----

    def toggle_record(self):
        self.ov.do_action("toggle_record")

    def set_recording_ui(self, on):
        self.recording = bool(on)
        hk = self.ov.hk("toggle_record")
        self.rec_btn.setText(("■ 结束录音（%s）" if on else "● 开始录音（%s）") % hk)
        self.rec_btn.setStyleSheet(
            "font-weight:600; background:#e24b4b; color:white;" if on
            else "font-weight:600;")
        self.text.setReadOnly(on)            # 录音时禁止手打，避免和录音打架
        for w in (self.name_edit, self.clear_btn, self.load_btn, self.import_btn):
            w.setEnabled(not on)
        # 注意：录音开始时不自动弹出编辑器（600×620 会挡住游戏画面）；
        #       叠加层上已经有"● 录音中 + 已录 N 个音"的提示，想看文本按 F11。
        self._refresh_status()

    def rec_append(self, token):
        lines = self.text.toPlainText().split("\n")
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            lines = [token]
        else:
            st = lines[-1].strip()
            head = st.split("=", 1)[0].strip().upper()
            cur = lines[-1].rstrip()
            if st.startswith("//") or head in ("TITLE", "BPM"):
                lines.append(token)                       # 不在注释/头部后面接着写
            elif len([t for t in cur.split() if t != "|"]) >= REC_WRAP:
                lines.append(token)                       # 一行写满了，换行
            else:
                lines[-1] = (cur + " " + token) if cur else token
        self.text.setPlainText("\n".join(lines) + "\n")
        self._cursor_to_end()
        self.text.ensureCursorVisible()

    def undo_one(self):
        before = len(self.note_tokens())
        lines = self.text.toPlainText().rstrip("\n").split("\n")
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            self.status.setText("没有可撤销的内容")
            return
        cur = lines[-1].rstrip()
        toks = cur.split()
        if not toks:
            lines.pop()
        elif toks[-1].startswith("//"):
            lines.pop()                                   # 整行是注释 → 撤销整行
        else:
            toks.pop()
            lines[-1] = " ".join(toks)
            if not lines[-1].strip():
                lines.pop()
        self.text.setPlainText(("\n".join(lines) + "\n") if lines else "")
        self._cursor_to_end()
        self.text.ensureCursorVisible()
        # 叠加层上那一串音符块要跟着一起消失（否则撤销后主窗口还留着已删的音）
        gone = before - len(self.note_tokens())
        if gone > 0:
            self.ov.truncate_rec(self.ov.rec_count - gone)
        self.status.setText("已撤销一个音 ｜ 现在共 %d 个音" % len(self.note_tokens()))

    def clear_all(self):
        if self.note_tokens() and QMessageBox.question(
                self, "清空", "确定清空当前编辑的内容吗？（曲谱库里已保存的文件不受影响）"
        ) != QMessageBox.Yes:
            return
        self.text.setPlainText("")
        self.ov.truncate_rec(0)

    # ---- 载入 / 导入 / 导出 / 保存 ----

    def load_current(self):
        raw = getattr(self.ov.song, "raw", "") or ""
        if not raw:
            return
        self.text.setPlainText(clean_song_body(raw) + "\n")
        self.name_edit.setText(self.ov.song.title)
        self.status.setText("已载入《%s》的 %d 个音，改完记得点「保存到曲谱库」"
                            % (self.ov.song.title, len(self.ov.song.notes)))

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入曲谱文件", SONGS_DIR or BASE_DIR, "曲谱文件 (*.txt);;所有文件 (*.*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            QMessageBox.warning(self, "导入失败", str(e))
            return
        title = os.path.splitext(os.path.basename(path))[0]
        for line in text.splitlines():
            if line.strip().upper().startswith("TITLE="):
                title = line.split("=", 1)[1].strip() or title
                break
        self.text.setPlainText(clean_song_body(text) + "\n")
        self.name_edit.setText(title)
        self.status.setText("已导入：%s" % path)

    def export_file(self):
        body = clean_song_body(self.text.toPlainText())
        if not body:
            QMessageBox.information(self, "还没有内容", "先录音或输入一些音符吧。")
            return
        name = self.name_edit.text().strip() or "未命名曲谱"
        default = os.path.join(BASE_DIR, safe_filename(name) + ".txt")
        path, _ = QFileDialog.getSaveFileName(self, "导出曲谱", default,
                                              "曲谱文件 (*.txt)")
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(game_song_text(name, body))
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
            return
        self.status.setText("已导出到：%s" % path)

    # ---- 曲谱文件夹 ----

    def choose_folder(self):
        """换一个曲谱文件夹（留空/选默认 = 回到程序旁边的 songs）"""
        cur = SONGS_DIR
        d = QFileDialog.getExistingDirectory(
            self, "选一个文件夹当曲谱库（放进这里的 .txt 会出现在面板列表里）", cur)
        if not d:
            return
        d = os.path.normpath(d)
        val = "" if is_default_songs_dir(d) else d
        self.ov.cfg["songs_dir"] = val
        self.ov._save_config({"songs_dir": val})
        new = apply_songs_dir(self.ov.cfg)
        if not is_default_songs_dir(new):
            have = [n for n in os.listdir(new) if n.lower().endswith(".txt")]
            if not have and QMessageBox.question(
                    self, "这个文件夹里还没有曲谱",
                    "要把程序自带的示例曲谱复制到\n%s\n里面吗？" % new) == QMessageBox.Yes:
                for name, text in SAMPLE_SONGS.items():
                    path = os.path.join(new, name)
                    if not os.path.exists(path):
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(text)
        self.ov.reload_songs()
        self._refresh_status()
        tail = "（默认：跟着程序走）" if is_default_songs_dir(new) else "（自定义）"
        self.status.setText("曲谱文件夹已切换%s：%s ｜ 现在共 %d 首"
                            % (tail, new, len(self.ov.songs)))
        self.status.setStyleSheet("color:#2a7; font-weight:600;")
        self.ov._say("曲谱文件夹：%s" % (os.path.basename(new) or new))

    def open_folder(self):
        os.makedirs(SONGS_DIR, exist_ok=True)
        try:
            os.startfile(SONGS_DIR)                     # Windows：资源管理器打开
        except Exception as e:
            QMessageBox.information(self, "曲谱文件夹",
                                    "曲谱就放在这个文件夹里：\n%s\n(%s)" % (SONGS_DIR, e))

    def save_to_library(self):
        return self._save(interactive=True)

    def save_quick(self):
        """热键（Shift+F3）用的静默保存：一个弹框都不弹。

        因为按 Shift+F3 的那一刻多半是游戏在前台，弹框会抢走焦点、打断演奏；
        曲名重名时也自动改成"某某2"，不打断玩家。
        """
        if self.recording:
            self.ov.set_recording(False)          # 还在录音就先收尾，避免存下没录完的内容
        return self._save(interactive=False)

    def _save(self, interactive):
        body = clean_song_body(self.text.toPlainText())
        name = self.name_edit.text().strip() or self._suggest_name()
        if not body:
            if interactive:
                QMessageBox.information(self, "还没有内容",
                                        "先录一遍音（%s），或在文本框里输入音符。" % self.ov.hk("toggle_record"))
            else:
                self.ov._say("还没录到音符，没法保存（先按 %s 录一遍）" % self.ov.hk("toggle_record"))
            return False
        if not self.name_edit.text().strip():
            self.name_edit.setText(name)          # 把自动起的名字显示出来，让用户看得见
        song = parse_song(game_song_text(name, body), name)
        if not song.notes:
            if interactive:
                QMessageBox.warning(
                    self, "没有识别到音符",
                    "文本里没有找到合法音符。\n写法示例：1 2 3 ^4 ^5 6 7 8\n"
                    "（1~8 对应按键 z x c v b n m ,  ，^ 表示高音）")
            else:
                self.ov._say("文本里没有合法音符，没法保存")
            return False
        os.makedirs(SONGS_DIR, exist_ok=True)
        path = os.path.join(SONGS_DIR, safe_filename(name) + ".txt")
        if os.path.exists(path):
            if interactive:
                if QMessageBox.question(
                        self, "覆盖确认",
                        "曲谱库里已经有《%s》了，要覆盖它吗？" % name
                ) != QMessageBox.Yes:
                    return False
            else:
                i = 2                              # 静默保存：自动换一个不重名的
                while os.path.exists(os.path.join(
                        SONGS_DIR, safe_filename("%s%d" % (name, i)) + ".txt")):
                    i += 1
                name = "%s%d" % (name, i)
                self.name_edit.setText(name)
                path = os.path.join(SONGS_DIR, safe_filename(name) + ".txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(game_song_text(name, body))
        except Exception as e:
            if interactive:
                QMessageBox.warning(self, "保存失败", str(e))
            else:
                self.ov._say("保存失败：%s" % e)
            return False
        self.ov.reload_songs(select_title=name)
        self.status.setText("已保存：%s（%d 个音）→ %s  面板列表已刷新"
                            % (name, len(song.notes), path))
        self.status.setStyleSheet("color:#2a7; font-weight:600;")
        if not interactive:
            self.ov._say("已保存《%s》（%d 个音）｜按 %s 换曲试听"
                         % (name, len(song.notes), self.ov.hk("next_song")))
        return True

    # ---- 窗口 ----

    def show_editor(self):
        self.show()
        self.raise_()
        self.activateWindow()
        if not self.name_edit.text().strip():
            self.name_edit.setText(self._suggest_name())    # 先给个不重名的名字，省得保存时弹框
            self.name_edit.selectAll()
        self._refresh_status()
        QTimer.singleShot(200, self._update_focus_hint)

    def _suggest_name(self):
        """songs 目录里挑一个不重复的默认曲名"""
        exist = set()
        try:
            for n in os.listdir(SONGS_DIR):
                exist.add(os.path.splitext(n)[0])
        except Exception:
            pass
        for i in range(1, 999):
            name = "我的曲谱%d" % i if i > 1 else "我的曲谱"
            if name not in exist:
                return name
        return "我的曲谱"

    def _update_focus_hint(self):
        self.focus_hint.setVisible(not self.isActiveWindow())

    def changeEvent(self, e):
        if e.type() == QEvent.ActivationChange:
            self.focus_hint.setVisible(not self.isActiveWindow())
        super().changeEvent(e)

    def closeEvent(self, e):
        if self.recording:
            self.ov.set_recording(False)
        e.ignore()
        self.hide()


def game_song_text(title, body):
    """拼出写入磁盘的曲谱文本"""
    return "BPM=90\nTITLE=%s\n%s\n" % (title, str(body).strip())


# ---------------------------------------------------------------- 入口

SAFETY_NOTE = ("[安全声明] 不安装键盘钩子、不模拟按键、不读写游戏内存、不注入游戏进程、不联网；"
               "仅用 GetAsyncKeyState 读取按键状态并绘制普通置顶分层窗口。")


def main():
    cfg = load_config()
    apply_songs_dir(cfg)              # 先决定曲谱目录，再补示例曲谱
    ensure_data_files()
    songs = load_songs()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ov = Overlay(cfg, songs)
    panel = PanelWindow(ov)
    ov.panel = panel
    editor = SongEditor(ov)
    ov.editor = editor
    ov.sync_panel()
    ov.show()
    panel.show()
    panel.raise_()
    ov._save_config({"hotkeys": cfg["hotkeys"]})     # 把新增热键写回 config.json
    QTimer.singleShot(200, ov._apply_clickthrough)
    QTimer.singleShot(220, panel.apply_style)
    print(SAFETY_NOTE)
    print("按键：%s" % " ".join(KEY_LABELS))
    print("热键（都要按住 Shift，避免和游戏里的 F 键抢键）：")
    for act, name in (("toggle_visible", "显示/隐藏全部窗口"), ("next_song", "换下一首"),
                      ("toggle_adjust", "锁定/调整窗口"), ("toggle_play", "从头重来"),
                      ("toggle_panel", "面板穿透"), ("editor", "曲谱编辑器"),
                      ("toggle_record", "开始/结束录音"), ("save_song", "保存曲谱"),
                      ("toggle_mode", "切换 经典/跟随演奏 模式"),
                      ("quit", "退出")):
        print("  %-20s %s" % (hotkey_text(cfg, act, " / "), name))
    print("也可以直接用鼠标点击窗口左侧面板上的按钮。")
    if not cfg.get("keyboard_monitor", True):
        print("[提示] keyboard_monitor=false：当前不读取任何键鼠输入，热键与灯带均不生效。")
    sys.exit(app.exec())


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _c0 = load_config()
        apply_songs_dir(_c0)
        ensure_data_files()
        c = load_config()
        ss = load_songs()
        for s in ss:
            print("曲谱: %-16s BPM %-4s 音符数 %-3d 时长 %.1f 拍" % (
                s.title, round(s.bpm), len(s.notes), s.total_beats))
        print("通道按键:", " ".join(KEY_LABELS),
              "| config.note_keys:", c.get("note_keys"),
              "| VK:", ["0x%02X" % (vk_of(k) or 0) for k in (c.get("note_keys") or DEFAULT_NOTE_KEYS)])
        print("热键:", ", ".join("%s=%s" % (k, v) for k, v in c["hotkeys"].items()))
        print("面板按钮:", ", ".join(a for row in PANEL_ROWS for a, _ in row))
        print("keyboard_monitor:", c.get("keyboard_monitor"),
              "| panel_width:", c.get("panel_width"),
              "| panel_interactive:", c.get("panel_interactive"))
        print("曲谱文件夹:", SONGS_DIR, "(默认)" if is_default_songs_dir(SONGS_DIR) else "(自定义)")
        sys.exit(0)
    main()
