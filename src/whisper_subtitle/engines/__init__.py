"""Speech recognition engines for Whisper Subtitle Generator."""

from .base import BaseEngine, TranscriptionResult
from .openai_whisper import OpenAIWhisperEngine
from .faster_whisper import FasterWhisperEngine
from .whisperkit import WhisperKitEngine
from .whispercpp import WhisperCppEngine
from .alibaba_asr import AlibabaASREngine

__all__ = [
    "BaseEngine",
    "TranscriptionResult",
    "OpenAIWhisperEngine",
    "FasterWhisperEngine",
    "WhisperKitEngine",
    "WhisperCppEngine",
    "AlibabaASREngine",
]