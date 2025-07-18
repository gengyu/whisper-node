#!/usr/bin/env python3
"""
完整工作流演示脚本
YouTube视频下载 -> 字幕提取/翻译 -> 视频合并
"""

import os
import sys
import random
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# 中文翻译词库
CHINESE_PHRASES = [
    "大家好，欢迎来到我们的频道",
    "今天我们将学习一些新的内容",
    "请大家订阅并点赞这个视频",
    "感谢大家的观看和支持",
    "这是一个非常有趣的话题",
    "让我们一起来探索这个问题",
    "希望这个视频对大家有帮助",
    "不要忘记分享给你的朋友们",
    "我们下期视频再见",
    "记得打开小铃铛接收通知"
]

def log_step(step_num, description):
    """记录步骤"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] 步骤 {step_num}: {description}")
    print("-" * 50)

def simulate_translation(english_text):
    """模拟英文到中文翻译"""
    if not english_text.strip():
        return english_text
    
    # 根据关键词进行简单的翻译映射
    text_lower = english_text.lower()
    
    if any(word in text_lower for word in ['hello', 'hi', 'welcome']):
        return "大家好，欢迎来到我们的频道"
    elif any(word in text_lower for word in ['today', 'learn', 'new']):
        return "今天我们将学习一些新的内容"
    elif any(word in text_lower for word in ['subscribe', 'like']):
        return "请大家订阅并点赞这个视频"
    elif any(word in text_lower for word in ['thank', 'watching']):
        return "感谢大家的观看和支持"
    else:
        # 随机选择一个中文短语
        return random.choice(CHINESE_PHRASES)

def create_sample_srt():
    """创建示例SRT字幕文件"""
    srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello everyone, welcome to our channel.

2
00:00:05,000 --> 00:00:08,000
Today we will learn something new and exciting.

3
00:00:09,000 --> 00:00:12,000
Please subscribe and like this video.

4
00:00:13,000 --> 00:00:16,000
Thank you for watching and see you next time.

5
00:00:17,000 --> 00:00:20,000
Don't forget to hit the notification bell.
"""
    return srt_content

def translate_srt_content(srt_content):
    """翻译SRT内容"""
    lines = srt_content.strip().split('\n')
    translated_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not line.isdigit() and '-->' not in line:
            # 这是字幕文本行
            translated_line = simulate_translation(line)
            translated_lines.append(translated_line)
        else:
            # 保持序号和时间戳不变
            translated_lines.append(line)
    
    return '\n'.join(translated_lines)

def create_test_video(output_file, duration=25):
    """创建测试视频"""
    try:
        # 创建一个带有文字的彩色视频
        cmd = f"""ffmpeg -f lavfi -i color=c=blue:size=1280x720:duration={duration} \
                 -vf "drawtext=fontfile=/System/Library/Fonts/Arial.ttf:text='测试视频 Test Video':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
                 -c:v libx264 -t {duration} -pix_fmt yuv420p "{output_file}" -y"""
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 测试视频创建成功: {output_file}")
            return True
        else:
            print(f"❌ 视频创建失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 创建视频异常: {e}")
        return False

def merge_subtitles_to_video(video_file, srt_file, output_file):
    """将字幕合并到视频"""
    try:
        # 使用ffmpeg将字幕烧录到视频中
        cmd = f"""ffmpeg -i "{video_file}" \
                 -vf "subtitles='{srt_file}':force_style='Fontsize=24,PrimaryColour=&Hffffff&,OutlineColour=&H000000&,Outline=2'" \
                 -c:a copy "{output_file}" -y"""
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 字幕合并成功: {output_file}")
            return True
        else:
            print(f"❌ 字幕合并失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 合并异常: {e}")
        return False

def show_file_info(filepath, description):
    """显示文件信息"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath) / (1024 * 1024)  # MB
        print(f"✅ {description}: {os.path.basename(filepath)} ({size:.2f} MB)")
        return True
    else:
        print(f"❌ {description}: 文件不存在")
        return False

def main():
    print("🎬 YouTube视频处理完整工作流演示")
    print("=" * 60)
    print("流程: 视频创建 -> 字幕翻译 -> 字幕合并 -> 最终输出")
    print("特点: 模拟翻译，无需API调用")
    print("=" * 60)
    
    # 创建工作目录
    work_dir = "demo_workflow"
    os.makedirs(work_dir, exist_ok=True)
    
    # 文件路径
    original_srt = os.path.join(work_dir, "original_subtitles.srt")
    translated_srt = os.path.join(work_dir, "chinese_subtitles.srt")
    test_video = os.path.join(work_dir, "test_video.mp4")
    final_video = os.path.join(work_dir, "final_video_with_chinese_subs.mp4")
    
    try:
        # 步骤1: 创建原始字幕文件
        log_step(1, "创建原始英文字幕文件")
        srt_content = create_sample_srt()
        
        with open(original_srt, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        print("原始字幕内容预览:")
        print(srt_content[:200] + "...")
        print(f"✅ 字幕文件保存: {original_srt}")
        
        # 步骤2: 翻译字幕
        log_step(2, "翻译字幕为中文")
        translated_content = translate_srt_content(srt_content)
        
        with open(translated_srt, 'w', encoding='utf-8') as f:
            f.write(translated_content)
        
        print("翻译后字幕预览:")
        print(translated_content[:200] + "...")
        print(f"✅ 中文字幕保存: {translated_srt}")
        
        # 步骤3: 创建测试视频
        log_step(3, "创建测试视频")
        if not create_test_video(test_video):
            print("❌ 无法创建测试视频，请检查ffmpeg安装")
            return False
        
        # 步骤4: 合并字幕到视频
        log_step(4, "将中文字幕合并到视频")
        if not merge_subtitles_to_video(test_video, translated_srt, final_video):
            print("❌ 字幕合并失败")
            return False
        
        # 步骤5: 显示结果
        log_step(5, "工作流完成，显示结果")
        print("\n📁 生成的文件:")
        show_file_info(original_srt, "原始英文字幕")
        show_file_info(translated_srt, "翻译中文字幕")
        show_file_info(test_video, "原始测试视频")
        show_file_info(final_video, "最终合并视频")
        
        # 显示详细的翻译对比
        print("\n📝 翻译对比示例:")
        print("-" * 40)
        
        try:
            with open(original_srt, 'r', encoding='utf-8') as f:
                orig_lines = f.readlines()
            
            with open(translated_srt, 'r', encoding='utf-8') as f:
                trans_lines = f.readlines()
            
            # 显示前几行对比
            for i, (orig, trans) in enumerate(zip(orig_lines[:8], trans_lines[:8])):
                if orig.strip() and not orig.strip().isdigit() and '-->' not in orig:
                    print(f"英文: {orig.strip()}")
                    print(f"中文: {trans.strip()}")
                    print()
                    
        except Exception as e:
            print(f"读取文件失败: {e}")
        
        print("\n🎉 完整工作流演示成功！")
        print(f"\n📂 所有文件保存在: {os.path.abspath(work_dir)}")
        print("\n🎥 可以使用视频播放器打开最终视频查看效果")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 工作流失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 演示完成！")
    else:
        print("\n❌ 演示失败！")
    
    sys.exit(0 if success else 1)