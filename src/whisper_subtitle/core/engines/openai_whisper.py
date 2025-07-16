"""OpenAI Whisper engine implementation."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base import BaseEngine, TranscriptionResult

logger = logging.getLogger(__name__)


class OpenAIWhisperEngine(BaseEngine):
    """OpenAI Whisper engine for speech recognition."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI Whisper engine.
        
        Args:
            config: Engine configuration
        """
        super().__init__(config)
        self._whisper = None
        self._available_models = [
            "tiny", "tiny.en", "base", "base.en", 
            "small", "small.en", "medium", "medium.en",
            "large", "large-v1", "large-v2", "large-v3"
        ]
        self._available_languages = [
            "auto", "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr", "pl",
            "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi", "he", "uk", "el",
            "ms", "cs", "ro", "da", "hu", "ta", "no", "th", "ur", "hr", "bg", "lt",
            "la", "mi", "ml", "cy", "sk", "te", "fa", "lv", "bn", "sr", "az", "sl",
            "kn", "et", "mk", "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq",
            "sw", "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc", "ka",
            "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo", "ht", "ps", "tk",
            "nn", "mt", "sa", "lb", "my", "bo", "tl", "mg", "as", "tt", "haw", "ln",
            "ha", "ba", "jw", "su"
        ]
    
    def _load_whisper(self):
        """Load Whisper model lazily."""
        if self._whisper is None:
            try:
                import whisper
                self._whisper = whisper
                logger.info("OpenAI Whisper loaded successfully")
            except ImportError:
                logger.error("OpenAI Whisper not installed. Install with: pip install openai-whisper")
                raise
    
    def is_available(self) -> bool:
        """Check if OpenAI Whisper is available."""
        try:
            import whisper
            return True
        except ImportError:
            return False
    
    def get_models(self) -> List[str]:
        """Get list of available models."""
        return self._available_models.copy()
    
    def get_languages(self) -> List[str]:
        """Get list of supported languages."""
        return self._available_languages.copy()
    
    async def transcribe(
        self,
        file_path: Path,
        model: str = "base",
        language: str = "auto",
        output_format: str = "srt",
        output_path: Optional[Path] = None
    ) -> TranscriptionResult:
        """Transcribe audio/video file using OpenAI Whisper.
        
        Args:
            file_path: Path to the input file
            model: Whisper model to use
            language: Language code (auto for auto-detection)
            output_format: Output format (srt, vtt, txt)
            output_path: Path for output file
            
        Returns:
            TranscriptionResult with transcription details
        """
        start_time = time.time()
        
        try:
            # Load Whisper
            self._load_whisper()
            
            # Validate inputs
            if not file_path.exists():
                raise FileNotFoundError(f"Input file not found: {file_path}")
            
            if model not in self._available_models:
                logger.warning(f"Unknown model {model}, using 'base'")
                model = "base"
            
            # Generate output path if not provided
            if output_path is None:
                output_path = file_path.parent / f"{file_path.stem}.{output_format}"
            
            logger.info(f"Loading Whisper model: {model}")
            whisper_model = self._whisper.load_model(model)
            
            # Prepare transcription options
            options = {
                "language": None if language == "auto" else language,
                "task": "transcribe",
                "verbose": False
            }
            
            # Add config options
            if "temperature" in self.config:
                options["temperature"] = self.config["temperature"]
            if "beam_size" in self.config:
                options["beam_size"] = self.config["beam_size"]
            if "best_of" in self.config:
                options["best_of"] = self.config["best_of"]
            
            logger.info(f"Transcribing {file_path} with options: {options}")
            
            # Perform transcription
            result = whisper_model.transcribe(str(file_path), **options)
            
            # Extract segments
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "text": segment.get("text", "").strip()
                })
            
            # Format and save output
            self._format_output(segments, output_format, output_path)
            
            # Get full text
            full_text = result.get("text", "")
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                success=True,
                output_path=output_path,
                text=full_text,
                segments=segments,
                language=result.get("language"),
                duration=None,  # Whisper doesn't provide duration directly
                processing_time=processing_time,
                engine=self.name,
                model=model,
                metadata={
                    "whisper_version": getattr(self._whisper, "__version__", "unknown"),
                    "options": options
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"OpenAI Whisper transcription failed: {e}")
            
            return TranscriptionResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                engine=self.name,
                model=model
            )