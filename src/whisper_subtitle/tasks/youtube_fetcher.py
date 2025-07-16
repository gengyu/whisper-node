"""YouTube video fetcher for scheduled downloads."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from pathlib import Path

from ..utils.video import VideoDownloader
from ..core.service import TranscriptionService
from .scheduler import TaskScheduler, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class YouTubeChannel:
    """YouTube channel configuration."""
    channel_id: str
    channel_name: str
    last_check: Optional[datetime] = None
    last_video_id: Optional[str] = None
    enabled: bool = True
    transcription_config: Dict = None


@dataclass
class VideoFetchResult:
    """Result of video fetch operation."""
    video_id: str
    title: str
    url: str
    duration: Optional[int] = None
    upload_date: Optional[str] = None
    downloaded: bool = False
    transcribed: bool = False
    file_path: Optional[str] = None
    error: Optional[str] = None


class YouTubeFetcher:
    """YouTube video fetcher and processor."""
    
    def __init__(
        self,
        scheduler: TaskScheduler,
        transcription_service: TranscriptionService,
        download_dir: str = "downloads",
        check_interval: timedelta = timedelta(hours=1)
    ):
        self.scheduler = scheduler
        self.transcription_service = transcription_service
        self.download_dir = Path(download_dir)
        self.check_interval = check_interval
        
        self.video_downloader = VideoDownloader()
        self.channels: Dict[str, YouTubeChannel] = {}
        self.processed_videos: Set[str] = set()
        
        # Ensure download directory exists
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    async def add_channel(
        self,
        channel_id: str,
        channel_name: str,
        transcription_config: Dict = None
    ) -> bool:
        """Add a YouTube channel to monitor.
        
        Args:
            channel_id: YouTube channel ID or username
            channel_name: Display name for the channel
            transcription_config: Configuration for transcription
        
        Returns:
            True if channel was added successfully
        """
        if transcription_config is None:
            transcription_config = {
                "engine": "openai_whisper",
                "model": "base",
                "language": "auto",
                "output_format": "srt"
            }
        
        try:
            # Verify channel exists by getting channel info
            channel_url = f"https://www.youtube.com/@{channel_id}"
            info = await self.video_downloader.get_video_info(channel_url)
            
            channel = YouTubeChannel(
                channel_id=channel_id,
                channel_name=channel_name,
                transcription_config=transcription_config
            )
            
            self.channels[channel_id] = channel
            
            # Schedule periodic check for this channel
            await self.scheduler.schedule_recurring_task(
                task_id=f"youtube_check_{channel_id}",
                name=f"Check YouTube channel: {channel_name}",
                func=self._check_channel_for_new_videos,
                interval=self.check_interval,
                args=(channel_id,)
            )
            
            logger.info(f"Added YouTube channel: {channel_name} (ID: {channel_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add YouTube channel {channel_id}: {str(e)}")
            return False
    
    async def remove_channel(self, channel_id: str) -> bool:
        """Remove a YouTube channel from monitoring.
        
        Args:
            channel_id: Channel ID to remove
        
        Returns:
            True if channel was removed
        """
        if channel_id not in self.channels:
            return False
        
        # Cancel the scheduled task
        await self.scheduler.cancel_task(f"youtube_check_{channel_id}")
        
        # Remove from channels
        del self.channels[channel_id]
        
        logger.info(f"Removed YouTube channel: {channel_id}")
        return True
    
    async def get_channels(self) -> List[YouTubeChannel]:
        """Get list of monitored channels.
        
        Returns:
            List of YouTube channels
        """
        return list(self.channels.values())
    
    async def enable_channel(self, channel_id: str, enabled: bool = True) -> bool:
        """Enable or disable channel monitoring.
        
        Args:
            channel_id: Channel ID
            enabled: Whether to enable monitoring
        
        Returns:
            True if channel status was updated
        """
        if channel_id not in self.channels:
            return False
        
        self.channels[channel_id].enabled = enabled
        logger.info(f"Channel {channel_id} {'enabled' if enabled else 'disabled'}")
        return True
    
    async def check_all_channels(self) -> Dict[str, List[VideoFetchResult]]:
        """Check all channels for new videos.
        
        Returns:
            Dictionary mapping channel IDs to lists of new videos
        """
        results = {}
        
        for channel_id in self.channels.keys():
            try:
                videos = await self._check_channel_for_new_videos(channel_id)
                if videos:
                    results[channel_id] = videos
            except Exception as e:
                logger.error(f"Error checking channel {channel_id}: {str(e)}")
                results[channel_id] = []
        
        return results
    
    async def _check_channel_for_new_videos(self, channel_id: str) -> List[VideoFetchResult]:
        """Check a specific channel for new videos.
        
        Args:
            channel_id: Channel ID to check
        
        Returns:
            List of new videos found
        """
        if channel_id not in self.channels:
            logger.warning(f"Channel {channel_id} not found")
            return []
        
        channel = self.channels[channel_id]
        
        if not channel.enabled:
            logger.debug(f"Channel {channel_id} is disabled, skipping")
            return []
        
        logger.info(f"Checking channel for new videos: {channel.channel_name}")
        
        try:
            # Get channel URL
            channel_url = f"https://www.youtube.com/@{channel_id}"
            
            # Get recent videos from the channel
            playlist_info = await self.video_downloader.get_playlist_info(
                channel_url,
                max_videos=10  # Check last 10 videos
            )
            
            new_videos = []
            
            for video_info in playlist_info.get('entries', []):
                video_id = video_info.get('id')
                
                if not video_id:
                    continue
                
                # Skip if we've already processed this video
                if video_id in self.processed_videos:
                    continue
                
                # Check if this video is newer than our last check
                upload_date = video_info.get('upload_date')
                if channel.last_check and upload_date:
                    try:
                        video_date = datetime.strptime(upload_date, '%Y%m%d')
                        if video_date <= channel.last_check:
                            continue
                    except ValueError:
                        pass  # If date parsing fails, process the video anyway
                
                # Create video fetch result
                video_result = VideoFetchResult(
                    video_id=video_id,
                    title=video_info.get('title', 'Unknown'),
                    url=video_info.get('webpage_url', f"https://www.youtube.com/watch?v={video_id}"),
                    duration=video_info.get('duration'),
                    upload_date=upload_date
                )
                
                new_videos.append(video_result)
                
                # Schedule download and transcription
                await self._schedule_video_processing(channel_id, video_result)
            
            # Update last check time
            channel.last_check = datetime.now()
            
            if new_videos:
                logger.info(f"Found {len(new_videos)} new videos in channel: {channel.channel_name}")
            
            return new_videos
            
        except Exception as e:
            logger.error(f"Error checking channel {channel_id}: {str(e)}")
            return []
    
    async def _schedule_video_processing(self, channel_id: str, video: VideoFetchResult):
        """Schedule download and transcription for a video.
        
        Args:
            channel_id: Channel ID
            video: Video to process
        """
        channel = self.channels[channel_id]
        
        # Schedule download task
        download_task_id = f"download_{video.video_id}"
        await self.scheduler.schedule_task(
            task_id=download_task_id,
            name=f"Download video: {video.title}",
            func=self._download_video,
            args=(channel_id, video)
        )
        
        # Schedule transcription task (depends on download)
        transcription_task_id = f"transcribe_{video.video_id}"
        await self.scheduler.schedule_task(
            task_id=transcription_task_id,
            name=f"Transcribe video: {video.title}",
            func=self._transcribe_video,
            args=(channel_id, video),
            schedule_time=datetime.now() + timedelta(minutes=5)  # Delay to allow download
        )
        
        # Mark as processed
        self.processed_videos.add(video.video_id)
    
    async def _download_video(self, channel_id: str, video: VideoFetchResult) -> bool:
        """Download a video.
        
        Args:
            channel_id: Channel ID
            video: Video to download
        
        Returns:
            True if download was successful
        """
        try:
            logger.info(f"Downloading video: {video.title}")
            
            # Create channel-specific directory
            channel_dir = self.download_dir / channel_id
            channel_dir.mkdir(exist_ok=True)
            
            # Download video
            result = await self.video_downloader.download_video(
                video.url,
                str(channel_dir),
                audio_only=True  # We only need audio for transcription
            )
            
            if result['success']:
                video.downloaded = True
                video.file_path = result['file_path']
                logger.info(f"Successfully downloaded: {video.title}")
                return True
            else:
                video.error = result.get('error', 'Download failed')
                logger.error(f"Failed to download {video.title}: {video.error}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            video.error = error_msg
            logger.error(f"Error downloading video {video.title}: {error_msg}")
            return False
    
    async def _transcribe_video(self, channel_id: str, video: VideoFetchResult) -> bool:
        """Transcribe a downloaded video.
        
        Args:
            channel_id: Channel ID
            video: Video to transcribe
        
        Returns:
            True if transcription was successful
        """
        try:
            # Check if video was downloaded
            if not video.downloaded or not video.file_path:
                logger.warning(f"Video not downloaded, skipping transcription: {video.title}")
                return False
            
            # Check if file exists
            if not Path(video.file_path).exists():
                logger.warning(f"Downloaded file not found: {video.file_path}")
                return False
            
            logger.info(f"Transcribing video: {video.title}")
            
            channel = self.channels[channel_id]
            config = channel.transcription_config
            
            # Perform transcription
            result = await self.transcription_service.transcribe_file(
                file_path=video.file_path,
                engine=config.get('engine', 'openai_whisper'),
                model=config.get('model', 'base'),
                language=config.get('language', 'auto'),
                output_format=config.get('output_format', 'srt')
            )
            
            if result.success:
                video.transcribed = True
                
                # Save transcription to file
                output_dir = Path(video.file_path).parent
                output_file = output_dir / f"{Path(video.file_path).stem}.{config.get('output_format', 'srt')}"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    if config.get('output_format') == 'srt':
                        f.write(result.to_srt())
                    elif config.get('output_format') == 'vtt':
                        f.write(result.to_vtt())
                    else:
                        f.write(result.to_text())
                
                logger.info(f"Successfully transcribed: {video.title}")
                logger.info(f"Transcription saved to: {output_file}")
                return True
            else:
                video.error = result.error or 'Transcription failed'
                logger.error(f"Failed to transcribe {video.title}: {video.error}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            video.error = error_msg
            logger.error(f"Error transcribing video {video.title}: {error_msg}")
            return False
    
    async def get_processing_status(self) -> Dict[str, Dict]:
        """Get status of all video processing tasks.
        
        Returns:
            Dictionary with processing status information
        """
        status = {
            'channels': len(self.channels),
            'processed_videos': len(self.processed_videos),
            'active_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0
        }
        
        # Get task statistics
        tasks = await self.scheduler.list_tasks()
        
        for task in tasks:
            if task.name.startswith(('Download video:', 'Transcribe video:')):
                if task.status == TaskStatus.RUNNING:
                    status['active_tasks'] += 1
                elif task.status == TaskStatus.COMPLETED:
                    status['completed_tasks'] += 1
                elif task.status == TaskStatus.FAILED:
                    status['failed_tasks'] += 1
        
        return status
    
    async def cleanup_old_files(self, older_than: timedelta = timedelta(days=30)):
        """Clean up old downloaded files.
        
        Args:
            older_than: Remove files older than this duration
        """
        cutoff_time = datetime.now() - older_than
        removed_count = 0
        
        try:
            for file_path in self.download_dir.rglob('*'):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old files")
                
        except Exception as e:
            logger.error(f"Error during file cleanup: {str(e)}")