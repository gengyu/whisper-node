#!/usr/bin/env python3
"""Test YouTube transcription CLI functionality."""

import sys
import subprocess
from pathlib import Path

def test_youtube_cli():
    """Test the YouTube transcription CLI command."""
    
    # Test URL (short video)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print("🎬 Testing YouTube transcription CLI...")
    print(f"URL: {url}")
    print()
    
    try:
        # Run the CLI command
        cmd = [
            sys.executable, "-m", "whisper_subtitle.cli", 
            "youtube", "transcribe", url,
            "--engine", "openai_whisper",
            "--model", "tiny",
            "--format", "srt"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        print()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("\n✅ YouTube CLI transcription test passed!")
        else:
            print("\n❌ YouTube CLI transcription test failed!")
            
    except subprocess.TimeoutExpired:
        print("❌ Command timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Error running command: {e}")

if __name__ == "__main__":
    test_youtube_cli()