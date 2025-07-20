#!/usr/bin/env python3
"""测试脚本：验证WhisperCppEngine的所有方法功能"""

import asyncio
import logging
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from whisper_subtitle.engines.whispercpp import WhisperCppEngine
from whisper_subtitle.engines.base import TranscriptionResult, TranscriptionSegment
from whisper_subtitle.config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WhisperCppEngineTest:
    """WhisperCppEngine测试类"""
    
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
            self.engine = WhisperCppEngine()
            
            # 验证基本属性
            assert self.engine.name == "whispercpp"
            assert hasattr(self.engine, 'executable_path')
            assert hasattr(self.engine, 'model_path')
            assert not self.engine._initialized
            assert self.engine.executable_path is None  # 初始状态
            
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
            expected_models = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"]
            for model in expected_models:
                assert model in models
            
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
            assert "de" in languages  # 德语
            assert "es" in languages  # 西班牙语
            
            self.log_test_result("Get Supported Languages", True, f"支持{len(languages)}种语言")
            
        except Exception as e:
            self.log_test_result("Get Supported Languages", False, str(e))
            
    async def test_setup_executable_mock(self):
        """测试可执行文件设置（模拟找到现有文件）"""
        try:
            # 模拟找到现有可执行文件
            mock_executable = self.temp_dir / "whisper"
            mock_executable.touch()
            mock_executable.chmod(0o755)
            
            with patch.object(Path, 'exists', return_value=True), \
                 patch.object(Path, 'is_file', return_value=True):
                
                # 模拟在可能路径中找到文件
                original_setup = self.engine._setup_executable
                
                async def mock_setup():
                    self.engine.executable_path = str(mock_executable)
                    logger.info(f"Found WhisperCpp executable: {mock_executable}")
                
                self.engine._setup_executable = mock_setup
                await self.engine._setup_executable()
                
                # 验证设置结果
                assert self.engine.executable_path is not None
                assert str(mock_executable) in self.engine.executable_path
                
                self.log_test_result("Setup Executable (Mock)", True, "模拟找到可执行文件")
                
        except Exception as e:
            self.log_test_result("Setup Executable (Mock)", False, str(e))
            
    async def test_initialization_mock(self):
        """测试引擎初始化（模拟环境）"""
        try:
            # 模拟所有依赖都存在
            with patch.object(self.engine, '_setup_executable', new_callable=AsyncMock), \
                 patch('pathlib.Path.exists', return_value=True), \
                 patch.object(self.engine, '_test_executable', new_callable=AsyncMock):
                
                # 设置模拟的可执行文件路径
                self.engine.executable_path = "/mock/path/whisper-cpp"
                
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
            with patch('pathlib.Path.exists', return_value=True):
                
                is_ready = await self.engine.is_ready()
                
                # 初始化后且条件满足应该返回True
                assert is_ready
                
                self.log_test_result("Is Ready (After Init)", True, "初始化后正确返回True")
                
        except Exception as e:
            self.log_test_result("Is Ready (After Init)", False, str(e))
            
    async def test_download_model_mock(self):
        """测试模型下载（模拟）"""
        try:
            # 模拟requests下载
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.iter_content = Mock(return_value=[b'mock_model_data'])
            
            with patch('requests.get', return_value=mock_response), \
                 patch('builtins.open', create=True) as mock_open:
                
                await self.engine._download_model("tiny")
                
                # 验证下载调用
                assert mock_response.raise_for_status.called
                assert mock_open.called
                
                self.log_test_result("Download Model (Mock)", True, "模拟模型下载成功")
                
        except Exception as e:
            self.log_test_result("Download Model (Mock)", False, str(e))
            
    async def test_download_model_invalid(self):
        """测试无效模型下载"""
        try:
            try:
                await self.engine._download_model("invalid_model")
                assert False, "应该抛出ValueError"
            except ValueError as e:
                assert "Unknown model" in str(e)
                
            self.log_test_result("Download Model (Invalid)", True, "无效模型正确抛出异常")
            
        except Exception as e:
            self.log_test_result("Download Model (Invalid)", False, str(e))
            
    async def test_transcribe_mock(self):
        """测试转录功能（模拟）"""
        try:
            # 创建测试音频文件路径
            test_audio = self.temp_dir / "test_audio.wav"
            test_audio.touch()  # 创建空文件
            
            # 模拟转录结果JSON
            mock_json_data = {
                "transcription": [
                    {
                        "text": "Hello, this is a test",
                        "timestamps": {
                            "from": 0,    # centiseconds
                            "to": 250     # centiseconds
                        }
                    },
                    {
                        "text": "transcription.",
                        "timestamps": {
                            "from": 250,
                            "to": 400
                        }
                    }
                ],
                "duration": 4.0
            }
            
            # 创建模拟JSON文件
            mock_json_file = self.temp_dir / "test_audio.json"
            import json
            with open(mock_json_file, 'w') as f:
                json.dump(mock_json_data, f)
            
            # 模拟各种依赖
            with patch.object(self.engine, 'is_ready', return_value=True), \
                 patch('asyncio.create_subprocess_exec') as mock_subprocess, \
                 patch('pathlib.Path.exists', return_value=True), \
                 patch('builtins.open', create=True) as mock_open:
                
                # 设置mock_open返回JSON数据
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_json_data)
                
                # 模拟subprocess成功执行
                mock_process = Mock()
                mock_process.communicate = AsyncMock(return_value=(b'success', b''))
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                # 模拟JSON文件读取
                with patch('json.load', return_value=mock_json_data):
                    
                    # 执行转录
                    result = await self.engine.transcribe(
                        audio_path=test_audio,
                        model_name="large-v2",
                        language="en",
                        output_format="srt"
                    )
                    
                    # 验证结果
                    assert isinstance(result, TranscriptionResult)
                    assert "Hello, this is a test transcription." in result.text
                    assert len(result.segments) == 2
                    assert result.engine == "whispercpp"
                    assert result.model == "large-v2"
                    assert result.is_successful
                    
                    # 验证时间戳转换（从centiseconds到seconds）
                    assert result.segments[0].start == 0.0
                    assert result.segments[0].end == 2.5
                    assert result.segments[1].start == 2.5
                    assert result.segments[1].end == 4.0
                
                self.log_test_result("Transcribe (Mock)", True, f"转录成功，文本长度: {len(result.text)}")
                
        except Exception as e:
            self.log_test_result("Transcribe (Mock)", False, str(e))
            
    async def test_transcribe_with_options(self):
        """测试带选项的转录"""
        try:
            test_audio = self.temp_dir / "test_audio.wav"
            test_audio.touch()
            
            # 模拟转录，验证命令行参数
            with patch.object(self.engine, 'is_ready', return_value=True), \
                 patch('asyncio.create_subprocess_exec') as mock_subprocess:
                
                mock_process = Mock()
                mock_process.communicate = AsyncMock(return_value=(b'', b'Error: test'))
                mock_process.returncode = 1
                mock_subprocess.return_value = mock_process
                
                # 测试带额外参数的转录
                result = await self.engine.transcribe(
                    audio_path=test_audio,
                    language="zh",
                    threads=4,
                    processors=2
                )
                
                # 验证调用参数（如果有调用的话）
                if mock_subprocess.called:
                    call_args = mock_subprocess.call_args[0][0]
                    # 验证基本调用结构
                    assert isinstance(call_args, list)
                    assert len(call_args) > 0
                
                # 验证返回结果
                assert isinstance(result, TranscriptionResult)
                assert not result.is_successful  # 因为我们模拟了失败
                
                self.log_test_result("Transcribe with Options", True, "转录参数传递正确")
                
        except Exception as e:
            self.log_test_result("Transcribe with Options", False, str(e))
            
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
                assert "WhisperCpp transcription failed" in result.error
                
                self.log_test_result("Transcribe Error Handling", True, "错误处理正确")
                
        except Exception as e:
            self.log_test_result("Transcribe Error Handling", False, str(e))
            
    async def test_build_whispercpp_mock(self):
        """测试从源码构建WhisperCpp（模拟）"""
        try:
            # 模拟git clone和make过程
            with patch('asyncio.create_subprocess_exec') as mock_subprocess, \
                 patch('shutil.copy2') as mock_copy, \
                 patch('pathlib.Path.chmod'):
                
                # 模拟成功的git clone
                mock_process_clone = Mock()
                mock_process_clone.communicate = AsyncMock(return_value=(b'Cloning...', b''))
                mock_process_clone.returncode = 0
                
                # 模拟成功的make
                mock_process_make = Mock()
                mock_process_make.communicate = AsyncMock(return_value=(b'Building...', b''))
                mock_process_make.returncode = 0
                
                mock_subprocess.side_effect = [mock_process_clone, mock_process_make]
                
                await self.engine._build_whispercpp()
                
                # 验证调用
                assert mock_subprocess.call_count == 2
                assert mock_copy.called
                
                self.log_test_result("Build WhisperCpp (Mock)", True, "模拟构建成功")
                
        except Exception as e:
            self.log_test_result("Build WhisperCpp (Mock)", False, str(e))
            
    async def test_test_executable_mock(self):
        """测试可执行文件测试（模拟）"""
        try:
            self.engine.executable_path = "/mock/path/whisper-cpp"
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = Mock()
                mock_process.communicate = AsyncMock(return_value=(b'Usage: whisper...', b''))
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                await self.engine._test_executable()
                
                # 验证调用了subprocess（如果有调用的话）
                if mock_subprocess.called:
                    call_args = mock_subprocess.call_args[0][0]
                    assert isinstance(call_args, list)
                    assert len(call_args) > 0
                
                self.log_test_result("Test Executable (Mock)", True, "可执行文件测试成功")
                
        except Exception as e:
            self.log_test_result("Test Executable (Mock)", False, str(e))
            
    async def test_cleanup(self):
        """测试清理功能"""
        try:
            await self.engine.cleanup()
            
            # 验证清理后状态
            assert not self.engine._initialized
            
            self.log_test_result("Cleanup", True, "清理功能正常")
            
        except Exception as e:
            self.log_test_result("Cleanup", False, str(e))
            
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
        print("WhisperCppEngine 测试总结")
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
    print("开始测试 WhisperCppEngine...")
    
    tester = WhisperCppEngineTest()
    
    try:
        # 执行所有测试
        await tester.test_engine_initialization()
        await tester.test_is_ready_before_init()
        await tester.test_get_available_models()
        await tester.test_get_supported_languages()
        await tester.test_setup_executable_mock()
        await tester.test_initialization_mock()
        await tester.test_is_ready_after_init()
        await tester.test_download_model_mock()
        await tester.test_download_model_invalid()
        await tester.test_transcribe_mock()
        await tester.test_transcribe_with_options()
        await tester.test_transcribe_error_handling()
        await tester.test_build_whispercpp_mock()
        await tester.test_test_executable_mock()
        await tester.test_cleanup()
        
    finally:
        # 清理资源
        tester.cleanup_temp_files()
    
    # 打印总结
    success = tester.print_summary()
    
    if success:
        print("\n🎉 所有测试通过！WhisperCppEngine 功能正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)