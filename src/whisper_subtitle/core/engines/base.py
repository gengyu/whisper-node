"""Base engine class for speech recognition."""

import abc
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""
    success: bool
    output_path: Optional[Path] = None
    text: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    processing_time: Optional[float] = None
    engine: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class BaseEngine(abc.ABC):
    """Base class for speech recognition engines."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the engine with configuration."""
        self.config = config
        self.name = self.__class__.__name__.lower().replace('engine', '')
    
    @abc.abstractmethod
    async def transcribe(
        self,
        file_path: Path,
        model: str = "base",
        language: str = "auto",
        output_format: str = "srt",
        output_path: Optional[Path] = None
    ) -> TranscriptionResult:
        """Transcribe audio/video file.
        
        Args:
            file_path: Path to the input file
            model: Model to use for transcription
            language: Language code (auto for auto-detection)
            output_format: Output format (srt, vtt, txt)
            output_path: Path for output file
            
        Returns:
            TranscriptionResult with transcription details
        """
        pass
    
    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if the engine is available and ready to use."""
        pass
    
    @abc.abstractmethod
    def get_models(self) -> List[str]:
        """Get list of available models."""
        pass
    
    @abc.abstractmethod
    def get_languages(self) -> List[str]:
        """Get list of supported languages."""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get engine information."""
        return {
            "name": self.name,
            "ready": self.is_available(),
            "models": self.get_models(),
            "languages": self.get_languages(),
            "config": self.config
        }
    
    def _format_output(
        self,
        segments: List[Dict[str, Any]],
        output_format: str,
        output_path: Path
    ) -> None:
        """Format and save transcription output.
        
        Args:
            segments: List of transcription segments
            output_format: Output format (srt, vtt, txt)
            output_path: Path to save the output
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_format.lower() == "srt":
            self._write_srt(segments, output_path)
        elif output_format.lower() == "vtt":
            self._write_vtt(segments, output_path)
        elif output_format.lower() == "txt":
            self._write_txt(segments, output_path)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _write_srt(self, segments: List[Dict[str, Any]], output_path: Path) -> None:
        """Write SRT format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start_time = self._format_time_srt(segment.get('start', 0))
                end_time = self._format_time_srt(segment.get('end', 0))
                text = segment.get('text', '').strip()
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
    
    def _write_vtt(self, segments: List[Dict[str, Any]], output_path: Path) -> None:
        """Write VTT format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for segment in segments:
                start_time = self._format_time_vtt(segment.get('start', 0))
                end_time = self._format_time_vtt(segment.get('end', 0))
                text = segment.get('text', '').strip()
                
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
    
    def _write_txt(self, segments: List[Dict[str, Any]], output_path: Path) -> None:
        """Write plain text format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                text = segment.get('text', '').strip()
                if text:
                    f.write(f"{text}\n")
    
    def _format_time_srt(self, seconds: float) -> str:
        """Format time for SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _format_time_vtt(self, seconds: float) -> str:
        """Format time for VTT format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"