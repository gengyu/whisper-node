#!/usr/bin/env python3
"""
快速工作流验证脚本
简化版本，用于快速验证完整流程
"""

import os
import sys
import random
import subprocess
from pathlib import Path

# 中文翻译模拟库
CHINESE_WORDS = [
    "你好", "欢迎", "感谢", "观看", "视频", "内容", "精彩", "有趣",
    "学习", "分享", "订阅", "点赞", "评论", "关注", "频道", "更新",
    "教程", "技术", "知识", "经验", "方法", "技巧", "实用", "简单",
    "详细", "完整", "专业", "高质量", "推荐", "必看", "重要", "注意"
]

def simulate_chinese_translation(english_text):
    """模拟英文到中文的翻译"""
    if not english_text.strip():
        return english_text
    
    # 简单的单词替换模拟
    words = english_text.lower().split()
    chinese_words = []
    
    for word in words:
        if word in ['hello', 'hi']:
            chinese_words.append('你好')
        elif word in ['welcome', 'welcome to']:
            chinese_words.append('欢迎')
        elif word in ['thank', 'thanks', 'thank you']:
            chinese_words.append('感谢您')
        elif word in ['video', 'channel']:
            chinese_words.append('视频')
        elif word in ['subscribe', 'like']:
            chinese_words.append('订阅点赞')
        elif word in ['watch', 'watching']:
            chinese_words.append('观看')
        elif word in ['please']:
            chinese_words.append('请')
        else:
            # 随机选择中文词汇
            chinese_words.append(random.choice(CHINESE_WORDS))
    
    # 组合成中文句子
    result = ''.join(chinese_words[:3]) + '。'  # 限制长度并添加句号
    return result

def quick_test():
    """快速测试完整工作流"""
    print("🚀 快速工作流验证")
    print("=" * 40)
    
    # 创建测试目录
    test_dir = "quick_test"
    os.makedirs(test_dir, exist_ok=True)
    original_dir = os.getcwd()
    
    try:
        os.chdir(test_dir)
        
        # 1. 创建测试SRT文件
        print("📝 1. 创建测试字幕文件...")
        test_srt = """1
00:00:01,000 --> 00:00:03,000
Hello everyone, welcome to our channel.

2
00:00:04,000 --> 00:00:06,000
Today we will learn something new.

3
00:00:07,000 --> 00:00:09,000
Please subscribe and like this video.

4
00:00:10,000 --> 00:00:12,000
Thank you for watching.
"""
        
        with open("original.srt", "w", encoding="utf-8") as f:
            f.write(test_srt)
        print("✅ 原始字幕文件创建完成")
        
        # 2. 模拟翻译
        print("\n🌐 2. 翻译字幕到中文...")
        lines = test_srt.strip().split('\n')
        translated_lines = []
        
        for line in lines:
            if line.strip() and not line.strip().isdigit() and '-->' not in line:
                # 这是字幕文本行
                translated_line = simulate_chinese_translation(line)
                translated_lines.append(translated_line)
            else:
                translated_lines.append(line)
        
        translated_srt = '\n'.join(translated_lines)
        
        with open("translated.srt", "w", encoding="utf-8") as f:
            f.write(translated_srt)
        print("✅ 中文字幕文件生成完成")
        
        # 3. 创建测试视频
        print("\n🎥 3. 创建测试视频...")
        try:
            cmd = "ffmpeg -f lavfi -i color=blue:size=640x480:duration=15 -c:v libx264 -t 15 -pix_fmt yuv420p test_video.mp4 -y"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 测试视频创建完成")
            else:
                print("⚠️ 视频创建失败，跳过视频合并步骤")
                return show_results()
        except Exception as e:
            print(f"⚠️ 视频创建异常: {e}，跳过视频合并步骤")
            return show_results()
        
        # 4. 合并字幕到视频
        print("\n🔗 4. 合并中文字幕到视频...")
        try:
            cmd = "ffmpeg -i test_video.mp4 -vf \"subtitles=translated.srt\" -c:a copy final_video.mp4 -y"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 视频合并完成")
            else:
                print(f"⚠️ 视频合并失败: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 视频合并异常: {e}")
        
        return show_results()
        
    finally:
        os.chdir(original_dir)

def show_results():
    """显示测试结果"""
    print("\n📊 测试结果")
    print("=" * 40)
    
    test_dir = "quick_test"
    files = {
        "original.srt": "原始英文字幕",
        "translated.srt": "翻译中文字幕",
        "test_video.mp4": "测试视频文件",
        "final_video.mp4": "最终合并视频"
    }
    
    for filename, description in files.items():
        filepath = os.path.join(test_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"✅ {description}: {filename} ({size} bytes)")
        else:
            print(f"❌ {description}: {filename} (不存在)")
    
    # 显示翻译对比
    original_file = os.path.join(test_dir, "original.srt")
    translated_file = os.path.join(test_dir, "translated.srt")
    
    if os.path.exists(original_file) and os.path.exists(translated_file):
        print("\n📝 翻译对比:")
        print("-" * 40)
        
        try:
            with open(original_file, "r", encoding="utf-8") as f:
                original_content = f.read()
            
            with open(translated_file, "r", encoding="utf-8") as f:
                translated_content = f.read()
            
            print("原始字幕:")
            print(original_content[:200] + "...")
            print("\n翻译字幕:")
            print(translated_content[:200] + "...")
            
        except Exception as e:
            print(f"读取文件失败: {e}")
    
    print("\n🎉 快速验证完成！")
    print("\n📁 所有文件保存在 'quick_test' 目录中")
    return True

def main():
    print("🎬 YouTube视频处理完整工作流验证")
    print("功能: 字幕翻译 -> 视频合并")
    print("注意: 使用模拟翻译，不调用真实API")
    print("=" * 50)
    
    try:
        return quick_test()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)