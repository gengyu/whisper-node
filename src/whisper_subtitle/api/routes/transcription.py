"""Transcription API routes."""

import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field

from ...config.settings import settings
from ...utils.video import VideoDownloader

logger = logging.getLogger(__name__)

router = APIRouter()


class TranscriptionRequest(BaseModel):
    """Transcription request model."""
    file_path: Optional[str] = Field(None, description="Path to local file")
    url: Optional[str] = Field(None, description="URL to download video/audio")
    engine: str = Field("openai_whisper", description="Speech recognition engine")
    model: Optional[str] = Field(None, description="Model name (engine-specific)")
    language: Optional[str] = Field(None, description="Source language code")
    output_format: str = Field("srt", description="Output subtitle format")
    merge_segments: bool = Field(True, description="Merge short segments")
    split_long_segments: bool = Field(True, description="Split long segments")
    filter_short_segments: bool = Field(True, description="Filter very short segments")
    task_id: Optional[str] = Field(None, description="Task ID for tracking")


class TranscriptionResponse(BaseModel):
    """Transcription response model."""
    task_id: str
    status: str
    message: str
    file_path: Optional[str] = None
    download_url: Optional[str] = None
    segments: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None


class TaskStatusResponse(BaseModel):
    """Task status response model."""
    task_id: str
    status: str
    progress: float
    message: str
    result: Optional[Dict] = None
    error: Optional[str] = None


# In-memory task storage (in production, use Redis or database)
tasks: Dict[str, Dict] = {}


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    request: TranscriptionRequest,
    background_tasks: BackgroundTasks,
    app_request: Request
):
    """Start transcription task."""
    try:
        # Generate task ID
        task_id = request.task_id or str(uuid.uuid4())
        
        # Validate request
        if not request.file_path and not request.url:
            raise HTTPException(
                status_code=400,
                detail="Either file_path or url must be provided"
            )
        
        # Get transcription service
        transcription_service = app_request.app.state.transcription_service
        
        # Check if engine is available
        available_engines = transcription_service.get_available_engines()
        if request.engine not in available_engines:
            raise HTTPException(
                status_code=400,
                detail=f"Engine '{request.engine}' is not available. Available engines: {available_engines}"
            )
        
        # Initialize task
        tasks[task_id] = {
            "status": "pending",
            "progress": 0.0,
            "message": "Task created",
            "request": request.dict(),
            "result": None,
            "error": None
        }
        
        # Start background task
        background_tasks.add_task(
            _process_transcription_task,
            task_id,
            request,
            transcription_service
        )
        
        return TranscriptionResponse(
            task_id=task_id,
            status="pending",
            message="Transcription task started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start transcription task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transcribe/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get transcription task status."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        result=task["result"],
        error=task["error"]
    )


@router.get("/transcribe/{task_id}/result")
async def get_task_result(task_id: str):
    """Get transcription task result."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task is not completed. Current status: {task['status']}"
        )
    
    return task["result"]


@router.delete("/transcribe/{task_id}")
async def cancel_task(task_id: str):
    """Cancel transcription task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    if task["status"] in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Task cannot be cancelled. Current status: {task['status']}"
        )
    
    # Mark as cancelled
    tasks[task_id]["status"] = "cancelled"
    tasks[task_id]["message"] = "Task cancelled by user"
    
    return {"message": "Task cancelled successfully"}


@router.get("/transcribe/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 50):
    """List transcription tasks."""
    filtered_tasks = []
    
    for task_id, task in tasks.items():
        if status is None or task["status"] == status:
            filtered_tasks.append({
                "task_id": task_id,
                "status": task["status"],
                "progress": task["progress"],
                "message": task["message"],
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at")
            })
    
    # Sort by creation time (most recent first)
    filtered_tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "tasks": filtered_tasks[:limit],
        "total": len(filtered_tasks)
    }


async def _process_transcription_task(
    task_id: str,
    request: TranscriptionRequest,
    transcription_service
):
    """Process transcription task in background."""
    try:
        # Update task status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["message"] = "Starting transcription"
        tasks[task_id]["progress"] = 0.1
        
        # Determine input file
        if request.url:
            # Download from URL
            tasks[task_id]["message"] = "Downloading video"
            tasks[task_id]["progress"] = 0.2
            
            downloader = VideoDownloader()
            input_file = await downloader.download_video(
                request.url,
                audio_only=True  # Download audio only for transcription
            )
        else:
            # Use local file
            input_file = Path(request.file_path)
            if not input_file.exists():
                raise FileNotFoundError(f"File not found: {input_file}")
        
        # Start transcription
        tasks[task_id]["message"] = "Transcribing audio"
        tasks[task_id]["progress"] = 0.4
        
        # Transcribe
        result = await transcription_service.transcribe_file(
            file_path=str(input_file),
            engine=request.engine,
            model=request.model,
            language=request.language or "auto",
            output_format=request.output_format
        )
        
        # Post-process segments
        tasks[task_id]["message"] = "Post-processing segments"
        tasks[task_id]["progress"] = 0.8
        
        segments = result.segments
        
        if request.filter_short_segments:
            from ...utils.subtitle import SubtitleProcessor
            segments = SubtitleProcessor.filter_segments(segments)
        
        if request.merge_segments:
            from ...utils.subtitle import SubtitleProcessor
            segments = SubtitleProcessor.merge_segments(segments)
        
        if request.split_long_segments:
            from ...utils.subtitle import SubtitleProcessor
            segments = SubtitleProcessor.split_long_segments(segments)
        
        # Save result
        tasks[task_id]["message"] = "Saving result"
        tasks[task_id]["progress"] = 0.9
        
        output_file = settings.output_dir / f"{task_id}.{request.output_format}"
        
        # Create new result with processed segments
        from ...core.engines.base import TranscriptionResult
        processed_result = TranscriptionResult(
            success=True,
            text=result.text,
            segments=segments,
            language=result.language,
            duration=result.duration,
            model=result.model,
            engine=result.engine,
            output_path=output_file
        )
        
        # Save to file
        from ...utils.subtitle import SubtitleProcessor
        SubtitleProcessor.save_subtitle_file(
            segments=segments,
            file_path=str(output_file),
            format_type=request.output_format
        )
        
        # Complete task
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = "Transcription completed"
        tasks[task_id]["progress"] = 1.0
        tasks[task_id]["result"] = {
            "file_path": str(output_file),
            "download_url": f"/api/v1/download/{task_id}.{request.output_format}",
            "segments": segments,
            "metadata": {
                "language": result.language,
                "duration": result.duration,
                "model": result.model,
                "engine": result.engine,
                "segment_count": len(segments)
            }
        }
        
        # Cleanup temporary files
        if request.url and input_file.exists():
            input_file.unlink()
        
    except Exception as e:
        logger.error(f"Transcription task {task_id} failed: {str(e)}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"Transcription failed: {str(e)}"
        tasks[task_id]["error"] = str(e)


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download transcription result file."""
    file_path = settings.output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )