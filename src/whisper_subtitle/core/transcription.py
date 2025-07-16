"""Transcription service for handling speech recognition."""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from datetime import datetime

from ..config.settings import Settings
from .engines.registry import EngineRegistry, registry
from .engines.base import TranscriptionResult

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionRequest:
    """Transcription request data."""
    file_path: Path
    engine: str
    model: Optional[str] = None
    language: str = "auto"
    output_format: str = "srt"
    output_path: Optional[Path] = None
    
    # Post-processing options
    merge_segments: bool = False
    split_segments: bool = False
    filter_segments: bool = False
    min_segment_length: float = 1.0
    max_segment_length: float = 30.0


class TranscriptionService:
    """Service for handling transcription requests."""
    
    def __init__(self, settings: Settings):
        """Initialize the transcription service."""
        self.settings = settings
        self.engine_registry = registry
        
        # Import engines to ensure they are registered
        from . import engines
        
    async def transcribe_file(
        self,
        file_path: Union[str, Path],
        engine: str,
        model: Optional[str] = None,
        language: str = "auto",
        output_format: str = "srt",
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe a single file.
        
        Args:
            file_path: Path to the audio/video file
            engine: Speech recognition engine to use
            model: Model to use (optional)
            language: Language code
            output_format: Output format (srt, vtt, txt)
            output_path: Output file path (optional)
            **kwargs: Additional options
            
        Returns:
            TranscriptionResult with the transcription details
        """
        file_path = Path(file_path)
        
        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Validate engine
        if not self.engine_registry.is_engine_available(engine):
            raise ValueError(f"Engine not available: {engine}")
        
        # Get engine instance
        engine_instance = self.engine_registry.get_engine(engine)
        
        # Set model if not provided
        if model is None:
            engine_config = self.settings.get_engine_config(engine)
            model = engine_config.get("default_model", "base")
        
        # Generate output path if not provided
        if output_path is None:
            output_path = self._generate_output_path(file_path, output_format)
        else:
            output_path = Path(output_path)
        
        # Create transcription request
        request = TranscriptionRequest(
            file_path=file_path,
            engine=engine,
            model=model,
            language=language,
            output_format=output_format,
            output_path=output_path,
            **kwargs
        )
        
        logger.info(f"Starting transcription: {file_path} with {engine}")
        
        try:
            # Perform transcription
            result = await engine_instance.transcribe(
                file_path=file_path,
                model=model,
                language=language,
                output_format=output_format,
                output_path=output_path
            )
            
            # Post-process if needed
            if any([request.merge_segments, request.split_segments, request.filter_segments]):
                result = await self._post_process_result(result, request)
            
            logger.info(f"Transcription completed: {result.output_path}")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    async def transcribe_batch(
        self,
        file_paths: List[Union[str, Path]],
        engine: str,
        model: Optional[str] = None,
        language: str = "auto",
        output_format: str = "srt",
        output_dir: Optional[Union[str, Path]] = None,
        max_concurrent: int = 3,
        **kwargs
    ) -> List[TranscriptionResult]:
        """Transcribe multiple files concurrently.
        
        Args:
            file_paths: List of file paths to transcribe
            engine: Speech recognition engine to use
            model: Model to use (optional)
            language: Language code
            output_format: Output format (srt, vtt, txt)
            output_dir: Output directory (optional)
            max_concurrent: Maximum concurrent transcriptions
            **kwargs: Additional options
            
        Returns:
            List of TranscriptionResult objects
        """
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create semaphore to limit concurrent transcriptions
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def transcribe_single(file_path: Union[str, Path]) -> TranscriptionResult:
            async with semaphore:
                output_path = None
                if output_dir:
                    file_path_obj = Path(file_path)
                    output_path = output_dir / f"{file_path_obj.stem}.{output_format}"
                
                return await self.transcribe_file(
                    file_path=file_path,
                    engine=engine,
                    model=model,
                    language=language,
                    output_format=output_format,
                    output_path=output_path,
                    **kwargs
                )
        
        # Run transcriptions concurrently
        tasks = [transcribe_single(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to transcribe {file_paths[i]}: {result}")
            else:
                successful_results.append(result)
        
        return successful_results
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engines."""
        return self.engine_registry.list_engines()
    
    def get_engine_info(self, engine: str) -> Dict[str, Any]:
        """Get information about a specific engine."""
        return self.engine_registry.get_engine_info(engine)
    
    def get_engine_models(self, engine: str) -> List[str]:
        """Get available models for an engine."""
        return self.settings.get_engine_models(engine)
    
    def get_engine_languages(self, engine: str) -> List[str]:
        """Get supported languages for an engine."""
        return self.settings.get_engine_languages(engine)
    
    def _generate_output_path(self, input_path: Path, output_format: str) -> Path:
        """Generate output file path."""
        output_dir = self.settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{input_path.stem}_{timestamp}.{output_format}"
        
        return output_dir / filename
    
    async def _post_process_result(
        self,
        result: TranscriptionResult,
        request: TranscriptionRequest
    ) -> TranscriptionResult:
        """Post-process transcription result."""
        # This is a placeholder for post-processing logic
        # In a real implementation, you would:
        # 1. Parse the subtitle file
        # 2. Apply merge/split/filter operations
        # 3. Save the processed result
        
        logger.info("Post-processing transcription result")
        
        # For now, just return the original result
        return result
    
    async def cleanup(self):
        """Cleanup resources used by the transcription service."""
        logger.info("Cleaning up transcription service")
        
        # Cleanup engine registry if needed
        if hasattr(self.engine_registry, 'cleanup'):
            await self.engine_registry.cleanup()
        
        # Any other cleanup tasks can be added here
        logger.info("Transcription service cleanup completed")