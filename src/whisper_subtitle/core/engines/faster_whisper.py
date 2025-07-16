"""Faster Whisper engine implementation."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base import BaseEngine, TranscriptionResult

logger = logging.getLogger(__name__)


class FasterWhisperEngine(BaseEngine):
    """Faster Whisper engine for speech recognition."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Faster Whisper engine.
        
        Args:
            config: Engine configuration
        """
        super().__init__(config)
        self._model = None
        self._available_models = [
            "tiny", "tiny.en", "base", "base.en", 
            "small", "small.en", "medium", "medium.en",
            "large-v1", "large-v2", "large-v3", "large"
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
    
    def _load_model(self, model_name: str):
        """Load Faster Whisper model.
        
        Args:
            model_name: Name of the model to load
        """
        try:
            from faster_whisper import WhisperModel
            
            # Get device and compute type from config
            device = self.config.get("device", "auto")
            compute_type = self.config.get("compute_type", "default")
            
            logger.info(f"Loading Faster Whisper model: {model_name} on {device}")
            
            self._model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                cpu_threads=self.config.get("cpu_threads", 0),
                num_workers=self.config.get("num_workers", 1)
            )
            
            logger.info(f"Faster Whisper model {model_name} loaded successfully")
            
        except ImportError:
            logger.error("Faster Whisper not installed. Install with: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error(f"Failed to load Faster Whisper model {model_name}: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Faster Whisper is available."""
        try:
            from faster_whisper import WhisperModel
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
        """Transcribe audio/video file using Faster Whisper.
        
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
            # Validate inputs
            if not file_path.exists():
                raise FileNotFoundError(f"Input file not found: {file_path}")
            
            if model not in self._available_models:
                logger.warning(f"Unknown model {model}, using 'base'")
                model = "base"
            
            # Load model if needed
            if self._model is None:
                self._load_model(model)
            
            # Generate output path if not provided
            if output_path is None:
                output_path = file_path.parent / f"{file_path.stem}.{output_format}"
            
            # Prepare transcription options
            language_code = None if language == "auto" else language
            
            # Get additional options from config
            beam_size = self.config.get("beam_size", 5)
            best_of = self.config.get("best_of", 5)
            temperature = self.config.get("temperature", 0.0)
            condition_on_previous_text = self.config.get("condition_on_previous_text", True)
            
            logger.info(f"Transcribing {file_path} with Faster Whisper")
            
            # Perform transcription
            segments, info = self._model.transcribe(
                str(file_path),
                language=language_code,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                condition_on_previous_text=condition_on_previous_text,
                vad_filter=self.config.get("vad_filter", True),
                vad_parameters=self.config.get("vad_parameters", None)
            )
            
            # Convert segments to list and extract text
            segment_list = []
            full_text_parts = []
            
            for segment in segments:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                }
                segment_list.append(segment_dict)
                full_text_parts.append(segment.text.strip())
            
            # Format and save output
            self._format_output(segment_list, output_format, output_path)
            
            # Get full text
            full_text = " ".join(full_text_parts)
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                success=True,
                output_path=output_path,
                text=full_text,
                segments=segment_list,
                language=info.language,
                duration=info.duration,
                processing_time=processing_time,
                engine=self.name,
                model=model,
                metadata={
                    "language_probability": info.language_probability,
                    "duration": info.duration,
                    "duration_after_vad": getattr(info, "duration_after_vad", None),
                    "all_language_probs": getattr(info, "all_language_probs", None),
                    "options": {
                        "beam_size": beam_size,
                        "best_of": best_of,
                        "temperature": temperature,
                        "condition_on_previous_text": condition_on_previous_text
                    }
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Faster Whisper transcription failed: {e}")
            
            return TranscriptionResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                engine=self.name,
                model=model
            )