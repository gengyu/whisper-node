#!/usr/bin/env python3
"""Test YouTube download functionality."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from whisper_subtitle.utils.video import VideoDownloader

async def test_youtube_download():
    """Test YouTube video download."""
    print("Testing YouTube download functionality...")
    
    # YouTube URL to test (using a shorter, non-live video)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - short video for testing
    
    try:
        # Initialize downloader
        downloader = VideoDownloader()
        
        # Get video info first
        print(f"Getting video info for: {test_url}")
        info = await downloader.get_video_info(test_url)
        
        print(f"Video title: {info.get('title', 'Unknown')}")
        print(f"Duration: {info.get('duration', 'Unknown')} seconds")
        print(f"Uploader: {info.get('uploader', 'Unknown')}")
        
        # Download audio only for testing
        print("\nDownloading audio...")
        
        # Let VideoDownloader handle the path automatically
        downloaded_file = await downloader.download_video(
            url=test_url,
            output_path=None,  # Auto-generate path
            audio_only=True
        )
        
        if downloaded_file and downloaded_file.exists():
            print(f"✓ Audio downloaded successfully: {downloaded_file}")
            print(f"File size: {downloaded_file.stat().st_size / 1024 / 1024:.2f} MB")
        else:
            print("✗ Audio download failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_youtube_download())
    sys.exit(0 if success else 1)