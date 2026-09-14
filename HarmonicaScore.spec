# -*- mode: python ; coding: utf-8 -*-
"""三角洲口琴曲谱 —— 瘦身打包配置

只保留程序真正用到的 Qt 运行时（QtCore / QtGui / QtWidgets）。
原 45MB 里有一大半是用不到的东西：软件 OpenGL 模拟（7.7MB）、QML/Quick（5MB）、
QtPdf（2.5MB）、QtNetwork + OpenSSL（3.4MB）等等。

用：python -m PyInstaller --noconfirm HarmonicaScore.spec
"""
import os

# ---- 用不到的 PySide6 子模块（PyInstaller 层面直接不分析）----
EXCLUDES = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebView", "PySide6.QtWebChannel", "PySide6.QtWebSockets",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuickControls2",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtSpatialAudio",
    "PySide6.QtNetwork", "PySide6.QtNetworkAuth",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtDBus",
    "PySide6.QtPrintSupport", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtDesigner", "PySide6.QtUiTools", "PySide6.QtHelp",
    "PySide6.QtSerialPort", "PySide6.QtSerialBus",
    "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtRemoteObjects", "PySide6.QtStateMachine", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtPositioning", "PySide6.QtLocation",
    "PySide6.QtTextToSpeech", "PySide6.QtConcurrent", "PySide6.QtHttpServer",
    "PySide6.QtGraphs", "PySide6.QtVirtualKeyboard",
    "tkinter",
]

# ---- 二进制 / 数据文件黑名单（按小写子串匹配）----
# ⚠️ 绝对不能删的：Qt6Core / Qt6Gui / Qt6Widgets / python313.dll /
#    PySide6\platforms\qwindows.dll / plugins\styles\* / shiboken6.*
DROP = [
    # Qt 的软件 OpenGL 模拟（纯 QWidget 绘制用不到）
    "opengl32sw.dll",
    # 各大 Qt 模块（含它们依赖的 DLL）
    "qt6quick", "qt6qml", "qt6pdf", "qt6network", "qt6opengl", "qt6openglwidgets",
    "qt6svg", "qt6sql", "qt6test", "qt6xml", "qt6dbus", "qt6print", "qt6websockets",
    "qt6webchannel", "qt6webview", "qt6webengine", "qt6charts", "qt6multimedia",
    "qt6avcodec", "qt6avformat", "qt6avutil", "qt6swresample", "qt6swscale",
    "qt63d", "qt6sensors", "qt6positioning", "qt6location", "qt6texttospeech",
    "qt6concurrent", "qt6httpserver", "qt6graphs", "qt6remoteobjects", "qt6statemachine",
    "qt6designer", "qt6help", "qt6uitools", "qt6serialport", "qt6serialbus",
    "qt6bluetooth", "qt6nfc", "qt6spatialaudio", "qt6virtualkeyboard", "qt6scxml",
    "qt6labswavefrontmesh", "qt6labssettings", "qt6labssharedimage", "qt6labscalendar",
    "qt6shadertools", "qt6networkauth", "qt6qmlmodels", "qt6qmlworkerscript",
    # 对应的 PySide6 python 扩展
    "pyside6\\qtquick", "pyside6\\qtqml", "pyside6\\qtpdf", "pyside6\\qtnetwork",
    "pyside6\\qtopengl", "pyside6\\qtsvg", "pyside6\\qtsql", "pyside6\\qttest",
    "pyside6\\qtxml", "pyside6\\qtdbus", "pyside6\\qtprintsupport", "pyside6\\qtcharts",
    "pyside6\\qtmultimedia", "pyside6\\qt3d", "pyside6\\qtwebengine", "pyside6\\qtconcurrent",
    "pyside6\\qtuitools", "pyside6\\qtscxml", "pyside6\\qttexttospeech",
    "pyside6\\qtbluetooth", "pyside6\\qtpositioning", "pyside6\\qtsensors",
    # 只有 Qt6Network 才需要的加密库
    "libcrypto-3-x64", "libssl-3-x64",
    # 用不到的插件（保留 qwindows / qmodernwindowsstyle / qico / qjpeg）
    "plugins\\sqldrivers", "plugins\\tls", "plugins\\networkinformation",
    "plugins\\platforms\\qdirect2d", "plugins\\platforms\\qminimal",
    "plugins\\platforms\\qwebgl",
    "plugins\\imageformats\\qpdf", "plugins\\imageformats\\qsvg",
    "plugins\\imageformats\\qtga", "plugins\\imageformats\\qtiff",
    "plugins\\imageformats\\qwbmp", "plugins\\imageformats\\qwebp",
    "plugins\\imageformats\\qicns", "plugins\\imageformats\\qgif",
    "plugins\\generic", "plugins\\iconengines",
    # Qt 的翻译文件用不到（我们是自绘界面，没有 Qt 标准对话框文字）
    "pyside6\\translations", "translations\\qt",
]


def _keep(name):
    low = name.lower().replace("/", "\\")
    for s in DROP:
        if s in low:
            return False
    return True


a = Analysis(
    ["harmonica_visualizer.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)

_bin_before = len(a.binaries)
a.binaries = [b for b in a.binaries if _keep(b[0])]
a.datas = [d for d in a.datas if _keep(d[0])]
print("[瘦身] binaries %d -> %d ; datas -> %d" % (_bin_before, len(a.binaries), len(a.datas)))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HarmonicaScore",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # 不开 UPX：压缩过的 exe 更容易被杀软误报
    console=False,                  # 不弹黑框
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
