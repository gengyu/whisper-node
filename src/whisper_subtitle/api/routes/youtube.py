"""YouTube monitoring and processing API routes."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from ...tasks.scheduler import TaskStatus
from ...tasks.youtube_fetcher import YouTubeChannel, VideoFetchResult

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class ChannelAddRequest(BaseModel):
    """Request model for adding a YouTube channel."""
    channel_id: str = Field(..., description="YouTube channel ID or username")
    channel_name: str = Field(..., description="Display name for the channel")
    transcription_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Transcription configuration"
    )


class ChannelResponse(BaseModel):
    """Response model for YouTube channel information."""
    channel_id: str
    channel_name: str
    last_check: Optional[datetime]
    last_video_id: Optional[str]
    enabled: bool
    transcription_config: Dict[str, Any]


class VideoResponse(BaseModel):
    """Response model for video information."""
    video_id: str
    title: str
    url: str
    duration: Optional[int]
    upload_date: Optional[str]
    downloaded: bool
    transcribed: bool
    file_path: Optional[str]
    error: Optional[str]


class ChannelStatusResponse(BaseModel):
    """Response model for channel processing status."""
    channel_id: str
    channel_name: str
    enabled: bool
    last_check: Optional[datetime]
    videos_found: List[VideoResponse]


class YouTubeStatusResponse(BaseModel):
    """Response model for overall YouTube processing status."""
    channels: int
    processed_videos: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int


class TaskResponse(BaseModel):
    """Response model for task information."""
    id: str
    name: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]


def get_youtube_fetcher(request: Request):
    """Dependency to get YouTube fetcher from app state."""
    if not hasattr(request.app.state, 'youtube_fetcher'):
        raise HTTPException(status_code=503, detail="YouTube fetcher not available")
    return request.app.state.youtube_fetcher


def get_scheduler(request: Request):
    """Dependency to get task scheduler from app state."""
    if not hasattr(request.app.state, 'scheduler'):
        raise HTTPException(status_code=503, detail="Task scheduler not available")
    return request.app.state.scheduler


@router.post("/youtube/channels", response_model=Dict[str, Any])
async def add_youtube_channel(
    request: ChannelAddRequest,
    youtube_fetcher=Depends(get_youtube_fetcher)
):
    """Add a YouTube channel for monitoring.
    
    Args:
        request: Channel addition request
        youtube_fetcher: YouTube fetcher service
    
    Returns:
        Success status and channel information
    """
    try:
        success = await youtube_fetcher.add_channel(
            channel_id=request.channel_id,
            channel_name=request.channel_name,
            transcription_config=request.transcription_config
        )
        
        if success:
            return {
                "success": True,
                "message": f"Channel '{request.channel_name}' added successfully",
                "channel_id": request.channel_id
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to add channel '{request.channel_id}'"
            )
            
    except Exception as e:
        logger.error(f"Error adding YouTube channel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/youtube/channels", response_model=List[ChannelResponse])
async def list_youtube_channels(youtube_fetcher=Depends(get_youtube_fetcher)):
    """List all monitored YouTube channels.
    
    Args:
        youtube_fetcher: YouTube fetcher service
    
    Returns:
        List of monitored channels
    """
    try:
        channels = await youtube_fetcher.get_channels()
        
        return [
            ChannelResponse(
                channel_id=channel.channel_id,
                channel_name=channel.channel_name,
                last_check=channel.last_check,
                last_video_id=channel.last_video_id,
                enabled=channel.enabled,
                transcription_config=channel.transcription_config or {}
            )
            for channel in channels
        ]
        
    except Exception as e:
        logger.error(f"Error listing YouTube channels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/youtube/channels/{channel_id}")
async def remove_youtube_channel(
    channel_id: str,
    youtube_fetcher=Depends(get_youtube_fetcher)
):
    """Remove a YouTube channel from monitoring.
    
    Args:
        channel_id: Channel ID to remove
        youtube_fetcher: YouTube fetcher service
    
    Returns:
        Success status
    """
    try:
        success = await youtube_fetcher.remove_channel(channel_id)
        
        if success:
            return {
                "success": True,
                "message": f"Channel '{channel_id}' removed successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_id}' not found"
            )
            
    except Exception as e:
        logger.error(f"Error removing YouTube channel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/youtube/channels/{channel_id}/enable")
async def enable_youtube_channel(
    channel_id: str,
    enabled: bool = True,
    youtube_fetcher=Depends(get_youtube_fetcher)
):
    """Enable or disable a YouTube channel.
    
    Args:
        channel_id: Channel ID
        enabled: Whether to enable the channel
        youtube_fetcher: YouTube fetcher service
    
    Returns:
        Success status
    """
    try:
        success = await youtube_fetcher.enable_channel(channel_id, enabled)
        
        if success:
            status = "enabled" if enabled else "disabled"
            return {
                "success": True,
                "message": f"Channel '{channel_id}' {status} successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_id}' not found"
            )
            
    except Exception as e:
        logger.error(f"Error updating YouTube channel status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/youtube/channels/check")
async def check_all_channels(
    youtube_fetcher=Depends(get_youtube_fetcher)
):
    """Manually trigger a check for new videos in all channels.
    
    Args:
        youtube_fetcher: YouTube fetcher service
    
    Returns:
        Check results for all channels
    """
    try:
        results = await youtube_fetcher.check_all_channels()
        
        response = []
        for channel_id, videos in results.items():
            channels = await youtube_fetcher.get_channels()
            channel = next((c for c in channels if c.channel_id == channel_id), None)
            
            if channel:
                response.append(ChannelStatusResponse(
                    channel_id=channel_id,
                    channel_name=channel.channel_name,
                    enabled=channel.enabled,
                    last_check=channel.last_check,
                    videos_found=[
                        VideoResponse(
                            video_id=video.video_id,
                            title=video.title,
                            url=video.url,
                            duration=video.duration,
                            upload_date=video.upload_date,
                            downloaded=video.downloaded,
                            transcribed=video.transcribed,
                            file_path=video.file_path,
                            error=video.error
                        )
                        for video in videos
                    ]
                ))
        
        return {
            "success": True,
            "message": f"Checked {len(results)} channels",
            "results": response
        }
        
    except Exception as e:
        logger.error(f"Error checking YouTube channels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/youtube/status", response_model=YouTubeStatusResponse)
async def get_youtube_status(youtube_fetcher=Depends(get_youtube_fetcher)):
    """Get YouTube processing status.
    
    Args:
        youtube_fetcher: YouTube fetcher service
    
    Returns:
        YouTube processing status
    """
    try:
        status = await youtube_fetcher.get_processing_status()
        
        return YouTubeStatusResponse(
            channels=status['channels'],
            processed_videos=status['processed_videos'],
            active_tasks=status['active_tasks'],
            completed_tasks=status['completed_tasks'],
            failed_tasks=status['failed_tasks']
        )
        
    except Exception as e:
        logger.error(f"Error getting YouTube status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/youtube/tasks", response_model=List[TaskResponse])
async def list_youtube_tasks(
    status: Optional[str] = None,
    limit: Optional[int] = 50,
    scheduler=Depends(get_scheduler)
):
    """List YouTube-related tasks.
    
    Args:
        status: Filter by task status
        limit: Maximum number of tasks to return
        scheduler: Task scheduler service
    
    Returns:
        List of YouTube-related tasks
    """
    try:
        # Convert string status to enum if provided
        status_filter = None
        if status:
            try:
                status_filter = TaskStatus(status.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: pending, running, completed, failed, cancelled"
                )
        
        tasks = await scheduler.list_tasks(status=status_filter, limit=limit)
        
        # Filter YouTube-related tasks
        youtube_tasks = [
            task for task in tasks
            if any(keyword in task.name.lower() for keyword in [
                'youtube', 'download video', 'transcribe video', 'check youtube'
            ])
        ]
        
        return [
            TaskResponse(
                id=task.id,
                name=task.name,
                status=task.status.value,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                error=task.error
            )
            for task in youtube_tasks
        ]
        
    except Exception as e:
        logger.error(f"Error listing YouTube tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/youtube/tasks/{task_id}")
async def cancel_youtube_task(
    task_id: str,
    scheduler=Depends(get_scheduler)
):
    """Cancel a YouTube-related task.
    
    Args:
        task_id: Task ID to cancel
        scheduler: Task scheduler service
    
    Returns:
        Success status
    """
    try:
        success = await scheduler.cancel_task(task_id)
        
        if success:
            return {
                "success": True,
                "message": f"Task '{task_id}' cancelled successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Task '{task_id}' not found or cannot be cancelled"
            )
            
    except Exception as e:
        logger.error(f"Error cancelling YouTube task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/youtube/cleanup")
async def cleanup_old_files(
    older_than_days: int = 30,
    youtube_fetcher=Depends(get_youtube_fetcher)
):
    """Clean up old downloaded files.
    
    Args:
        older_than_days: Remove files older than this many days
        youtube_fetcher: YouTube fetcher service
    
    Returns:
        Cleanup status
    """
    try:
        from datetime import timedelta
        
        await youtube_fetcher.cleanup_old_files(
            older_than=timedelta(days=older_than_days)
        )
        
        return {
            "success": True,
            "message": f"Cleanup completed for files older than {older_than_days} days"
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))