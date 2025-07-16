"""Faster Whisper engine implementation."""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional, Union

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None

from .base import BaseEngine, TranscriptionResult, TranscriptionSegment
from ..config.settings import settings

logger = logging.getLogger(__name__)


class FasterWhisperEngine(BaseEngine):
    """Faster Whisper speech recognition engine."""
    
    def __init__(self):
        super().__init__("faster_whisper")
        self.model = None
        self.current_model_name = None
        self.device = settings.faster_whisper_device
    
    async def initialize(self) -> None:
        """Initialize the Faster Whisper engine."""
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError("faster-whisper package is not installed")
        
        if self._initialized:
            return
        
        logger.info("Initializing Faster Whisper engine...")
        
        try:
            # Load default model
            await self._load_model(settings.faster_whisper_model_size)
            self._initialized = True
            logger.info("Faster Whisper engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Faster Whisper engine: {str(e)}")
            raise
    
    async def is_ready(self) -> bool:
        """Check if the engine is ready to use."""
        return (
            FASTER_WHISPER_AVAILABLE and 
            self._initialized and 
            self.model is not None
        )
    
    async def _load_model(self, model_name: str) -> None:
        """Load a Faster Whisper model."""
        if self.current_model_name == model_name and self.model is not None:
            return
        
        logger.info(f"Loading Faster Whisper model: {model_name}")
        
        # Determine device
        device = self.device
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        
        # Run model loading in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(
            None,
            lambda: WhisperModel(
                model_name,
                device=device,
                download_root=str(settings.model_dir / "faster_whisper")
            )
        )
        self.current_model_name = model_name
        
        logger.info(f"Model {model_name} loaded successfully on {device}")
    
    async def transcribe(
        self,
        audio_path: Union[str, Path],
        model_name: str = "medium",
        language: Optional[str] = None,
        output_format: str = "srt",
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio using Faster Whisper."""
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError("faster-whisper package is not installed")
        
        audio_path = Path(audio_path)
        start_time = time.time()
        
        if not await self.is_ready():
            await self.initialize()
        
        # Load model if different from current
        await self._load_model(model_name)
        
        logger.info(f"Transcribing {audio_path} with Faster Whisper ({model_name})")
        
        try:
            # Prepare transcription options
            transcribe_options = {
                "language": language,
                "task": "transcribe",
                "beam_size": kwargs.get("beam_size", 5),
                "best_of": kwargs.get("best_of", 5),
                "temperature": kwargs.get("temperature", 0.0),
                "condition_on_previous_text": kwargs.get("condition_on_previous_text", True),
                "initial_prompt": kwargs.get("initial_prompt"),
                "word_timestamps": kwargs.get("word_timestamps", False),
                "vad_filter": kwargs.get("vad_filter", True),
                "vad_parameters": kwargs.get("vad_parameters"),
            }
            
            # Remove None values
            transcribe_options = {k: v for k, v in transcribe_options.items() if v is not None}
            
            # Run transcription in thread pool
            loop = asyncio.get_event_loop()
            segments_generator, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(str(audio_path), **transcribe_options)
            )
            
            # Convert generator to list in thread pool
            segments_list = await loop.run_in_executor(
                None,
                lambda: list(segments_generator)
            )
            
            # Process segments
            segments = []
            full_text = []
            
            for segment in segments_list:
                segments.append(TranscriptionSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    confidence=getattr(segment, 'avg_logprob', None)
                ))
                full_text.append(segment.text.strip())
            
            processing_time = time.time() - start_time
            
            transcription_result = TranscriptionResult(
                text=" ".join(full_text),
                segments=segments,
                language=info.language,
                duration=info.duration,
                output_path=None,
                engine=self.name,
                model=model_name,
                processing_time=processing_time,
                metadata={
                    "language_probability": info.language_probability,
                    "duration": info.duration,
                    "duration_after_vad": getattr(info, 'duration_after_vad', None),
                    "all_language_probs": getattr(info, 'all_language_probs', None),
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
            error_msg = f"Faster Whisper transcription failed: {str(e)}"
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
        """Get list of available Faster Whisper models."""
        return [
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v1",
            "large-v2",
            "large-v3"
        ]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        # Faster Whisper supports the same languages as OpenAI Whisper
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
        logger.info("Faster Whisper engine cleaned up")