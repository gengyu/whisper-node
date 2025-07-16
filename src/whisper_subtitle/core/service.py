"""Core service for speech recognition and subtitle generation."""

import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .engines.registry import get_engine, get_available_engines
from .engines.base import TranscriptionResult
from .transcription import TranscriptionService
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class SubtitleService:
    """Main service for subtitle generation."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the subtitle service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or Settings()
        self.transcription_service = TranscriptionService(self.settings)
        
        # Ensure directories exist
        self.settings.ensure_directories()
    
    async def transcribe_file(
        self,
        file_path: Path,
        engine: Optional[str] = None,
        model: Optional[str] = None,
        language: str = "auto",
        output_format: str = "srt",
        output_path: Optional[Path] = None
    ) -> TranscriptionResult:
        """Transcribe a single file.
        
        Args:
            file_path: Path to the input file
            engine: Engine name (defaults to configured default)
            model: Model name (defaults to configured default)
            language: Language code
            output_format: Output format (srt, vtt, txt)
            output_path: Custom output path
            
        Returns:
            TranscriptionResult
        """
        # Use defaults from settings
        engine = engine or self.settings.default_engine
        model = model or self.settings.default_model
        
        logger.info(f"Starting transcription: {file_path} with {engine}/{model}")
        
        try:
            result = await self.transcription_service.transcribe_file(
                file_path=file_path,
                engine=engine,
                model=model,
                language=language,
                output_format=output_format,
                output_path=output_path
            )
            
            if result.success:
                logger.info(f"Transcription completed: {result.output_path}")
            else:
                logger.error(f"Transcription failed: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return TranscriptionResult(
                success=False,
                error=str(e),
                engine=engine,
                model=model
            )
    
    async def transcribe_batch(
        self,
        file_paths: List[Path],
        engine: Optional[str] = None,
        model: Optional[str] = None,
        language: str = "auto",
        output_format: str = "srt",
        max_concurrent: Optional[int] = None
    ) -> List[TranscriptionResult]:
        """Transcribe multiple files concurrently.
        
        Args:
            file_paths: List of input file paths
            engine: Engine name
            model: Model name
            language: Language code
            output_format: Output format
            max_concurrent: Maximum concurrent tasks
            
        Returns:
            List of TranscriptionResults
        """
        max_concurrent = max_concurrent or self.settings.max_concurrent_tasks
        
        logger.info(f"Starting batch transcription: {len(file_paths)} files")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def transcribe_with_semaphore(file_path: Path) -> TranscriptionResult:
            async with semaphore:
                return await self.transcribe_file(
                    file_path=file_path,
                    engine=engine,
                    model=model,
                    language=language,
                    output_format=output_format
                )
        
        tasks = [transcribe_with_semaphore(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(TranscriptionResult(
                    success=False,
                    error=str(result),
                    engine=engine,
                    model=model
                ))
            else:
                processed_results.append(result)
        
        successful = sum(1 for r in processed_results if r.success)
        logger.info(f"Batch transcription completed: {successful}/{len(file_paths)} successful")
        
        return processed_results
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engines.
        
        Returns:
            List of available engine names
        """
        return get_available_engines()
    
    def get_engine_info(self, engine_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific engine.
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            Engine information dict or None
        """
        engine = get_engine(engine_name)
        return engine.get_info() if engine else None
    
    def get_all_engines_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all engines.
        
        Returns:
            Dict mapping engine names to their info
        """
        from .engines.registry import registry
        return registry.get_all_engines_info()
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate if a file can be processed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is valid, False otherwise
        """
        if not file_path.exists():
            return False
        
        if not file_path.is_file():
            return False
        
        # Check file size
        if file_path.stat().st_size > self.settings.max_file_size:
            return False
        
        # Check file extension
        if file_path.suffix.lower() not in self.settings.allowed_extensions:
            return False
        
        return True
    
    def get_output_path(
        self,
        input_path: Path,
        output_format: str = "srt",
        custom_path: Optional[Path] = None
    ) -> Path:
        """Generate output path for transcription result.
        
        Args:
            input_path: Input file path
            output_format: Output format
            custom_path: Custom output path
            
        Returns:
            Output file path
        """
        if custom_path:
            return custom_path
        
        # Generate default output path
        output_dir = self.settings.output_dir
        filename = input_path.stem + f".{output_format}"
        
        return output_dir / filename
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of files cleaned up
        """
        temp_dir = self.settings.temp_dir
        if not temp_dir.exists():
            return 0
        
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        cleaned_count = 0
        
        for file_path in temp_dir.rglob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {file_path}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} temporary files")
        return cleaned_count