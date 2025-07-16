"""WhisperKit engine implementation for Apple Silicon."""

import logging
import time
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base import BaseEngine, TranscriptionResult

logger = logging.getLogger(__name__)


class WhisperKitEngine(BaseEngine):
    """WhisperKit engine for Apple Silicon devices."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize WhisperKit engine.
        
        Args:
            config: Engine configuration
        """
        super().__init__(config)
        self._cli_path = self.config.get("cli_path", "whisperkit-cli")
        self._available_models = [
            "tiny", "tiny.en", "base", "base.en", 
            "small", "small.en", "medium", "medium.en",
            "large-v3"
        ]
        self._available_languages = [
            "auto", "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr", "pl",
            "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi", "he", "uk", "el",
            "ms", "cs", "ro", "da", "hu", "ta", "no", "th", "ur", "hr", "bg", "lt"
        ]
    
    def is_available(self) -> bool:
        """Check if WhisperKit CLI is available."""
        try:
            result = subprocess.run(
                [self._cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def get_models(self) -> List[str]:
        """Get list of available models."""
        return self._available_models.copy()
    
    def get_languages(self) -> List[str]:
        """Get list of supported languages."""
        return self._available_languages.copy()
    
    async def transcribe(
        self,
        file_path: Path,
        model: str = "base",
        language: str = "auto",
        output_format: str = "srt",
        output_path: Optional[Path] = None
    ) -> TranscriptionResult:
        """Transcribe audio/video file using WhisperKit.
        
        Args:
            file_path: Path to the input file
            model: Whisper model to use
            language: Language code (auto for auto-detection)
            output_format: Output format (srt, vtt, txt)
            output_path: Path for output file
            
        Returns:
            TranscriptionResult with transcription details
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not file_path.exists():
                raise FileNotFoundError(f"Input file not found: {file_path}")
            
            if model not in self._available_models:
                logger.warning(f"Unknown model {model}, using 'base'")
                model = "base"
            
            # Generate output path if not provided
            if output_path is None:
                output_path = file_path.parent / f"{file_path.stem}.{output_format}"
            
            # Prepare WhisperKit command
            cmd = [
                self._cli_path,
                "transcribe",
                str(file_path),
                "--model", model,
                "--output-format", "json",  # Always get JSON for processing
                "--output-dir", str(output_path.parent)
            ]
            
            # Add language if specified
            if language != "auto":
                cmd.extend(["--language", language])
            
            # Add additional options from config
            if self.config.get("verbose", False):
                cmd.append("--verbose")
            
            if "temperature" in self.config:
                cmd.extend(["--temperature", str(self.config["temperature"])])
            
            if "beam_size" in self.config:
                cmd.extend(["--beam-size", str(self.config["beam_size"])])
            
            logger.info(f"Running WhisperKit command: {' '.join(cmd)}")
            
            # Run WhisperKit CLI
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout", 3600)  # 1 hour default timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"WhisperKit CLI failed: {result.stderr}")
            
            # Parse JSON output
            json_output_path = output_path.parent / f"{file_path.stem}.json"
            
            if not json_output_path.exists():
                # Try to find the JSON file with different naming
                json_files = list(output_path.parent.glob(f"{file_path.stem}*.json"))
                if json_files:
                    json_output_path = json_files[0]
                else:
                    raise FileNotFoundError("WhisperKit JSON output not found")
            
            # Load transcription result
            with open(json_output_path, 'r', encoding='utf-8') as f:
                whisperkit_result = json.load(f)
            
            # Extract segments
            segments = []
            full_text_parts = []
            
            for segment in whisperkit_result.get("segments", []):
                segment_dict = {
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "text": segment.get("text", "").strip()
                }
                segments.append(segment_dict)
                if segment_dict["text"]:
                    full_text_parts.append(segment_dict["text"])
            
            # Format and save output in requested format
            self._format_output(segments, output_format, output_path)
            
            # Get full text
            full_text = " ".join(full_text_parts)
            
            # Clean up JSON file if not needed
            if output_format != "json":
                try:
                    json_output_path.unlink()
                except Exception:
                    pass  # Ignore cleanup errors
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                success=True,
                output_path=output_path,
                text=full_text,
                segments=segments,
                language=whisperkit_result.get("language"),
                duration=whisperkit_result.get("duration"),
                processing_time=processing_time,
                engine=self.name,
                model=model,
                metadata={
                    "whisperkit_version": self._get_version(),
                    "cli_output": result.stdout,
                    "original_result": whisperkit_result
                }
            )
            
        except subprocess.TimeoutExpired:
            processing_time = time.time() - start_time
            error_msg = f"WhisperKit transcription timed out after {self.config.get('timeout', 3600)} seconds"
            logger.error(error_msg)
            
            return TranscriptionResult(
                success=False,
                error=error_msg,
                processing_time=processing_time,
                engine=self.name,
                model=model
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"WhisperKit transcription failed: {e}")
            
            return TranscriptionResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                engine=self.name,
                model=model
            )
    
    def _get_version(self) -> str:
        """Get WhisperKit CLI version.
        
        Returns:
            Version string or 'unknown'
        """
        try:
            result = subprocess.run(
                [self._cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"
    
    def download_model(self, model: str) -> bool:
        """Download a WhisperKit model.
        
        Args:
            model: Model name to download
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [self._cli_path, "download", "--model", model]
            
            logger.info(f"Downloading WhisperKit model: {model}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes for download
            )
            
            if result.returncode == 0:
                logger.info(f"WhisperKit model {model} downloaded successfully")
                return True
            else:
                logger.error(f"Failed to download WhisperKit model {model}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading WhisperKit model {model}: {e}")
            return False
    
    def list_downloaded_models(self) -> List[str]:
        """List downloaded WhisperKit models.
        
        Returns:
            List of downloaded model names
        """
        try:
            result = subprocess.run(
                [self._cli_path, "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse the output to extract model names
                models = []
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and line in self._available_models:
                        models.append(line)
                return models
            
        except Exception as e:
            logger.error(f"Error listing WhisperKit models: {e}")
        
        return []