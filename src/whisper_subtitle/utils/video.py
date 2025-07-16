"""Video download utilities using yt-dlp."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

import yt_dlp

from ..config.settings import settings

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Video downloader using yt-dlp."""
    
    def __init__(self):
        self.download_dir = settings.temp_dir / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_video(
        self,
        url: str,
        output_path: Optional[Union[str, Path]] = None,
        quality: str = "best[height<=720]",
        audio_only: bool = False,
        **kwargs
    ) -> Path:
        """Download video from URL.
        
        Args:
            url: Video URL
            output_path: Output file path (auto-generated if None)
            quality: Video quality selector
            audio_only: Download audio only
            **kwargs: Additional yt-dlp options
        
        Returns:
            Path to downloaded file
        """
        logger.info(f"Downloading video from: {url}")
        
        try:
            # Get video info first
            info = await self.get_video_info(url)
            
            if output_path is None:
                # Generate output filename
                title = info.get('title', 'video').replace('/', '_').replace('\\', '_')
                ext = 'mp3' if audio_only else info.get('ext', 'mp4')
                output_path = self.download_dir / f"{title}.{ext}"
            else:
                output_path = Path(output_path)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Configure yt-dlp options
            ydl_opts = {
                'outtmpl': str(output_path.with_suffix('')),
                'format': 'bestaudio/best' if audio_only else quality,
                'noplaylist': True,
                'extractaudio': audio_only,
                'audioformat': 'mp3' if audio_only else None,
                'audioquality': '192',
                **kwargs
            }
            
            # Run download in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._download_with_ydl(url, ydl_opts)
            )
            
            # Find the actual downloaded file
            downloaded_files = list(output_path.parent.glob(f"{output_path.stem}.*"))
            if not downloaded_files:
                raise RuntimeError("Download completed but no file found")
            
            actual_file = downloaded_files[0]
            
            # Rename to expected path if different
            if actual_file != output_path:
                actual_file.rename(output_path)
                actual_file = output_path
            
            logger.info(f"Video downloaded successfully: {actual_file}")
            return actual_file
            
        except Exception as e:
            error_msg = f"Video download failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _download_with_ydl(self, url: str, ydl_opts: dict) -> None:
        """Download video using yt-dlp (synchronous)."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    
    async def get_video_info(self, url: str) -> Dict:
        """Get video information without downloading.
        
        Args:
            url: Video URL
        
        Returns:
            Dictionary with video information
        """
        logger.info(f"Getting video info for: {url}")
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extractaudio': False,
                'noplaylist': True,
            }
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._get_info_with_ydl(url, ydl_opts)
            )
            
            return info
            
        except Exception as e:
            error_msg = f"Failed to get video info: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _get_info_with_ydl(self, url: str, ydl_opts: dict) -> Dict:
        """Get video info using yt-dlp (synchronous)."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    
    async def get_playlist_info(self, url: str) -> List[Dict]:
        """Get playlist information.
        
        Args:
            url: Playlist URL
        
        Returns:
            List of video information dictionaries
        """
        logger.info(f"Getting playlist info for: {url}")
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extractaudio': False,
                'extract_flat': True,  # Don't extract individual video info
            }
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._get_info_with_ydl(url, ydl_opts)
            )
            
            if 'entries' in info:
                return list(info['entries'])
            else:
                return [info]
            
        except Exception as e:
            error_msg = f"Failed to get playlist info: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def download_playlist(
        self,
        url: str,
        output_dir: Optional[Union[str, Path]] = None,
        quality: str = "best[height<=720]",
        audio_only: bool = False,
        max_downloads: Optional[int] = None,
        **kwargs
    ) -> List[Path]:
        """Download entire playlist.
        
        Args:
            url: Playlist URL
            output_dir: Output directory
            quality: Video quality selector
            audio_only: Download audio only
            max_downloads: Maximum number of videos to download
            **kwargs: Additional yt-dlp options
        
        Returns:
            List of downloaded file paths
        """
        if output_dir is None:
            output_dir = self.download_dir / "playlist"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading playlist from: {url}")
        
        try:
            # Get playlist info
            playlist_info = await self.get_playlist_info(url)
            
            if max_downloads:
                playlist_info = playlist_info[:max_downloads]
            
            # Download videos concurrently (with limit)
            semaphore = asyncio.Semaphore(3)  # Limit concurrent downloads
            
            async def download_single(video_info: Dict) -> Optional[Path]:
                async with semaphore:
                    try:
                        video_url = video_info.get('url') or video_info.get('webpage_url')
                        if not video_url:
                            logger.warning(f"No URL found for video: {video_info.get('title', 'Unknown')}")
                            return None
                        
                        return await self.download_video(
                            video_url,
                            output_path=None,  # Auto-generate
                            quality=quality,
                            audio_only=audio_only,
                            **kwargs
                        )
                    except Exception as e:
                        logger.error(f"Failed to download video {video_info.get('title', 'Unknown')}: {str(e)}")
                        return None
            
            # Download all videos
            tasks = [download_single(video_info) for video_info in playlist_info]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful downloads
            downloaded_files = [result for result in results if isinstance(result, Path)]
            
            logger.info(f"Downloaded {len(downloaded_files)} videos from playlist")
            return downloaded_files
            
        except Exception as e:
            error_msg = f"Playlist download failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def get_supported_sites(self) -> List[str]:
        """Get list of supported sites.
        
        Returns:
            List of supported site names
        """
        try:
            loop = asyncio.get_event_loop()
            extractors = await loop.run_in_executor(
                None,
                lambda: yt_dlp.extractor.list_extractors()
            )
            
            return [extractor.IE_NAME for extractor in extractors if hasattr(extractor, 'IE_NAME')]
            
        except Exception as e:
            logger.error(f"Failed to get supported sites: {str(e)}")
            return []
    
    def is_supported_url(self, url: str) -> bool:
        """Check if URL is supported by yt-dlp.
        
        Args:
            url: URL to check
        
        Returns:
            True if URL is supported
        """
        try:
            # Try to extract info without downloading
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'simulate': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=False)
            
            return True
            
        except Exception:
            return False
    
    async def cleanup_downloads(self, older_than_days: int = 7) -> None:
        """Clean up old downloaded files.
        
        Args:
            older_than_days: Delete files older than this many days
        """
        import time
        
        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        
        try:
            deleted_count = 0
            for file_path in self.download_dir.rglob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old download files")
            
        except Exception as e:
            logger.error(f"Failed to cleanup downloads: {str(e)}")