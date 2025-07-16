"""Whisper Subtitle Generator - Video speech recognition and subtitle generation."""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "Video speech recognition and subtitle generation with multiple Whisper engines"

from .config.settings import settings
from .core.transcriber import TranscriptionService
from .engines import (
    OpenAIWhisperEngine,
    FasterWhisperEngine,
    WhisperKitEngine,
    WhisperCppEngine,
    AlibabaASREngine,
)

__all__ = [
    "settings",
    "TranscriptionService",
    "OpenAIWhisperEngine",
    "FasterWhisperEngine",
    "WhisperKitEngine",
    "WhisperCppEngine",
    "AlibabaASREngine",
]