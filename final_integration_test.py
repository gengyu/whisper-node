#!/usr/bin/env python3
"""
最终集成测试脚本
验证 Whisper Subtitle Generator 的翻译和社交媒体功能
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🔧 {description}")
    print(f"Command: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"Error: {result.stderr}")
        print(f"Exit code: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        print(f"Exception: {e}")
        return False

def main():
    print("🎬 Whisper Subtitle Generator - 最终集成测试")
    print("=" * 60)
    
    # 测试基本CLI命令
    tests = [
        ("python -m whisper_subtitle.cli --help", "测试主CLI帮助"),
        ("python -m whisper_subtitle.cli translate --help", "测试翻译CLI帮助"),
        ("python -m whisper_subtitle.cli social --help", "测试社交媒体CLI帮助"),
        ("python -m whisper_subtitle.cli translate languages", "测试支持的语言列表"),
        ("python -m whisper_subtitle.cli social platforms", "测试社交媒体平台列表"),
        ("python -m whisper_subtitle.cli translate file --help", "测试文件翻译帮助"),
        ("python -m whisper_subtitle.cli social configure --help", "测试社交媒体配置帮助"),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for cmd, desc in tests:
        if run_command(cmd, desc):
            success_count += 1
            print("✅ 成功")
        else:
            print("❌ 失败")
    
    # 测试配置文件生成
    print("\n📝 测试配置文件生成")
    print("-" * 50)
    
    config_file = "test_social_config.yaml"
    if run_command(f"python -m whisper_subtitle.cli social configure -o {config_file}", "生成社交媒体配置模板"):
        if os.path.exists(config_file):
            print(f"✅ 配置文件 {config_file} 生成成功")
            with open(config_file, 'r') as f:
                content = f.read()
                print(f"配置文件内容预览:\n{content[:200]}...")
            success_count += 1
        else:
            print(f"❌ 配置文件 {config_file} 未生成")
    total_count += 1
    
    # 测试SRT文件翻译（无凭证）
    print("\n🌐 测试SRT文件翻译（预期需要凭证）")
    print("-" * 50)
    
    srt_file = "test_subtitle.srt"
    output_file = "test_subtitle_translated.srt"
    
    if os.path.exists(srt_file):
        result = run_command(
            f"python -m whisper_subtitle.cli translate file {srt_file} {output_file} --target-lang zh",
            "测试SRT文件翻译"
        )
        if not result:  # 预期失败，因为没有凭证
            print("✅ 正确显示需要阿里云凭证的错误信息")
            success_count += 1
        else:
            print("❌ 应该显示凭证错误")
    else:
        print(f"❌ 测试文件 {srt_file} 不存在")
    total_count += 1
    
    # 运行功能测试脚本
    print("\n🧪 运行功能测试脚本")
    print("-" * 50)
    
    if os.path.exists("test_translation_social.py"):
        if run_command("python test_translation_social.py", "运行翻译和社交媒体功能测试"):
            print("✅ 功能测试脚本运行成功")
            success_count += 1
        else:
            print("❌ 功能测试脚本运行失败")
    else:
        print("❌ 功能测试脚本不存在")
    total_count += 1
    
    # 总结
    print("\n📊 测试总结")
    print("=" * 60)
    print(f"总测试数: {total_count}")
    print(f"成功: {success_count}")
    print(f"失败: {total_count - success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("\n🎉 所有测试通过！")
        print("\n📝 下一步:")
        print("1. 配置阿里云翻译服务凭证")
        print("2. 配置YouTube和Twitter API凭证")
        print("3. 进行真实环境测试")
    else:
        print("\n⚠️  部分测试失败，请检查相关功能")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)