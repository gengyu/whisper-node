@echo off
chcp 65001 >nul

echo 🎤 启动 Whisper Subtitle Generator 服务器
echo ======================================

REM 检查虚拟环境
if not exist ".venv" (
    echo ❌ 虚拟环境不存在，请先运行安装脚本
    echo    python install.py
    pause
    exit /b 1
)

REM 激活虚拟环境
echo 📦 激活虚拟环境...
call .venv\Scripts\activate.bat

REM 检查依赖
echo 🔍 检查依赖...
python -c "import whisper_subtitle" 2>nul
if errorlevel 1 (
    echo ❌ 依赖未安装，请先运行：
    echo    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
    pause
    exit /b 1
)

REM 启动服务器
echo 🚀 启动服务器...
echo    Web界面: http://127.0.0.1:8000
echo    API文档: http://127.0.0.1:8000/docs
echo    按 Ctrl+C 停止服务器
echo.

set PYTHONPATH=src
python -m whisper_subtitle.cli server --host 127.0.0.1 --port 8000

pause