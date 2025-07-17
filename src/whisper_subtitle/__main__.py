#!/usr/bin/env python3
"""Main entry point for the whisper_subtitle package."""

from .cli.main import cli


# PYTHONPATH=src python3 -m whisper_subtitle.api.main
# https://www.youtube.com/watch?v=HuFYqnbVbzY
if __name__ == '__main__':
    cli()