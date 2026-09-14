@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo   正在打包 exe（瘦身配置），请稍候约 1 分钟...
echo   只保留程序用得到的 QtCore / QtGui / QtWidgets，体积约 22MB（原来 45MB）
echo.
"C:\Users\Admin\.workbuddy\binaries\python\envs\default\Scripts\python.exe" -m PyInstaller --noconfirm --distpath dist --workpath build HarmonicaScore.spec
if errorlevel 1 (
    echo.
    echo   [打包失败] 请看上面的红色报错信息
    pause
    exit /b 1
)
echo.
echo   打包完成！exe 在 dist\HarmonicaScore.exe
echo   下一步：把它复制到 ..\口琴曲谱\ 并改名成「三角洲口琴曲谱.exe」
echo   然后跑一次 python _tests\_t_smoke.py 确认能正常启动
echo.
pause
