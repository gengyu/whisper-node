"""Speech recognition engines."""

from .registry import EngineRegistry, register_engine
from .base import BaseEngine, TranscriptionResult

# Import and register engines
try:
    from .openai_whisper import OpenAIWhisperEngine
    register_engine("openai_whisper", OpenAIWhisperEngine)
except ImportError:
    pass

try:
    from .faster_whisper import FasterWhisperEngine
    register_engine("faster_whisper", FasterWhisperEngine)
except ImportError:
    pass

try:
    from .whisperkit import WhisperKitEngine
    register_engine("whisperkit", WhisperKitEngine)
except ImportError:
    pass

__all__ = ["EngineRegistry", "BaseEngine", "TranscriptionResult", "register_engine"]