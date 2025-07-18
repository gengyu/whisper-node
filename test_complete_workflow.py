#!/usr/bin/env python3
"""
完整工作流测试脚本
从YouTube下载视频 -> 提取字幕 -> 翻译成中文 -> 合并到原视频
"""

import os
import sys
import random
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# 模拟中文翻译词库
CHINESE_TRANSLATIONS = [
    "你好，这是一个测试字幕。",
    "这是第二行字幕内容。",
    "这是第三行字幕。",
    "欢迎观看这个视频。",
    "感谢您的观看。",
    "这是一个很棒的视频。",
    "让我们开始学习吧。",
    "这个内容非常有趣。",
    "希望您喜欢这个视频。",
    "请订阅我们的频道。",
    "下次见！",
    "这是重要的信息。",
    "请注意这个细节。",
    "让我们继续下一个话题。",
    "这是一个很好的例子。"
]

def log_step(step, message):
    """记录步骤日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 步骤 {step}: {message}")

def run_command(cmd, description, check_output=False):
    """运行命令并返回结果"""
    log_step("CMD", f"{description}")
    print(f"执行命令: {cmd}")
    
    try:
        if check_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True, check=True)
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def simulate_translation(text):
    """模拟翻译：随机生成中文"""
    # 简单的模拟翻译逻辑
    if not text.strip():
        return text
    
    # 随机选择一个中文翻译
    return random.choice(CHINESE_TRANSLATIONS)

def parse_srt_content(content):
    """解析SRT内容"""
    blocks = []
    current_block = {}
    lines = content.strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.isdigit():  # 字幕序号
            if current_block:
                blocks.append(current_block)
            current_block = {'index': int(line)}
        elif '-->' in line:  # 时间戳
            current_block['timing'] = line
        elif line:  # 字幕文本
            if 'text' not in current_block:
                current_block['text'] = []
            current_block['text'].append(line)
        elif not line and current_block:  # 空行，结束当前块
            blocks.append(current_block)
            current_block = {}
        
        i += 1
    
    if current_block:
        blocks.append(current_block)
    
    return blocks

def format_srt_content(blocks):
    """格式化SRT内容"""
    result = []
    for block in blocks:
        if 'index' in block and 'timing' in block and 'text' in block:
            result.append(str(block['index']))
            result.append(block['timing'])
            result.extend(block['text'])
            result.append('')  # 空行分隔
    
    return '\n'.join(result)

def translate_srt_file(input_file, output_file):
    """翻译SRT文件"""
    log_step("TRANSLATE", f"翻译字幕文件: {input_file} -> {output_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析SRT内容
        blocks = parse_srt_content(content)
        
        # 翻译每个文本块
        for block in blocks:
            if 'text' in block:
                translated_text = []
                for text_line in block['text']:
                    translated_line = simulate_translation(text_line)
                    translated_text.append(translated_line)
                block['text'] = translated_text
        
        # 格式化并保存
        translated_content = format_srt_content(blocks)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated_content)
        
        print(f"✅ 字幕翻译完成，共翻译 {len(blocks)} 个字幕块")
        return True
        
    except Exception as e:
        print(f"❌ 翻译失败: {e}")
        return False

def download_youtube_video(url, output_dir):
    """下载YouTube视频"""
    log_step("DOWNLOAD", f"下载YouTube视频: {url}")
    
    # 检查yt-dlp是否安装
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ yt-dlp 未安装，请先安装: pip install yt-dlp")
        return None, None
    
    try:
        # 下载视频和字幕
        cmd = f"yt-dlp -f 'best[height<=720]' --write-auto-sub --sub-lang en --convert-subs srt -o '{output_dir}/%(title)s.%(ext)s' '{url}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 下载失败: {result.stderr}")
            return None, None
        
        # 查找下载的文件
        video_files = list(Path(output_dir).glob("*.mp4")) + list(Path(output_dir).glob("*.webm")) + list(Path(output_dir).glob("*.mkv"))
        srt_files = list(Path(output_dir).glob("*.srt"))
        
        if video_files and srt_files:
            video_file = str(video_files[0])
            srt_file = str(srt_files[0])
            print(f"✅ 下载完成")
            print(f"   视频文件: {video_file}")
            print(f"   字幕文件: {srt_file}")
            return video_file, srt_file
        else:
            print("❌ 未找到下载的视频或字幕文件")
            return None, None
            
    except Exception as e:
        print(f"❌ 下载异常: {e}")
        return None, None

def extract_subtitles_from_video(video_file, output_srt):
    """从视频提取字幕（使用whisper）"""
    log_step("EXTRACT", f"从视频提取字幕: {video_file}")
    
    try:
        # 使用whisper提取字幕
        cmd = f"python -m whisper_subtitle.cli transcribe '{video_file}' --output-format srt --output-file '{output_srt}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_srt):
            print(f"✅ 字幕提取完成: {output_srt}")
            return True
        else:
            print(f"❌ 字幕提取失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 字幕提取异常: {e}")
        return False

def merge_subtitles_to_video(video_file, srt_file, output_video):
    """将字幕合并到视频"""
    log_step("MERGE", f"合并字幕到视频: {video_file} + {srt_file}")
    
    # 检查ffmpeg是否安装
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ffmpeg 未安装，请先安装 ffmpeg")
        return False
    
    try:
        # 使用ffmpeg合并字幕
        cmd = f"ffmpeg -i '{video_file}' -vf \"subtitles='{srt_file}'\" -c:a copy '{output_video}' -y"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_video):
            print(f"✅ 视频合并完成: {output_video}")
            return True
        else:
            print(f"❌ 视频合并失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 视频合并异常: {e}")
        return False

def create_test_video_and_srt():
    """创建测试视频和字幕文件"""
    log_step("CREATE", "创建测试视频和字幕文件")
    
    # 创建测试SRT文件
    test_srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello, this is a test video.

2
00:00:04,000 --> 00:00:06,000
Welcome to our channel.

3
00:00:07,000 --> 00:00:09,000
Please subscribe and like.

4
00:00:10,000 --> 00:00:12,000
Thank you for watching.
"""
    
    test_srt_file = "test_video.srt"
    with open(test_srt_file, 'w', encoding='utf-8') as f:
        f.write(test_srt_content)
    
    # 创建测试视频（10秒黑屏视频）
    test_video_file = "test_video.mp4"
    
    try:
        cmd = f"ffmpeg -f lavfi -i color=black:size=640x480:duration=12 -c:v libx264 -t 12 -pix_fmt yuv420p '{test_video_file}' -y"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 测试文件创建完成")
            print(f"   视频: {test_video_file}")
            print(f"   字幕: {test_srt_file}")
            return test_video_file, test_srt_file
        else:
            print(f"❌ 测试视频创建失败: {result.stderr}")
            return None, None
            
    except Exception as e:
        print(f"❌ 创建测试文件异常: {e}")
        return None, None

