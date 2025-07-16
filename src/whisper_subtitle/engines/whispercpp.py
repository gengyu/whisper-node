"""WhisperCpp engine implementation."""

import asyncio
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Union

from .base import BaseEngine, TranscriptionResult, TranscriptionSegment
from ..config.settings import settings

logger = logging.getLogger(__name__)


class WhisperCppEngine(BaseEngine):
    """WhisperCpp speech recognition engine."""
    
    def __init__(self):
        super().__init__("whispercpp")
        self.executable_path = None
        self.model_path = settings.whispercpp_model_path
    
    async def initialize(self) -> None:
        """Initialize the WhisperCpp engine."""
        if self._initialized:
            return
        
        logger.info("Initializing WhisperCpp engine...")
        
        try:
            # Find or download whisper.cpp executable
            await self._setup_executable()
            
            # Check if model exists
            if not self.model_path.exists():
                await self._download_model("large-v2")
            
            # Test executable
            await self._test_executable()
            
            self._initialized = True
            logger.info("WhisperCpp engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WhisperCpp engine: {str(e)}")
            raise
    
    async def is_ready(self) -> bool:
        """Check if the engine is ready to use."""
        return (
            self._initialized and
            self.executable_path and
            Path(self.executable_path).exists() and
            self.model_path.exists()
        )
    
    async def _setup_executable(self) -> None:
        """Setup WhisperCpp executable."""
        # Try to find existing executable
        possible_names = ["whisper", "whisper.cpp", "main"]
        possible_paths = [
            Path.cwd() / "bin",
            Path.cwd() / "whisper.cpp",
            Path("/usr/local/bin"),
            Path("/opt/homebrew/bin"),
        ]
        
        for path in possible_paths:
            for name in possible_names:
                executable = path / name
                if executable.exists() and executable.is_file():
                    self.executable_path = str(executable)
                    logger.info(f"Found WhisperCpp executable: {executable}")
                    return
        
        # If not found, try to build from source
        await self._build_whispercpp()
    
    async def _build_whispercpp(self) -> None:
        """Build WhisperCpp from source."""
        logger.info("Building WhisperCpp from source...")
        
        build_dir = settings.temp_dir / "whisper.cpp"
        build_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Clone repository
            clone_cmd = [
                "git", "clone", "https://github.com/ggerganov/whisper.cpp.git", str(build_dir)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Git clone failed: {stderr.decode()}")
            
            # Build
            build_cmd = ["make", "-j"]
            
            process = await asyncio.create_subprocess_exec(
                *build_cmd,
                cwd=build_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Build failed: {stderr.decode()}")
            
            # Copy executable to bin directory
            bin_dir = Path.cwd() / "bin"
            bin_dir.mkdir(exist_ok=True)
            
            source_executable = build_dir / "main"
            target_executable = bin_dir / "whisper-cpp"
            
            import shutil
            shutil.copy2(source_executable, target_executable)
            target_executable.chmod(0o755)
            
            self.executable_path = str(target_executable)
            
            logger.info(f"WhisperCpp built successfully: {target_executable}")
            
        except Exception as e:
            logger.error(f"Failed to build WhisperCpp: {str(e)}")
            raise
    
    async def _download_model(self, model_name: str) -> None:
        """Download WhisperCpp model."""
        logger.info(f"Downloading WhisperCpp model: {model_name}")
        
        # Create directory
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Model download URLs
        model_urls = {
            "tiny": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
            "base": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
            "small": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
            "medium": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
            "large-v1": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v1.bin",
            "large-v2": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v2.bin",
            "large-v3": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin",
        }
        
        if model_name not in model_urls:
            raise ValueError(f"Unknown model: {model_name}")
        
        try:
            import requests
            response = requests.get(model_urls[model_name], stream=True)
            response.raise_for_status()
            
            with open(self.model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Model {model_name} downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to download model {model_name}: {str(e)}")
            raise
    
    async def _test_executable(self) -> None:
        """Test WhisperCpp executable."""
        cmd = [self.executable_path, "--help"]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Executable test failed: {stderr.decode()}")
            
            logger.info("WhisperCpp executable test passed")
        except Exception as e:
            logger.error(f"Executable test failed: {str(e)}")
            raise
    
    async def transcribe(
        self,
        audio_path: Union[str, Path],
        model_name: str = "large-v2",
        language: Optional[str] = None,
        output_format: str = "srt",
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio using WhisperCpp."""
        audio_path = Path(audio_path)
        start_time = time.time()
        
        if not await self.is_ready():
            await self.initialize()
        
        logger.info(f"Transcribing {audio_path} with WhisperCpp ({model_name})")
        
        try:
            # Prepare output directory
            output_dir = settings.temp_dir / "whispercpp"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Build command
            cmd = [
                self.executable_path,
                "-m", str(self.model_path),
                "-f", str(audio_path),
                "--output-json",
                "--output-file", str(output_dir / audio_path.stem)
            ]
            
            if language:
                cmd.extend(["-l", language])
            
            # Add additional options
            if kwargs.get("threads"):
                cmd.extend(["-t", str(kwargs["threads"])])
            
            if kwargs.get("processors"):
                cmd.extend(["-p", str(kwargs["processors"])])
            
            # Run transcription
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"WhisperCpp transcription failed: {stderr.decode()}")
            
            # Find output JSON file
            json_file = output_dir / f"{audio_path.stem}.json"
            if not json_file.exists():
                raise RuntimeError("No output JSON file found")
            
            # Parse JSON result
            with open(json_file, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            
            # Process segments
            segments = []
            full_text = []
            
            for segment_data in result_data.get("transcription", []):
                # WhisperCpp JSON format may vary
                timestamps = segment_data.get("timestamps", {})
                segment = TranscriptionSegment(
                    start=timestamps.get("from", 0.0) / 100.0,  # Convert from centiseconds
                    end=timestamps.get("to", 0.0) / 100.0,
                    text=segment_data.get("text", "").strip()
                )
                segments.append(segment)
                full_text.append(segment.text)
            
            processing_time = time.time() - start_time
            
            transcription_result = TranscriptionResult(
                text=" ".join(full_text),
                segments=segments,
                language=language or "unknown",
                duration=result_data.get("duration", 0.0),
                output_path=None,
                engine=self.name,
                model=model_name,
                processing_time=processing_time,
                metadata={
                    "model_path": str(self.model_path),
                    "executable_path": self.executable_path,
                }
            )
            
            # Save to file if requested
            if output_format != "none":
                output_dir = settings.output_dir
                output_filename = f"{audio_path.stem}_{self.name}_{model_name}.{output_format}"
                output_path = output_dir / output_filename
                transcription_result.save_to_file(output_path, output_format)
            
            # Clean up temporary JSON file
            json_file.unlink(missing_ok=True)
            
            logger.info(f"Transcription completed in {processing_time:.2f}s")
            return transcription_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"WhisperCpp transcription failed: {str(e)}"
            logger.error(error_msg)
            
            return TranscriptionResult(
                text="",
                segments=[],
                language="unknown",
                duration=0.0,
                output_path=None,
                engine=self.name,
                model=model_name,
                processing_time=processing_time,
                error=error_msg
            )
    
    def get_available_models(self) -> List[str]:
        """Get list of available WhisperCpp models."""
        return [
            "tiny",
            "base",
            "small",
            "medium",
            "large-v1",
            "large-v2",
            "large-v3"
        ]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        # WhisperCpp supports the same languages as OpenAI Whisper
        return [
            "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca",
            "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo",
            "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id",
            "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln",
            "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my",
            "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa",
            "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta",
            "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi",
            "yo", "zh"
        ]
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False
        logger.info("WhisperCpp engine cleaned up")