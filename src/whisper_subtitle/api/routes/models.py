"""Models management API routes."""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class EngineInfo(BaseModel):
    """Engine information model."""
    name: str
    display_name: str
    description: str
    available: bool
    platform_supported: bool
    models: List[str]
    languages: List[str]
    default_model: Optional[str] = None
    requirements: List[str] = []
    status: str = "unknown"


class ModelInfo(BaseModel):
    """Model information model."""
    name: str
    engine: str
    size: Optional[str] = None
    languages: List[str] = []
    description: Optional[str] = None
    downloaded: bool = False
    download_url: Optional[str] = None
    file_path: Optional[str] = None


class ModelDownloadRequest(BaseModel):
    """Model download request model."""
    engine: str
    model: str
    force: bool = False


class ModelDownloadResponse(BaseModel):
    """Model download response model."""
    task_id: str
    status: str
    message: str
    engine: str
    model: str


@router.get("/engines", response_model=List[EngineInfo])
async def get_engines(request: Request):
    """Get available speech recognition engines."""
    try:
        transcription_service = request.app.state.transcription_service
        available_engines = await transcription_service.get_available_engines()
        
        engines_info = []
        
        for engine_name, engine_instance in available_engines.items():
            try:
                # Get engine information
                is_ready = await engine_instance.is_ready()
                models = await engine_instance.get_available_models()
                languages = await engine_instance.get_supported_languages()
                
                # Determine engine display info
                engine_info = {
                    "openai_whisper": {
                        "display_name": "OpenAI Whisper",
                        "description": "OpenAI's Whisper model for speech recognition",
                        "requirements": ["torch", "whisper"]
                    },
                    "faster_whisper": {
                        "display_name": "Faster Whisper",
                        "description": "Optimized Whisper implementation using CTranslate2",
                        "requirements": ["faster-whisper"]
                    },
                    "whisperkit": {
                        "display_name": "WhisperKit",
                        "description": "Apple's WhisperKit for macOS and iOS",
                        "requirements": ["macOS", "Apple Silicon"]
                    },
                    "whispercpp": {
                        "display_name": "Whisper.cpp",
                        "description": "C++ implementation of Whisper",
                        "requirements": ["C++ compiler"]
                    },
                    "alibaba_asr": {
                        "display_name": "Alibaba Cloud ASR",
                        "description": "Alibaba Cloud's speech recognition service",
                        "requirements": ["API credentials"]
                    }
                }.get(engine_name, {
                    "display_name": engine_name.title(),
                    "description": f"{engine_name} speech recognition engine",
                    "requirements": []
                })
                
                engines_info.append(EngineInfo(
                    name=engine_name,
                    display_name=engine_info["display_name"],
                    description=engine_info["description"],
                    available=is_ready,
                    platform_supported=True,  # If it's in available_engines, it's supported
                    models=models,
                    languages=languages,
                    default_model=models[0] if models else None,
                    requirements=engine_info["requirements"],
                    status="ready" if is_ready else "not_ready"
                ))
                
            except Exception as e:
                logger.error(f"Failed to get info for engine {engine_name}: {str(e)}")
                engines_info.append(EngineInfo(
                    name=engine_name,
                    display_name=engine_name.title(),
                    description=f"{engine_name} speech recognition engine",
                    available=False,
                    platform_supported=True,
                    models=[],
                    languages=[],
                    status="error"
                ))
        
        return engines_info
        
    except Exception as e:
        logger.error(f"Failed to get engines: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engines/{engine_name}", response_model=EngineInfo)
