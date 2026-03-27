@echo off
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
    py app.py
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python app.py
    goto :eof
)

echo 未检测到 Python，请先安装 Python 3.10 或更高版本。
echo 安装后可双击此文件，或运行: python app.py
pause
