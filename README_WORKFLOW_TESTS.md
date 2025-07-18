# YouTube视频处理完整工作流测试脚本

本项目包含了从YouTube下载视频、提取字幕、翻译成中文、再合并到原视频的完整工作流测试脚本。

## 📁 测试脚本说明

### 1. `test_complete_workflow.py` - 完整工作流脚本
**功能**: 最完整的工作流测试，支持YouTube下载和本地测试两种模式

**特点**:
- ✅ 支持YouTube视频下载（需要yt-dlp）
- ✅ 支持本地测试视频生成
- ✅ 字幕提取和翻译
- ✅ 视频字幕合并
- ✅ 模拟中文翻译（无需API）

**使用方法**:
```bash
python test_complete_workflow.py
# 选择模式：1=测试模式，2=YouTube下载模式
```

### 2. `quick_workflow_test.py` - 快速验证脚本
**功能**: 简化版工作流，专注于核心功能验证

**特点**:
- ✅ 快速测试字幕翻译
- ✅ 视频创建和合并
- ✅ 结果文件检查
- ✅ 轻量级实现

**使用方法**:
```bash
python quick_workflow_test.py
```

### 3. `demo_complete_workflow.py` - 演示脚本
**功能**: 最佳的演示版本，包含详细的步骤说明和结果展示

**特点**:
- ✅ 详细的步骤日志
- ✅ 翻译对比展示
- ✅ 文件信息统计
- ✅ 用户友好的输出

**使用方法**:
```bash
python demo_complete_workflow.py
```

## 🛠️ 依赖要求

### 必需依赖
- **Python 3.7+**
- **FFmpeg** - 用于视频处理和字幕合并
  ```bash
  # macOS
  brew install ffmpeg
  
  # Ubuntu/Debian
  sudo apt update && sudo apt install ffmpeg
  
  # Windows
  # 下载并安装 https://ffmpeg.org/download.html
  ```

### 可选依赖
- **yt-dlp** - 用于YouTube视频下载（仅完整工作流需要）
  ```bash
  pip install yt-dlp
  ```

## 📊 工作流程说明

### 完整流程
```
1. 视频获取
   ├── YouTube下载 (yt-dlp)
   └── 本地测试视频生成 (ffmpeg)

2. 字幕处理
   ├── 字幕提取 (whisper/自动字幕)
   ├── SRT解析
   └── 模拟中文翻译

3. 视频合并
   ├── 字幕烧录 (ffmpeg)
   └── 最终视频输出
```

### 翻译模拟机制
- 🎯 **智能关键词映射**: 根据英文关键词选择对应中文翻译
- 🎲 **随机短语生成**: 使用预设中文短语库
- 📝 **SRT格式保持**: 保持原有时间戳和格式

## 📁 输出文件结构

每个脚本都会创建独立的工作目录：

```
workflow_test/          # test_complete_workflow.py
├── test_video.mp4
├── test_video.srt
├── translated_subtitles.srt
└── final_video_with_chinese_subtitles.mp4

quick_test/             # quick_workflow_test.py
├── original.srt
├── translated.srt
├── test_video.mp4
└── final_video.mp4

demo_workflow/          # demo_complete_workflow.py
├── original_subtitles.srt
├── chinese_subtitles.srt
├── test_video.mp4
└── final_video_with_chinese_subs.mp4
```

## 🎯 使用场景

### 开发测试
推荐使用 `demo_complete_workflow.py`
- 详细的步骤输出
- 完整的结果展示
- 适合功能验证

### 快速验证
推荐使用 `quick_workflow_test.py`
- 快速执行
- 核心功能测试
- 适合CI/CD

### 完整演示
推荐使用 `test_complete_workflow.py`
- 支持真实YouTube下载
- 完整工作流展示
- 适合产品演示

## 🔧 自定义配置

### 修改翻译词库
在脚本中找到 `CHINESE_PHRASES` 或 `CHINESE_TRANSLATIONS` 数组，添加自定义中文翻译：

```python
CHINESE_PHRASES = [
    "你的自定义翻译1",
    "你的自定义翻译2",
    # 添加更多...
]
```

### 调整视频参数
修改 `create_test_video()` 函数中的参数：

```python
# 视频尺寸
size=1280x720

# 视频时长
duration=25

# 字体大小
fontsize=48
```

## ⚠️ 注意事项

1. **FFmpeg安装**: 所有脚本都需要FFmpeg支持
2. **字体支持**: 中文字幕需要系统支持中文字体
3. **磁盘空间**: 视频文件可能占用较多空间
4. **网络连接**: YouTube下载需要稳定网络
5. **API限制**: 当前使用模拟翻译，实际使用需配置翻译API

## 🚀 扩展功能

### 集成真实翻译API
替换 `simulate_translation()` 函数，调用真实的翻译服务：

```python
def real_translation(text, target_lang='zh'):
    # 调用阿里云、百度、Google等翻译API
    # 返回翻译结果
    pass
```

### 支持更多视频格式
修改FFmpeg命令支持更多输入/输出格式：

```python
# 支持更多视频格式
supported_formats = ['.mp4', '.avi', '.mkv', '.mov', '.webm']
```

### 批量处理
扩展脚本支持批量处理多个视频文件。

## 📞 技术支持

如果遇到问题，请检查：
1. FFmpeg是否正确安装
2. Python版本是否兼容
3. 文件权限是否正确
4. 磁盘空间是否充足

---

**最后更新**: 2024年
**版本**: 1.0.0
**作者**: Whisper Subtitle Generator Team