"""WhisperKit engine implementation for macOS."""

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


class WhisperKitEngine(BaseEngine):
    """WhisperKit speech recognition engine for macOS."""
    
    def __init__(self):
        super().__init__("whisperkit")
        self.cli_path = settings.whisperkit_cli_path
        self.model_path = settings.whisperkit_model_path
    
    async def initialize(self) -> None:
        """Initialize the WhisperKit engine."""
        if self._initialized:
            return
        
        if not settings.is_macos:
            raise RuntimeError("WhisperKit is only available on macOS")
        
        if not settings.is_apple_silicon:
            raise RuntimeError("WhisperKit requires Apple Silicon (M1/M2) chips")
        
        logger.info("Initializing WhisperKit engine...")
        
        try:
            # Check if CLI exists
            if not self.cli_path.exists():
                await self._download_whisperkit_cli()
            
            # Check if model exists
            if not self.model_path.exists():
                await self._download_model("large-v2")
            
            # Test CLI
            await self._test_cli()
            
            self._initialized = True
            logger.info("WhisperKit engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WhisperKit engine: {str(e)}")
            raise
    
    async def is_ready(self) -> bool:
        """Check if the engine is ready to use."""
        return (
            settings.is_macos and
            settings.is_apple_silicon and
            self._initialized and
            self.cli_path.exists() and
            self.model_path.exists()
        )
    
    async def _download_whisperkit_cli(self) -> None:
        """Download WhisperKit CLI."""
        logger.info("Downloading WhisperKit CLI...")
        
        # Create directory
        self.cli_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download URL (this would need to be updated with actual URL)
        download_url = "https://github.com/argmaxinc/WhisperKit/releases/latest/download/whisperkit-cli"
        
        try:
            import requests
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(self.cli_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Make executable
            self.cli_path.chmod(0o755)
            
            logger.info("WhisperKit CLI downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to download WhisperKit CLI: {str(e)}")
            raise
    
    async def _download_model(self, model_name: str) -> None:
        """Download WhisperKit model."""
        logger.info(f"Downloading WhisperKit model: {model_name}")
        
        # Create directory
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use CLI to download model
        cmd = [
            str(self.cli_path),
            "download",
            "--model", model_name,
            "--output-dir", str(self.model_path.parent)
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Model download failed: {stderr.decode()}")
            
            logger.info(f"Model {model_name} downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to download model {model_name}: {str(e)}")
            raise
    
    async def _test_cli(self) -> None:
        """Test WhisperKit CLI."""
        cmd = [str(self.cli_path), "--version"]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"CLI test failed: {stderr.decode()}")
            
            logger.info(f"WhisperKit CLI version: {stdout.decode().strip()}")
        except Exception as e:
            logger.error(f"CLI test failed: {str(e)}")
            raise
    
    async def transcribe(
        self,
        audio_path: Union[str, Path],
        model_name: str = "large-v2",
        language: Optional[str] = None,
        output_format: str = "srt",
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio using WhisperKit."""
        audio_path = Path(audio_path)
        start_time = time.time()
        
        if not await self.is_ready():
            await self.initialize()
        
        logger.info(f"Transcribing {audio_path} with WhisperKit ({model_name})")
        
        try:
            # Prepare output directory
            output_dir = settings.temp_dir / "whisperkit"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Build command
            cmd = [
                str(self.cli_path),
                "transcribe",
                "--audio-path", str(audio_path),
                "--model-path", str(self.model_path),
                "--output-dir", str(output_dir),
                "--output-format", "json"  # Always use JSON for parsing
            ]
            
            if language:
                cmd.extend(["--language", language])
            
            # Add additional options
            if kwargs.get("verbose"):
                cmd.append("--verbose")
            
            # Run transcription
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"WhisperKit transcription failed: {stderr.decode()}")
            
            # Find output JSON file
            json_files = list(output_dir.glob(f"{audio_path.stem}*.json"))
            if not json_files:
                raise RuntimeError("No output JSON file found")
            
            json_file = json_files[0]
            
            # Parse JSON result
            with open(json_file, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            
            # Process segments
            segments = []
            full_text = []
            
            for segment_data in result_data.get("segments", []):
                segment = TranscriptionSegment(
                    start=segment_data.get("start", 0.0),
                    end=segment_data.get("end", 0.0),
                    text=segment_data.get("text", "").strip(),
                    confidence=segment_data.get("confidence")
                )
                segments.append(segment)
                full_text.append(segment.text)
            
            processing_time = time.time() - start_time
            
            transcription_result = TranscriptionResult(
                text=" ".join(full_text) or result_data.get("text", ""),
                segments=segments,
                language=result_data.get("language", language or "unknown"),
                duration=result_data.get("duration", 0.0),
                output_path=None,
                engine=self.name,
                model=model_name,
                processing_time=processing_time,
                metadata={
                    "whisperkit_version": result_data.get("version"),
                    "model_path": str(self.model_path),
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
            error_msg = f"WhisperKit transcription failed: {str(e)}"
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
        """Get list of available WhisperKit models."""
        return [
            "large-v2",
            "large-v3"
        ]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        # WhisperKit supports the same languages as OpenAI Whisper
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
        logger.info("WhisperKit engine cleaned up")