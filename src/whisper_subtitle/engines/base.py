"""Base classes for speech recognition engines."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Dict, Any


@dataclass
class TranscriptionSegment:
    """Represents a single transcription segment with timing information."""
    start: float  # Start time in seconds
    end: float    # End time in seconds
    text: str     # Transcribed text
    confidence: Optional[float] = None  # Confidence score (0-1)
    speaker: Optional[str] = None       # Speaker identification
    
    @property
    def duration(self) -> float:
        """Duration of the segment in seconds."""
        return self.end - self.start
    
    def to_srt_format(self, index: int) -> str:
        """Convert segment to SRT subtitle format."""
        start_time = self._seconds_to_srt_time(self.start)
        end_time = self._seconds_to_srt_time(self.end)
        return f"{index}\n{start_time} --> {end_time}\n{self.text}\n"
    
    def to_vtt_format(self) -> str:
        """Convert segment to WebVTT format."""
        start_time = self._seconds_to_vtt_time(self.start)
        end_time = self._seconds_to_vtt_time(self.end)
        return f"{start_time} --> {end_time}\n{self.text}\n"
    
    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    @staticmethod
    def _seconds_to_vtt_time(seconds: float) -> str:
        """Convert seconds to WebVTT time format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"


@dataclass
class TranscriptionResult:
    """Complete transcription result with metadata."""
    text: str                           # Full transcribed text
    segments: List[TranscriptionSegment] # Individual segments with timing
    language: str                       # Detected/specified language
    duration: float                     # Total audio duration in seconds
    output_path: Optional[Path]         # Path to saved subtitle file
    engine: str                         # Engine used for transcription
    model: str                          # Model used for transcription
    confidence: Optional[float] = None  # Overall confidence score
    processing_time: Optional[float] = None  # Time taken for processing
    error: Optional[str] = None         # Error message if any
    metadata: Dict[str, Any] = None     # Additional metadata
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_successful(self) -> bool:
        """Check if transcription was successful."""
        return self.error is None and bool(self.text.strip())
    
    def to_srt(self) -> str:
        """Convert result to SRT subtitle format."""
        if not self.segments:
            return ""
        
        srt_content = []
        for i, segment in enumerate(self.segments, 1):
            srt_content.append(segment.to_srt_format(i))
        
        return "\n".join(srt_content)
    
    def to_vtt(self) -> str:
        """Convert result to WebVTT subtitle format."""
        if not self.segments:
            return "WEBVTT\n\n"
        
        vtt_content = ["WEBVTT\n"]
        for segment in self.segments:
            vtt_content.append(segment.to_vtt_format())
        
        return "\n".join(vtt_content)
    
    def to_txt(self) -> str:
        """Convert result to plain text format."""
        return self.text
    
    def to_json(self) -> Dict[str, Any]:
        """Convert result to JSON-serializable dictionary."""
        return {
            "text": self.text,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "confidence": seg.confidence,
                    "speaker": seg.speaker,
                }
                for seg in self.segments
            ],
            "language": self.language,
            "duration": self.duration,
            "engine": self.engine,
            "model": self.model,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "error": self.error,
            "metadata": self.metadata,
        }
    
    def save_to_file(self, output_path: Union[str, Path], format: str = "srt") -> Path:
        """Save transcription result to file.
        
        Args:
            output_path: Path to save the file
            format: Output format (srt, vtt, txt, json)
        
        Returns:
            Path to the saved file
        """
        output_path = Path(output_path)
        
        if format.lower() == "srt":
            content = self.to_srt()
        elif format.lower() == "vtt":
            content = self.to_vtt()
        elif format.lower() == "txt":
            content = self.to_txt()
        elif format.lower() == "json":
            import json
            content = json.dumps(self.to_json(), indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        
        self.output_path = output_path
        return output_path


class BaseEngine(ABC):
    """Abstract base class for speech recognition engines."""
    
    def __init__(self, name: str):
        self.name = name
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the engine (download models, setup, etc.)."""
        pass
    
    @abstractmethod
    async def is_ready(self) -> bool:
        """Check if the engine is ready to use."""
        pass
    
    @abstractmethod
    async def transcribe(
        self,
        audio_path: Union[str, Path],
        model_name: str = "medium",
        language: Optional[str] = None,
        output_format: str = "srt",
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio file.
        
        Args:
            audio_path: Path to audio file
            model_name: Model name/size to use
            language: Language code (auto-detect if None)
            output_format: Output format (srt, vtt, txt, json)
            **kwargs: Additional engine-specific parameters
        
        Returns:
            TranscriptionResult object
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this engine."""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        pass
    
    async def cleanup(self) -> None:
        """Clean up resources used by the engine."""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"
    
    def __repr__(self) -> str:
        return self.__str__()