async def get_engine_info(engine_name: str, request: Request):
    """Get information about a specific engine."""
    try:
        transcription_service = request.app.state.transcription_service
        available_engines = await transcription_service.get_available_engines()
        
        if engine_name not in available_engines:
            raise HTTPException(status_code=404, detail=f"Engine '{engine_name}' not found")
        
        engine_instance = available_engines[engine_name]
        
        # Get engine information
        is_ready = await engine_instance.is_ready()
        models = await engine_instance.get_available_models()
        languages = await engine_instance.get_supported_languages()
        
        # Engine display info
        engine_info = {
            "openai_whisper": {
                "display_name": "OpenAI Whisper",
                "description": "OpenAI's Whisper model for speech recognition",
                "requirements": ["torch", "whisper"]
            },
            "faster_whisper": {
                "display_name": "Faster Whisper",
                "description": "Optimized Whisper implementation using CTranslate2",
                "requirements": ["faster-whisper"]
            },
            "whisperkit": {
                "display_name": "WhisperKit",
                "description": "Apple's WhisperKit for macOS and iOS",
                "requirements": ["macOS", "Apple Silicon"]
            },
            "whispercpp": {
                "display_name": "Whisper.cpp",
                "description": "C++ implementation of Whisper",
                "requirements": ["C++ compiler"]
            },
            "alibaba_asr": {
                "display_name": "Alibaba Cloud ASR",
                "description": "Alibaba Cloud's speech recognition service",
                "requirements": ["API credentials"]
            }
        }.get(engine_name, {
            "display_name": engine_name.title(),
            "description": f"{engine_name} speech recognition engine",
            "requirements": []
        })
        
        return EngineInfo(
            name=engine_name,
            display_name=engine_info["display_name"],
            description=engine_info["description"],
            available=is_ready,
            platform_supported=True,
            models=models,
            languages=languages,
            default_model=models[0] if models else None,
            requirements=engine_info["requirements"],
            status="ready" if is_ready else "not_ready"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get engine info for {engine_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=List[ModelInfo])
async def get_models(engine: Optional[str] = None, request: Request = None):
    """Get available models for all engines or a specific engine."""
    try:
        transcription_service = request.app.state.transcription_service
        available_engines = await transcription_service.get_available_engines()
        
        models_info = []
        
        # Filter engines if specific engine requested
        engines_to_check = {engine: available_engines[engine]} if engine and engine in available_engines else available_engines
        
        for engine_name, engine_instance in engines_to_check.items():
            try:
                models = await engine_instance.get_available_models()
                languages = await engine_instance.get_supported_languages()
                
                for model_name in models:
                    # Try to get model-specific information
                    model_info = {
                        "name": model_name,
                        "engine": engine_name,
                        "languages": languages,
                        "downloaded": True,  # Assume downloaded if in available models
                        "description": f"{model_name} model for {engine_name}"
                    }
                    
                    # Add engine-specific model information
                    if engine_name in ["openai_whisper", "faster_whisper"]:
                        size_info = {
                            "tiny": "39 MB",
                            "base": "74 MB",
                            "small": "244 MB",
                            "medium": "769 MB",
                            "large": "1550 MB",
                            "large-v2": "1550 MB",
                            "large-v3": "1550 MB"
                        }
                        model_info["size"] = size_info.get(model_name, "Unknown")
                    
                    models_info.append(ModelInfo(**model_info))
                    
            except Exception as e:
                logger.error(f"Failed to get models for engine {engine_name}: {str(e)}")
                continue
        
        return models_info
        
    except Exception as e:
        logger.error(f"Failed to get models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/download", response_model=ModelDownloadResponse)
async def download_model(
    request_data: ModelDownloadRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """Download a model for a specific engine."""
    try:
        transcription_service = request.app.state.transcription_service
        available_engines = await transcription_service.get_available_engines()
        
        if request_data.engine not in available_engines:
            raise HTTPException(
                status_code=404,
                detail=f"Engine '{request_data.engine}' not found"
            )
        
        engine_instance = available_engines[request_data.engine]
        
        # Check if model is already available
        available_models = await engine_instance.get_available_models()
        if request_data.model in available_models and not request_data.force:
            return ModelDownloadResponse(
                task_id="",
                status="already_downloaded",
                message=f"Model '{request_data.model}' is already available",
                engine=request_data.engine,
                model=request_data.model
            )
        
        # Generate task ID for tracking
        import uuid
        task_id = str(uuid.uuid4())
        
        # Start download in background
        background_tasks.add_task(
            _download_model_task,
            task_id,
            request_data.engine,
            request_data.model,
            engine_instance
        )
        
        return ModelDownloadResponse(
            task_id=task_id,
            status="downloading",
            message=f"Started downloading model '{request_data.model}' for engine '{request_data.engine}'",
            engine=request_data.engine,
            model=request_data.model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start model download: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages")
async def get_supported_languages(engine: Optional[str] = None, request: Request = None):
    """Get supported languages for all engines or a specific engine."""
    try:
        transcription_service = request.app.state.transcription_service
        available_engines = await transcription_service.get_available_engines()
        
        languages_info = {}
        
        # Filter engines if specific engine requested
        engines_to_check = {engine: available_engines[engine]} if engine and engine in available_engines else available_engines
        
        for engine_name, engine_instance in engines_to_check.items():
            try:
                languages = await engine_instance.get_supported_languages()
                languages_info[engine_name] = languages
            except Exception as e:
                logger.error(f"Failed to get languages for engine {engine_name}: {str(e)}")
                languages_info[engine_name] = []
        
        # If specific engine requested, return just that engine's languages
        if engine and engine in languages_info:
            return {"languages": languages_info[engine]}
        
        return {"engines": languages_info}
        
    except Exception as e:
        logger.error(f"Failed to get supported languages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_models_status(request: Request):
    """Get overall status of models and engines."""
    try:
        transcription_service = request.app.state.transcription_service
        available_engines = await transcription_service.get_available_engines()
        
        status_info = {
            "total_engines": len(available_engines),
            "ready_engines": 0,
            "total_models": 0,
            "engines_status": {}
        }
        
        for engine_name, engine_instance in available_engines.items():
            try:
                is_ready = await engine_instance.is_ready()
                models = await engine_instance.get_available_models()
                
                if is_ready:
                    status_info["ready_engines"] += 1
                
                status_info["total_models"] += len(models)
                status_info["engines_status"][engine_name] = {
                    "ready": is_ready,
                    "models_count": len(models),
                    "models": models
                }
                
            except Exception as e:
                logger.error(f"Failed to get status for engine {engine_name}: {str(e)}")
                status_info["engines_status"][engine_name] = {
                    "ready": False,
                    "models_count": 0,
                    "models": [],
                    "error": str(e)
                }
        
        return status_info
        
    except Exception as e:
        logger.error(f"Failed to get models status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _download_model_task(
    task_id: str,
    engine_name: str,
    model_name: str,
    engine_instance
):
    """Background task to download model."""
    try:
        logger.info(f"Starting model download: {engine_name}/{model_name} (task: {task_id})")
        
        # This is a placeholder - actual implementation would depend on the engine
        # For now, we'll just simulate a download
        import asyncio
        await asyncio.sleep(5)  # Simulate download time
        
        logger.info(f"Model download completed: {engine_name}/{model_name} (task: {task_id})")
        
    except Exception as e:
        logger.error(f"Model download failed: {engine_name}/{model_name} (task: {task_id}): {str(e)}")