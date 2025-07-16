"""File upload API routes."""

import logging
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ...config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class UploadResponse(BaseModel):
    """File upload response model."""
    file_id: str
    filename: str
    file_path: str
    file_size: int
    content_type: str
    message: str


class FileInfo(BaseModel):
    """File information model."""
    file_id: str
    filename: str
    file_path: str
    file_size: int
    content_type: str
    upload_time: str


# Supported file extensions
SUPPORTED_AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac', '.wma'
}

SUPPORTED_VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'
}

SUPPORTED_EXTENSIONS = SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    # Check file size
    if hasattr(file, 'size') and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size // (1024*1024)}MB"
        )
    
    # Check file extension
    if file.filename:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
    
    # Check content type
    if file.content_type:
        if not (file.content_type.startswith('audio/') or 
                file.content_type.startswith('video/') or
                file.content_type == 'application/octet-stream'):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {file.content_type}"
            )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: str = Form(None)
):
    """Upload audio or video file for transcription."""
    try:
        # Validate file
        validate_file(file)
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Determine file extension
        if file.filename:
            original_ext = Path(file.filename).suffix.lower()
        else:
            # Try to determine from content type
            if file.content_type:
                if 'mp4' in file.content_type:
                    original_ext = '.mp4'
                elif 'mp3' in file.content_type:
                    original_ext = '.mp3'
                elif 'wav' in file.content_type:
                    original_ext = '.wav'
                else:
                    original_ext = '.bin'
            else:
                original_ext = '.bin'
        
        # Create upload directory
        upload_dir = settings.upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / f"{file_id}{original_ext}"
        
        # Read and save file content
        content = await file.read()
        
        # Check actual file size
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_file_size // (1024*1024)}MB"
            )
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"File uploaded successfully: {file_path}")
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename or f"upload{original_ext}",
            file_path=str(file_path),
            file_size=len(content),
            content_type=file.content_type or "application/octet-stream",
            message="File uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload/multiple", response_model=List[UploadResponse])
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    description: str = Form(None)
):
    """Upload multiple audio or video files for transcription."""
    if len(files) > 10:  # Limit number of files
        raise HTTPException(
            status_code=400,
            detail="Too many files. Maximum 10 files per upload."
        )
    
    results = []
    
    for file in files:
        try:
            # Validate file
            validate_file(file)
            
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Determine file extension
            if file.filename:
                original_ext = Path(file.filename).suffix.lower()
            else:
                original_ext = '.bin'
            
            # Create upload directory
            upload_dir = settings.upload_dir
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = upload_dir / f"{file_id}{original_ext}"
            
            # Read and save file content
            content = await file.read()
            
            # Check actual file size
            if len(content) > settings.max_file_size:
                results.append(UploadResponse(
                    file_id="",
                    filename=file.filename or "unknown",
                    file_path="",
                    file_size=len(content),
                    content_type=file.content_type or "application/octet-stream",
                    message=f"File too large. Maximum size: {settings.max_file_size // (1024*1024)}MB"
                ))
                continue
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            results.append(UploadResponse(
                file_id=file_id,
                filename=file.filename or f"upload{original_ext}",
                file_path=str(file_path),
                file_size=len(content),
                content_type=file.content_type or "application/octet-stream",
                message="File uploaded successfully"
            ))
            
        except Exception as e:
            logger.error(f"Failed to upload file {file.filename}: {str(e)}")
            results.append(UploadResponse(
                file_id="",
                filename=file.filename or "unknown",
                file_path="",
                file_size=0,
                content_type=file.content_type or "application/octet-stream",
                message=f"Upload failed: {str(e)}"
            ))
    
    return results


@router.get("/upload/{file_id}", response_model=FileInfo)
async def get_file_info(file_id: str):
    """Get information about uploaded file."""
    # Find file in upload directory
    upload_dir = settings.upload_dir
    
    # Look for file with any supported extension
    file_path = None
    for ext in SUPPORTED_EXTENSIONS:
        potential_path = upload_dir / f"{file_id}{ext}"
        if potential_path.exists():
            file_path = potential_path
            break
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get file stats
    stat = file_path.stat()
    
    return FileInfo(
        file_id=file_id,
        filename=file_path.name,
        file_path=str(file_path),
        file_size=stat.st_size,
        content_type="application/octet-stream",  # Could be improved with file type detection
        upload_time=str(stat.st_mtime)
    )


@router.delete("/upload/{file_id}")
async def delete_file(file_id: str):
    """Delete uploaded file."""
    # Find file in upload directory
    upload_dir = settings.upload_dir
    
    # Look for file with any supported extension
    file_path = None
    for ext in SUPPORTED_EXTENSIONS:
        potential_path = upload_dir / f"{file_id}{ext}"
        if potential_path.exists():
            file_path = potential_path
            break
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        logger.info(f"File deleted: {file_path}")
        return {"message": "File deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.get("/upload")
async def list_uploaded_files(limit: int = 50, offset: int = 0):
    """List uploaded files."""
    upload_dir = settings.upload_dir
    
    if not upload_dir.exists():
        return {"files": [], "total": 0}
    
    # Get all files in upload directory
    files = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            stat = file_path.stat()
            
            # Extract file ID from filename
            file_id = file_path.stem
            
            files.append({
                "file_id": file_id,
                "filename": file_path.name,
                "file_path": str(file_path),
                "file_size": stat.st_size,
                "upload_time": stat.st_mtime
            })
    
    # Sort by upload time (most recent first)
    files.sort(key=lambda x: x["upload_time"], reverse=True)
    
    # Apply pagination
    total = len(files)
    files = files[offset:offset + limit]
    
    return {
        "files": files,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/upload/supported-formats")
async def get_supported_formats():
    """Get supported file formats."""
    return {
        "audio_formats": sorted(list(SUPPORTED_AUDIO_EXTENSIONS)),
        "video_formats": sorted(list(SUPPORTED_VIDEO_EXTENSIONS)),
        "all_formats": sorted(list(SUPPORTED_EXTENSIONS)),
        "max_file_size": settings.max_file_size,
        "max_file_size_mb": settings.max_file_size // (1024 * 1024)
    }