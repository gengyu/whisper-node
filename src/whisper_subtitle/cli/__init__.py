"""Command-line interface module for the whisper subtitle generator."""

from .main import main, cli
from .commands import transcribe, server, youtube

__all__ = ['main', 'cli', 'transcribe', 'server', 'youtube']