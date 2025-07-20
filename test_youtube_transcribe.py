#!/usr/bin/env python3
"""Test YouTube transcription functionality."""

import asyncio
from pathlib import Path

from src.whisper_subtitle.utils.video import VideoDownloader
from src.whisper_subtitle.core.transcriber import TranscriptionService


async def test_youtube_transcribe():
    """Test YouTube video transcription."""
    print("Testing YouTube transcription functionality...")
    
    # YouTube URL to test (using a shorter, non-live video)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - short video for testing
    
    try:
        # Initialize services
        downloader = VideoDownloader()
        transcriber = TranscriptionService()
        
        # Get video info first
        print(f"Getting video info for: {test_url}")
        # info = await downloader.get_video_info(test_url)
        #
        # print(f"Video title: {info.get('title', 'Unknown')}")
        # print(f"Duration: {info.get('duration', 'Unknown')} seconds")
        # print(f"Uploader: {info.get('uploader', 'Unknown')}")
        
        # Download audio only for transcription
        print("\nDownloading audio...")
        
        downloaded_file = await downloader.download_video(
            url=test_url,
            output_path=None,  # Auto-generate path
            audio_only=False
        )
        
        if downloaded_file and downloaded_file.exists():
            print(f"✓ Audio downloaded successfully: {downloaded_file}")
            print(f"File size: {downloaded_file.stat().st_size / 1024 / 1024:.2f} MB")
        else:
            print("✗ Audio download failed")
            return False
        
        # Transcribe the downloaded audio
        print("\nTranscribing audio...")
        
        result = await transcriber.transcribe_audio(
            audio_path=downloaded_file,
            # engine_name="openai_whisper",  # Use OpenAI Whisper as it's most reliable
            engine_name="whisperkit",
            # engine_name="whispercpp",
            model_name="tiny",  # Use tiny model for faster processing
            language="en",  # English
            output_format="srt"
        )
        
        if result and result.output_path and Path(result.output_path).exists():
            print(f"✓ Transcription completed: {result.output_path}")
            print(f"Processing time: {result.duration:.2f} seconds")
            
            # Show first few lines of the subtitle
            with open(result.output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:10]  # First 10 lines
                print("\nFirst few lines of subtitle:")
                print("" + "".join(lines))
        else:
            print("✗ Transcription failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_youtube_transcribe())
    if success:
        print("\n🎉 YouTube transcription test completed successfully!")
    else:
        print("\n❌ YouTube transcription test failed.")