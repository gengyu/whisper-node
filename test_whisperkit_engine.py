#!/usr/bin/env python3
"""测试脚本：验证WhisperKitEngine的所有方法功能"""

import asyncio
import logging
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from whisper_subtitle.engines.whisperkit import WhisperKitEngine
from whisper_subtitle.engines.base import TranscriptionResult, TranscriptionSegment
from whisper_subtitle.config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WhisperKitEngineTest:
    """WhisperKitEngine测试类"""
    
    def __init__(self):
        self.engine = None
        self.test_results = []
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} - {test_name}"
        if message:
            result += f": {message}"
        
        self.test_results.append((test_name, success, message))
        logger.info(result)
        
    async def test_engine_initialization(self):
        """测试引擎初始化"""
        try:
            self.engine = WhisperKitEngine()
            
            # 验证基本属性
            assert self.engine.name == "whisperkit"
            assert hasattr(self.engine, 'cli_path')
            assert hasattr(self.engine, 'model_path')
            assert not self.engine._initialized
            
            self.log_test_result("Engine Initialization", True, "引擎对象创建成功")
            
        except Exception as e:
            self.log_test_result("Engine Initialization", False, str(e))
            
    async def test_is_ready_before_init(self):
        """测试初始化前的就绪状态"""
        try:
            is_ready = await self.engine.is_ready()
            
            # 在初始化前应该返回False
            assert not is_ready
            
            self.log_test_result("Is Ready (Before Init)", True, "初始化前正确返回False")
            
        except Exception as e:
            self.log_test_result("Is Ready (Before Init)", False, str(e))
            
    async def test_get_available_models(self):
        """测试获取可用模型列表"""
        try:
            models = self.engine.get_available_models()
            
            # 验证返回的是列表且包含预期模型
            assert isinstance(models, list)
            assert len(models) > 0
            assert "large-v2" in models
            assert "large-v3" in models
            
            self.log_test_result("Get Available Models", True, f"找到{len(models)}个模型: {models}")
            
        except Exception as e:
            self.log_test_result("Get Available Models", False, str(e))
            
    async def test_get_supported_languages(self):
        """测试获取支持的语言列表"""
        try:
            languages = self.engine.get_supported_languages()
            
            # 验证返回的是列表且包含常见语言
            assert isinstance(languages, list)
            assert len(languages) > 0
            assert "en" in languages  # 英语
            assert "zh" in languages  # 中文
            assert "ja" in languages  # 日语
            assert "fr" in languages  # 法语
            
            self.log_test_result("Get Supported Languages", True, f"支持{len(languages)}种语言")
            
        except Exception as e:
            self.log_test_result("Get Supported Languages", False, str(e))
            
    async def test_initialization_mock(self):
        """测试引擎初始化（模拟环境）"""
        try:
            # 模拟macOS和Apple Silicon环境
            with patch.object(settings, 'is_macos', True), \
                 patch.object(settings, 'is_apple_silicon', True), \
                 patch.object(self.engine.cli_path, 'exists', return_value=True), \
                 patch.object(self.engine.model_path, 'exists', return_value=True), \
                 patch.object(self.engine, '_test_cli', new_callable=AsyncMock):
                
                await self.engine.initialize()
                
                # 验证初始化状态
                assert self.engine._initialized
                
                self.log_test_result("Engine Initialize (Mock)", True, "模拟环境下初始化成功")
                
        except Exception as e:
            self.log_test_result("Engine Initialize (Mock)", False, str(e))
            
    async def test_is_ready_after_init(self):
        """测试初始化后的就绪状态"""
        try:
            # 模拟所有条件满足
            with patch.object(settings, 'is_macos', True), \
                 patch.object(settings, 'is_apple_silicon', True), \
                 patch.object(self.engine.cli_path, 'exists', return_value=True), \
                 patch.object(self.engine.model_path, 'exists', return_value=True):
                
                is_ready = await self.engine.is_ready()
                
                # 初始化后且条件满足应该返回True
                assert is_ready
                
                self.log_test_result("Is Ready (After Init)", True, "初始化后正确返回True")
                
        except Exception as e:
            self.log_test_result("Is Ready (After Init)", False, str(e))
            
    async def test_transcribe_mock(self):
        """测试转录功能（模拟）"""
        try:
            # 创建测试音频文件路径
            test_audio = self.temp_dir / "test_audio.wav"
            test_audio.touch()  # 创建空文件
            
            # 模拟转录结果
            mock_json_data = {
                "text": "Hello, this is a test transcription.",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 2.5,
                        "text": "Hello, this is a test",
                        "confidence": 0.95
                    },
                    {
                        "start": 2.5,
                        "end": 4.0,
                        "text": "transcription.",
                        "confidence": 0.92
                    }
                ],
                "language": "en",
                "duration": 4.0,
                "version": "1.0.0"
            }
            
            # 模拟JSON文件
            mock_json_file = self.temp_dir / "test_audio.json"
            import json
            with open(mock_json_file, 'w') as f:
                json.dump(mock_json_data, f)
            
            # 模拟各种依赖
            with patch.object(self.engine, 'is_ready', return_value=True), \
                 patch('asyncio.create_subprocess_exec') as mock_subprocess, \
                 patch.object(Path, 'glob', return_value=[mock_json_file]):
                
                # 模拟subprocess成功执行
                mock_process = Mock()
                mock_process.communicate = AsyncMock(return_value=(b'success', b''))
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                # 执行转录
                result = await self.engine.transcribe(
                    audio_path=test_audio,
                    model_name="large-v2",
                    language="en",
                    output_format="srt"
                )
                
                # 验证结果
                assert isinstance(result, TranscriptionResult)
                assert result.text == "Hello, this is a test transcription."
                assert len(result.segments) == 2
                assert result.language == "en"
                assert result.engine == "whisperkit"
                assert result.model == "large-v2"
                assert result.is_successful
                
                self.log_test_result("Transcribe (Mock)", True, f"转录成功，文本长度: {len(result.text)}")
                
        except Exception as e:
            self.log_test_result("Transcribe (Mock)", False, str(e))
            
    async def test_transcribe_error_handling(self):
        """测试转录错误处理"""
        try:
            test_audio = self.temp_dir / "nonexistent.wav"
            
            # 模拟subprocess失败
            with patch.object(self.engine, 'is_ready', return_value=True), \
                 patch('asyncio.create_subprocess_exec') as mock_subprocess:
                
                mock_process = Mock()
                mock_process.communicate = AsyncMock(return_value=(b'', b'Error: file not found'))
                mock_process.returncode = 1
                mock_subprocess.return_value = mock_process
                
                result = await self.engine.transcribe(test_audio)
                
                # 验证错误处理
                assert isinstance(result, TranscriptionResult)
                assert not result.is_successful
                assert result.error is not None
                assert "WhisperKit transcription failed" in result.error
                
                self.log_test_result("Transcribe Error Handling", True, "错误处理正确")
                
        except Exception as e:
            self.log_test_result("Transcribe Error Handling", False, str(e))
            
    async def test_cleanup(self):
        """测试清理功能"""
        try:
            await self.engine.cleanup()
            
            # 验证清理后状态
            assert not self.engine._initialized
            
            self.log_test_result("Cleanup", True, "清理功能正常")
            
        except Exception as e:
            self.log_test_result("Cleanup", False, str(e))
            
    async def test_platform_requirements(self):
        """测试平台要求检查"""
        try:
            # 测试非macOS环境
            with patch.object(settings, 'is_macos', False):
                engine = WhisperKitEngine()
                try:
                    await engine.initialize()
                    assert False, "应该抛出RuntimeError"
                except RuntimeError as e:
                    assert "only available on macOS" in str(e)
            
            # 测试非Apple Silicon环境
            with patch.object(settings, 'is_macos', True), \
                 patch.object(settings, 'is_apple_silicon', False):
                engine = WhisperKitEngine()
                try:
                    await engine.initialize()
                    assert False, "应该抛出RuntimeError"
                except RuntimeError as e:
                    assert "requires Apple Silicon" in str(e)
            
            self.log_test_result("Platform Requirements", True, "平台要求检查正确")
            
        except Exception as e:
            self.log_test_result("Platform Requirements", False, str(e))
            
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info(f"清理临时目录: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
            
    def print_summary(self):
        """打印测试总结"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, success, _ in self.test_results if success)
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("WhisperKitEngine 测试总结")
        print("="*60)
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print("\n失败的测试:")
            for name, success, message in self.test_results:
                if not success:
                    print(f"  ❌ {name}: {message}")
        
        print("="*60)
        
        return failed_tests == 0


async def main():
    """主测试函数"""
    print("开始测试 WhisperKitEngine...")
    
    tester = WhisperKitEngineTest()
    
    try:
        # 执行所有测试
        await tester.test_engine_initialization()
        await tester.test_is_ready_before_init()
        await tester.test_get_available_models()
        await tester.test_get_supported_languages()
        await tester.test_initialization_mock()
        await tester.test_is_ready_after_init()
        await tester.test_transcribe_mock()
        await tester.test_transcribe_error_handling()
        await tester.test_cleanup()
        await tester.test_platform_requirements()
        
    finally:
        # 清理资源
        tester.cleanup_temp_files()
    
    # 打印总结
    success = tester.print_summary()
    
    if success:
        print("\n🎉 所有测试通过！WhisperKitEngine 功能正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)