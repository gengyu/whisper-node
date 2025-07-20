#!/bin/bash


## 激活虚拟环境
#source .venv/bin/activate
#
## 启动服务器
#PYTHONPATH=src python -m whisper_subtitle.cli server
#
## 或使用启动脚本
#./start_server.sh

# Whisper Subtitle Generator 启动脚本

echo "🎤 启动 Whisper Subtitle Generator 服务器"
echo "======================================"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行安装脚本"
    echo "   python install.py"
    exit 1
fi

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source .venv/bin/activate

# 检查依赖
echo "🔍 检查依赖..."
if ! python -c "import whisper_subtitle" 2>/dev/null; then
    echo "❌ 依赖未安装，请先运行："
    echo "   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn"
    exit 1
fi

# 启动服务器
echo "🚀 启动服务器..."
echo "   Web界面: http://127.0.0.1:8000"
echo "   API文档: http://127.0.0.1:8000/docs"
echo "   按 Ctrl+C 停止服务器"
echo ""

PYTHONPATH=src python -m whisper_subtitle.cli server --host 127.0.0.1 --port 8000