# 激活虚拟环境
source .venv/bin/activate

# 启动服务器
PYTHONPATH=src python -m whisper_subtitle.cli server

# 或使用启动脚本
./start_server.sh


### 📋 可用的CLI命令
- 查看帮助： PYTHONPATH=src python -m whisper_subtitle.cli --help
- 系统信息： PYTHONPATH=src python -m whisper_subtitle.cli info
- 引擎检查： PYTHONPATH=src python -m whisper_subtitle.cli check
- 转录文件： PYTHONPATH=src python -m whisper_subtitle.cli transcribe audio.mp3