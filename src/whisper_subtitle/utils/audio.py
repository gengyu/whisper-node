"""Audio processing utilities."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Union

import ffmpeg

from ..config.settings import settings

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Audio processing utilities using FFmpeg."""
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable."""
        # Try common locations
        possible_paths = [
            "ffmpeg",  # In PATH
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",
            str(Path.cwd() / "bin" / "ffmpeg"),
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Found FFmpeg at: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        logger.warning("FFmpeg not found in common locations")
        return None
    
    async def extract_audio(
        self,
        video_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        audio_format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1
    ) -> Path:
        """Extract audio from video file.
        
        Args:
            video_path: Path to input video file
            output_path: Path for output audio file (auto-generated if None)
            audio_format: Output audio format (wav, mp3, flac, etc.)
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels (1=mono, 2=stereo)
        
        Returns:
            Path to extracted audio file
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if output_path is None:
            output_path = settings.temp_dir / f"{video_path.stem}.{audio_format}"
        else:
            output_path = Path(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Extracting audio from {video_path} to {output_path}")
        
        try:
            # Use ffmpeg-python for audio extraction
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream,
                str(output_path),
                acodec='pcm_s16le' if audio_format == 'wav' else 'libmp3lame',
                ar=sample_rate,
                ac=channels,
                loglevel='error'
            )
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            )
            
            if not output_path.exists():
                raise RuntimeError("Audio extraction failed - output file not created")
            
            logger.info(f"Audio extracted successfully: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            error_msg = f"FFmpeg error during audio extraction: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Audio extraction failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def convert_audio(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        target_format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1,
        bitrate: Optional[str] = None
    ) -> Path:
        """Convert audio file to different format.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output audio file
            target_format: Target audio format
            sample_rate: Target sample rate in Hz
            channels: Number of audio channels
            bitrate: Audio bitrate (e.g., '128k', '320k')
        
        Returns:
            Path to converted audio file
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input audio file not found: {input_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting audio from {input_path} to {output_path}")
        
        try:
            stream = ffmpeg.input(str(input_path))
            
            output_args = {
                'ar': sample_rate,
                'ac': channels,
                'loglevel': 'error'
            }
            
            if target_format == 'wav':
                output_args['acodec'] = 'pcm_s16le'
            elif target_format == 'mp3':
                output_args['acodec'] = 'libmp3lame'
                if bitrate:
                    output_args['audio_bitrate'] = bitrate
            elif target_format == 'flac':
                output_args['acodec'] = 'flac'
            
            stream = ffmpeg.output(stream, str(output_path), **output_args)
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            )
            
            if not output_path.exists():
                raise RuntimeError("Audio conversion failed - output file not created")
            
            logger.info(f"Audio converted successfully: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            error_msg = f"FFmpeg error during audio conversion: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Audio conversion failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def get_audio_info(
        self,
        audio_path: Union[str, Path]
    ) -> dict:
        """Get audio file information.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Dictionary with audio information
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # Use ffprobe to get audio information
            loop = asyncio.get_event_loop()
            probe = await loop.run_in_executor(
                None,
                lambda: ffmpeg.probe(str(audio_path), cmd='ffprobe')
            )
            
            audio_stream = None
            for stream in probe['streams']:
                if stream['codec_type'] == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise RuntimeError("No audio stream found in file")
            
            info = {
                'duration': float(probe['format'].get('duration', 0)),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'codec': audio_stream.get('codec_name', 'unknown'),
                'bitrate': int(audio_stream.get('bit_rate', 0)) if audio_stream.get('bit_rate') else None,
                'format': probe['format'].get('format_name', 'unknown'),
                'size': int(probe['format'].get('size', 0)),
            }
            
            return info
            
        except Exception as e:
            error_msg = f"Failed to get audio info: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def embed_subtitles(
        self,
        video_path: Union[str, Path],
        subtitle_path: Union[str, Path],
        output_path: Union[str, Path],
        subtitle_format: str = "srt"
    ) -> Path:
        """Embed subtitles into video file.
        
        Args:
            video_path: Path to input video file
            subtitle_path: Path to subtitle file
            output_path: Path for output video file
            subtitle_format: Subtitle format (srt, vtt, ass)
        
        Returns:
            Path to output video file
        """
        video_path = Path(video_path)
        subtitle_path = Path(subtitle_path)
        output_path = Path(output_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if not subtitle_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Embedding subtitles from {subtitle_path} into {video_path}")
        
        try:
            video_stream = ffmpeg.input(str(video_path))
            subtitle_stream = ffmpeg.input(str(subtitle_path))
            
            # Embed subtitles
            stream = ffmpeg.output(
                video_stream,
                subtitle_stream,
                str(output_path),
                vcodec='copy',
                acodec='copy',
                scodec='mov_text' if subtitle_format == 'srt' else 'webvtt',
                loglevel='error'
            )
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            )
            
            if not output_path.exists():
                raise RuntimeError("Subtitle embedding failed - output file not created")
            
            logger.info(f"Subtitles embedded successfully: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            error_msg = f"FFmpeg error during subtitle embedding: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Subtitle embedding failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def is_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available."""
        return self.ffmpeg_path is not None