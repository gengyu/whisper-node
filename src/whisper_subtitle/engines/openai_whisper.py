"""OpenAI Whisper engine implementation."""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional, Union

import whisper

from .base import BaseEngine, TranscriptionResult, TranscriptionSegment
from ..config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIWhisperEngine(BaseEngine):
    """OpenAI Whisper speech recognition engine."""
    
    def __init__(self):
        super().__init__("openai_whisper")
        self.model = None
        self.current_model_name = None
    
    async def initialize(self) -> None:
        """Initialize the OpenAI Whisper engine."""
        if self._initialized:
            return
        
        logger.info("Initializing OpenAI Whisper engine...")
        
        try:
            # Load default model
            await self._load_model(settings.openai_whisper_model)
            self._initialized = True
            logger.info("OpenAI Whisper engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI Whisper engine: {str(e)}")
            raise
    
    async def is_ready(self) -> bool:
        """Check if the engine is ready to use."""
        return self._initialized and self.model is not None
    
    async def _load_model(self, model_name: str) -> None:
        """Load a Whisper model."""
        if self.current_model_name == model_name and self.model is not None:
            return
        
        logger.info(f"Loading OpenAI Whisper model: {model_name}")
        
        # Run model loading in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(
            None, 
            lambda: whisper.load_model(model_name, download_root=str(settings.model_dir))
        )
        self.current_model_name = model_name
        
        logger.info(f"Model {model_name} loaded successfully")
    
    async def transcribe(
        self,
        audio_path: Union[str, Path],
        model_name: str = "medium",
        language: Optional[str] = None,
        output_format: str = "srt",
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio using OpenAI Whisper."""
        audio_path = Path(audio_path)
        start_time = time.time()
        
        if not await self.is_ready():
            await self.initialize()
        
        # Load model if different from current
        await self._load_model(model_name)
        
        logger.info(f"Transcribing {audio_path} with OpenAI Whisper ({model_name})")
        
        try:
            # Prepare transcription options
            transcribe_options = {
                "language": language,
                "task": "transcribe",
                "verbose": False,
                **kwargs
            }
            
            # Remove None values
            transcribe_options = {k: v for k, v in transcribe_options.items() if v is not None}
            
            # Run transcription in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(str(audio_path), **transcribe_options)
            )
            
            # Process result
            segments = []
            for segment in result.get("segments", []):
                segments.append(TranscriptionSegment(
                    start=segment["start"],
                    end=segment["end"],
                    text=segment["text"].strip(),
                    confidence=segment.get("avg_logprob")
                ))
            
            processing_time = time.time() - start_time
            
            transcription_result = TranscriptionResult(
                text=result["text"].strip(),
                segments=segments,
                language=result.get("language", language or "unknown"),
                duration=result.get("duration", 0.0),
                output_path=None,
                engine=self.name,
                model=model_name,
                processing_time=processing_time,
                metadata={
                    "whisper_version": whisper.__version__,
                    "model_size": model_name,
                }
            )
            
            # Save to file if requested
            if output_format != "none":
                output_dir = settings.output_dir
                output_filename = f"{audio_path.stem}_{self.name}_{model_name}.{output_format}"
                output_path = output_dir / output_filename
                transcription_result.save_to_file(output_path, output_format)
            
            logger.info(f"Transcription completed in {processing_time:.2f}s")
            return transcription_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"OpenAI Whisper transcription failed: {str(e)}"
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
        """Get list of available OpenAI Whisper models."""
        return [
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large",
            "large-v1",
            "large-v2",
            "large-v3"
        ]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        # OpenAI Whisper supports 99 languages
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
        if self.model is not None:
            # Clear model from memory
            del self.model
            self.model = None
            self.current_model_name = None
        
        self._initialized = False
        logger.info("OpenAI Whisper engine cleaned up")