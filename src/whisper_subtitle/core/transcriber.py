"""Core transcription service that manages different speech recognition engines."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..engines.base import BaseEngine, TranscriptionResult
from ..engines.openai_whisper import OpenAIWhisperEngine
from ..engines.faster_whisper import FasterWhisperEngine
from ..engines.whisperkit import WhisperKitEngine
from ..engines.whispercpp import WhisperCppEngine
from ..engines.alibaba_asr import AlibabaASREngine
from ..utils.audio import AudioProcessor
from ..config.settings import settings

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Main transcription service that coordinates different engines."""
    
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self._engines: Dict[str, BaseEngine] = {}
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize available speech recognition engines."""
        # OpenAI Whisper (always available)
        self._engines["openai_whisper"] = OpenAIWhisperEngine()
        
        # Faster Whisper (Windows/Linux)
        if not settings.is_macos or settings.debug:
            self._engines["faster_whisper"] = FasterWhisperEngine()
        
        # WhisperKit (macOS M-series only)
        if settings.is_macos and settings.is_apple_silicon:
            self._engines["whisperkit"] = WhisperKitEngine()
        
        # WhisperCpp (all platforms)
        self._engines["whispercpp"] = WhisperCppEngine()
        
        # Alibaba ASR (if configured)
        if all([
            settings.alibaba_access_key_id,
            settings.alibaba_access_key_secret,
            settings.alibaba_app_key
        ]):
            self._engines["alibaba_asr"] = AlibabaASREngine()
        
        logger.info(f"Initialized engines: {list(self._engines.keys())}")
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engine names."""
        return list(self._engines.keys())
    
    def get_engine(self, engine_name: str) -> Optional[BaseEngine]:
        """Get a specific engine by name."""
        return self._engines.get(engine_name)
    
    async def transcribe_audio(
        self,
        audio_path: Union[str, Path],
        engine_name: str = "openai_whisper",
        model_name: str = "medium",
        language: Optional[str] = None,
        output_format: str = "srt",
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio file using specified engine.
        
        Args:
            audio_path: Path to audio file
            engine_name: Name of the engine to use
            model_name: Model name/size to use
            language: Language code (auto-detect if None)
            output_format: Output format (srt, vtt, txt, json)
            **kwargs: Additional engine-specific parameters
        
        Returns:
            TranscriptionResult with transcription data
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        engine = self.get_engine(engine_name)
        if not engine:
            raise ValueError(f"Engine '{engine_name}' not available. Available engines: {self.get_available_engines()}")
        
        logger.info(f"Starting transcription with {engine_name} engine")
        logger.info(f"Audio file: {audio_path}")
        logger.info(f"Model: {model_name}, Language: {language}, Format: {output_format}")
        
        try:
            # Check if engine is ready
            if not await engine.is_ready():
                logger.info(f"Engine {engine_name} not ready, initializing...")
                await engine.initialize()
            
            # Perform transcription
            result = await engine.transcribe(
                audio_path=audio_path,
                model_name=model_name,
                language=language,
                output_format=output_format,
                **kwargs
            )
            
            logger.info(f"Transcription completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed with {engine_name}: {str(e)}")
            raise
    
    async def transcribe_video(
        self,
        video_path: Union[str, Path],
        engine_name: str = "openai_whisper",
        model_name: str = "medium",
        language: Optional[str] = None,
        output_format: str = "srt",
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe video file by extracting audio first.
        
        Args:
            video_path: Path to video file
            engine_name: Name of the engine to use
            model_name: Model name/size to use
            language: Language code (auto-detect if None)
            output_format: Output format (srt, vtt, txt, json)
            **kwargs: Additional engine-specific parameters
        
        Returns:
            TranscriptionResult with transcription data
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Extracting audio from video: {video_path}")
        
        try:
            # Extract audio from video
            audio_path = await self.audio_processor.extract_audio(video_path)
            
            # Transcribe the extracted audio
            result = await self.transcribe_audio(
                audio_path=audio_path,
                engine_name=engine_name,
                model_name=model_name,
                language=language,
                output_format=output_format,
                **kwargs
            )
            
            # Clean up temporary audio file
            if audio_path.exists():
                audio_path.unlink()
            
            return result
            
        except Exception as e:
            logger.error(f"Video transcription failed: {str(e)}")
            raise
    
    async def batch_transcribe(
        self,
        file_paths: List[Union[str, Path]],
        engine_name: str = "openai_whisper",
        model_name: str = "medium",
        language: Optional[str] = None,
        output_format: str = "srt",
        max_concurrent: int = 3,
        **kwargs
    ) -> List[TranscriptionResult]:
        """Transcribe multiple files concurrently.
        
        Args:
            file_paths: List of file paths to transcribe
            engine_name: Name of the engine to use
            model_name: Model name/size to use
            language: Language code (auto-detect if None)
            output_format: Output format (srt, vtt, txt, json)
            max_concurrent: Maximum number of concurrent transcriptions
            **kwargs: Additional engine-specific parameters
        
        Returns:
            List of TranscriptionResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def transcribe_single(file_path: Union[str, Path]) -> TranscriptionResult:
            async with semaphore:
                file_path = Path(file_path)
                
                # Determine if it's audio or video
                if file_path.suffix.lower() in ['.mp3', '.wav', '.flac', '.m4a', '.aac']:
                    return await self.transcribe_audio(
                        audio_path=file_path,
                        engine_name=engine_name,
                        model_name=model_name,
                        language=language,
                        output_format=output_format,
                        **kwargs
                    )
                else:
                    return await self.transcribe_video(
                        video_path=file_path,
                        engine_name=engine_name,
                        model_name=model_name,
                        language=language,
                        output_format=output_format,
                        **kwargs
                    )
        
        logger.info(f"Starting batch transcription of {len(file_paths)} files")
        
        tasks = [transcribe_single(file_path) for file_path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to transcribe {file_paths[i]}: {str(result)}")
                # Create error result
                error_result = TranscriptionResult(
                    text="",
                    segments=[],
                    language="unknown",
                    duration=0.0,
                    output_path=None,
                    engine=engine_name,
                    model=model_name,
                    error=str(result)
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        logger.info(f"Batch transcription completed")
        return final_results