def main():
    print("🎬 完整工作流测试脚本")
    print("=" * 60)
    print("功能: YouTube下载 -> 字幕提取 -> 中文翻译 -> 视频合并")
    print("=" * 60)
    
    # 创建工作目录
    work_dir = "workflow_test"
    os.makedirs(work_dir, exist_ok=True)
    os.chdir(work_dir)
    
    try:
        # 选择测试模式
        print("\n📋 选择测试模式:")
        print("1. 使用测试视频（推荐）")
        print("2. 从YouTube下载视频")
        
        choice = input("请选择 (1/2): ").strip()
        
        video_file = None
        srt_file = None
        
        if choice == "2":
            # YouTube下载模式
            youtube_url = input("请输入YouTube视频URL: ").strip()
            if youtube_url:
                video_file, srt_file = download_youtube_video(youtube_url, ".")
        
        if not video_file or choice == "1":
            # 测试模式
            log_step("TEST", "使用测试模式")
            video_file, srt_file = create_test_video_and_srt()
        
        if not video_file or not srt_file:
            print("❌ 无法获取视频或字幕文件")
            return False
        
        # 如果没有字幕文件，尝试提取
        if not os.path.exists(srt_file):
            extracted_srt = "extracted_subtitles.srt"
            if extract_subtitles_from_video(video_file, extracted_srt):
                srt_file = extracted_srt
            else:
                print("❌ 无法提取字幕")
                return False
        
        # 翻译字幕
        translated_srt = "translated_subtitles.srt"
        if not translate_srt_file(srt_file, translated_srt):
            print("❌ 字幕翻译失败")
            return False
        
        # 显示翻译结果
        print("\n📝 翻译结果预览:")
        print("-" * 40)
        try:
            with open(translated_srt, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content[:500] + "..." if len(content) > 500 else content)
        except Exception as e:
            print(f"无法读取翻译文件: {e}")
        
        # 合并字幕到视频
        output_video = "final_video_with_chinese_subtitles.mp4"
        if not merge_subtitles_to_video(video_file, translated_srt, output_video):
            print("❌ 视频合并失败")
            return False
        
        # 成功完成
        print("\n🎉 工作流完成！")
        print("=" * 60)
        print(f"📁 工作目录: {os.getcwd()}")
        print(f"🎥 原视频: {video_file}")
        print(f"📄 原字幕: {srt_file}")
        print(f"🇨🇳 中文字幕: {translated_srt}")
        print(f"🎬 最终视频: {output_video}")
        
        # 显示文件大小
        try:
            original_size = os.path.getsize(video_file) / (1024*1024)
            final_size = os.path.getsize(output_video) / (1024*1024)
            print(f"\n📊 文件大小:")
            print(f"   原视频: {original_size:.1f} MB")
            print(f"   最终视频: {final_size:.1f} MB")
        except:
            pass
        
        print("\n✅ 所有步骤完成！")
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        return False
    except Exception as e:
        print(f"\n❌ 工作流异常: {e}")
        return False
    finally:
        # 返回原目录
        os.chdir("..")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)