#!/usr/bin/env python3
"""Command-line interface for Whisper Subtitle Generator."""

import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from whisper_subtitle.cli.main import cli

if __name__ == '__main__':
    cli()