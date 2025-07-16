"""FastAPI main application."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from ..config.settings import settings
from ..core.service import TranscriptionService
from ..tasks.scheduler import TaskScheduler
from ..tasks.youtube_fetcher import YouTubeFetcher
from .routes import transcription, upload, models, youtube

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Whisper Subtitle Generator API")
    
    # Ensure required directories exist
    settings.ensure_directories()
    Path("downloads").mkdir(parents=True, exist_ok=True)
    
    # Initialize transcription service
    transcription_service = TranscriptionService(settings)
    app.state.transcription_service = transcription_service
    
    # Initialize task scheduler
    scheduler = TaskScheduler()
    await scheduler.start()
    app.state.scheduler = scheduler
    
    # Initialize YouTube fetcher
    youtube_fetcher = YouTubeFetcher(
        scheduler=scheduler,
        transcription_service=transcription_service,
        download_dir="downloads",
        check_interval=timedelta(hours=1)
    )
    app.state.youtube_fetcher = youtube_fetcher
    
    # Schedule cleanup tasks
    await scheduler.schedule_daily_task(
        task_id="cleanup_old_tasks",
        name="Clean up old tasks",
        func=scheduler.cleanup_old_tasks,
        hour=2,  # Run at 2 AM
        minute=0
    )
    
    await scheduler.schedule_daily_task(
        task_id="cleanup_old_files",
        name="Clean up old downloaded files",
        func=youtube_fetcher.cleanup_old_files,
        hour=3,  # Run at 3 AM
        minute=0
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down Whisper Subtitle Generator API")
    
    if hasattr(app.state, 'scheduler'):
        await app.state.scheduler.stop()
    
    # Cleanup transcription service
    if hasattr(app.state, 'transcription_service'):
        await app.state.transcription_service.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Whisper Subtitle Generator",
    description="Video speech recognition with automatic subtitling and LLM translation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(transcription.router, prefix="/api/v1", tags=["transcription"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(models.router, prefix="/api/v1", tags=["models"])
app.include_router(youtube.router, prefix="/api/v1", tags=["youtube"])

# Serve static files (web frontend)
static_dir = Path(__file__).parent.parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve web frontend
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    @app.get("/")
    async def serve_frontend():
        """Serve the web frontend."""
        index_file = web_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        else:
            return {"message": "Whisper Subtitle Generator API", "version": "1.0.0"}
else:
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Whisper Subtitle Generator API",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc"
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/health")
async def api_health_check():
    """API health check endpoint."""
    from datetime import datetime
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/info")
async def api_info():
    """API information endpoint."""
    transcription_service = app.state.transcription_service
    available_engines = await transcription_service.get_available_engines()
    
    scheduler_status = {}
    youtube_status = {}
    
    if hasattr(app.state, 'scheduler'):
        tasks = await app.state.scheduler.list_tasks(limit=100)
        scheduler_status = {
            "running": app.state.scheduler.running,
            "total_tasks": len(tasks),
            "pending_tasks": len([t for t in tasks if t.status.value == "pending"]),
            "running_tasks": len([t for t in tasks if t.status.value == "running"]),
            "completed_tasks": len([t for t in tasks if t.status.value == "completed"]),
            "failed_tasks": len([t for t in tasks if t.status.value == "failed"])
        }
    
    if hasattr(app.state, 'youtube_fetcher'):
        youtube_status = await app.state.youtube_fetcher.get_processing_status()
    
    return {
        "name": "Whisper Subtitle Generator",
        "version": "1.0.0",
        "description": "Video speech recognition with automatic subtitling and LLM translation",
        "available_engines": available_engines,
        "supported_formats": {
            "audio": ["mp3", "wav", "flac", "m4a", "ogg"],
            "video": ["mp4", "avi", "mov", "mkv", "webm"],
            "subtitle": ["srt", "vtt", "txt", "json"]
        },
        "max_file_size": settings.max_file_size,
        "temp_dir": str(settings.temp_dir),
        "output_dir": str(settings.output_dir),
        "features": {
            "task_scheduling": True,
            "youtube_monitoring": True,
            "automatic_transcription": True,
            "batch_processing": True
        },
        "scheduler_status": scheduler_status,
        "youtube_status": youtube_status
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "whisper_subtitle.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )