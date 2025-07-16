"""Subtitle processing utilities."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SubtitleProcessor:
    """Subtitle processing and format conversion utilities."""
    
    @staticmethod
    def parse_srt(content: str) -> List[Dict]:
        """Parse SRT subtitle content.
        
        Args:
            content: SRT file content
        
        Returns:
            List of subtitle segments
        """
        segments = []
        
        # Split by double newlines to get individual subtitle blocks
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            try:
                # Parse sequence number
                seq_num = int(lines[0].strip())
                
                # Parse timestamp
                timestamp_line = lines[1].strip()
                start_time, end_time = timestamp_line.split(' --> ')
                
                # Parse text (remaining lines)
                text = '\n'.join(lines[2:]).strip()
                
                segments.append({
                    'sequence': seq_num,
                    'start': SubtitleProcessor._parse_srt_timestamp(start_time),
                    'end': SubtitleProcessor._parse_srt_timestamp(end_time),
                    'text': text
                })
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse SRT block: {block[:50]}... Error: {e}")
                continue
        
        return segments
    
    @staticmethod
    def _parse_srt_timestamp(timestamp: str) -> float:
        """Parse SRT timestamp to seconds.
        
        Args:
            timestamp: Timestamp in format HH:MM:SS,mmm
        
        Returns:
            Time in seconds
        """
        # Format: HH:MM:SS,mmm
        time_part, ms_part = timestamp.split(',')
        hours, minutes, seconds = map(int, time_part.split(':'))
        milliseconds = int(ms_part)
        
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
        return total_seconds
    
    @staticmethod
    def parse_vtt(content: str) -> List[Dict]:
        """Parse WebVTT subtitle content.
        
        Args:
            content: VTT file content
        
        Returns:
            List of subtitle segments
        """
        segments = []
        
        # Remove WEBVTT header and split by double newlines
        content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.MULTILINE | re.DOTALL)
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for i, block in enumerate(blocks):
            lines = block.strip().split('\n')
            if len(lines) < 2:
                continue
            
            try:
                # Check if first line is a cue identifier (optional)
                if '-->' in lines[0]:
                    timestamp_line = lines[0]
                    text_lines = lines[1:]
                else:
                    timestamp_line = lines[1]
                    text_lines = lines[2:]
                
                # Parse timestamp
                start_time, end_time = timestamp_line.split(' --> ')
                
                # Parse text
                text = '\n'.join(text_lines).strip()
                
                segments.append({
                    'sequence': i + 1,
                    'start': SubtitleProcessor._parse_vtt_timestamp(start_time),
                    'end': SubtitleProcessor._parse_vtt_timestamp(end_time),
                    'text': text
                })
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse VTT block: {block[:50]}... Error: {e}")
                continue
        
        return segments
    
    @staticmethod
    def _parse_vtt_timestamp(timestamp: str) -> float:
        """Parse WebVTT timestamp to seconds.
        
        Args:
            timestamp: Timestamp in format MM:SS.mmm or HH:MM:SS.mmm
        
        Returns:
            Time in seconds
        """
        # Remove any extra spaces and settings
        timestamp = timestamp.strip().split()[0]
        
        # Format: MM:SS.mmm or HH:MM:SS.mmm
        if '.' in timestamp:
            time_part, ms_part = timestamp.split('.')
            milliseconds = int(ms_part)
        else:
            time_part = timestamp
            milliseconds = 0
        
        time_components = list(map(int, time_part.split(':')))
        
        if len(time_components) == 2:  # MM:SS
            minutes, seconds = time_components
            hours = 0
        elif len(time_components) == 3:  # HH:MM:SS
            hours, minutes, seconds = time_components
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp}")
        
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
        return total_seconds
    
    @staticmethod
    def segments_to_srt(segments: List[Dict]) -> str:
        """Convert segments to SRT format.
        
        Args:
            segments: List of subtitle segments
        
        Returns:
            SRT formatted string
        """
        srt_content = []
        
        for i, segment in enumerate(segments, 1):
            start_time = SubtitleProcessor._seconds_to_srt_timestamp(segment['start'])
            end_time = SubtitleProcessor._seconds_to_srt_timestamp(segment['end'])
            text = segment['text']
            
            srt_content.append(f"{i}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(text)
            srt_content.append("")  # Empty line between segments
        
        return '\n'.join(srt_content)
    
    @staticmethod
    def _seconds_to_srt_timestamp(seconds: float) -> str:
        """Convert seconds to SRT timestamp format.
        
        Args:
            seconds: Time in seconds
        
        Returns:
            Timestamp in format HH:MM:SS,mmm
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    @staticmethod
    def segments_to_vtt(segments: List[Dict]) -> str:
        """Convert segments to WebVTT format.
        
        Args:
            segments: List of subtitle segments
        
        Returns:
            WebVTT formatted string
        """
        vtt_content = ["WEBVTT", ""]
        
        for segment in segments:
            start_time = SubtitleProcessor._seconds_to_vtt_timestamp(segment['start'])
            end_time = SubtitleProcessor._seconds_to_vtt_timestamp(segment['end'])
            text = segment['text']
            
            vtt_content.append(f"{start_time} --> {end_time}")
            vtt_content.append(text)
            vtt_content.append("")  # Empty line between segments
        
        return '\n'.join(vtt_content)
    
    @staticmethod
    def _seconds_to_vtt_timestamp(seconds: float) -> str:
        """Convert seconds to WebVTT timestamp format.
        
        Args:
            seconds: Time in seconds
        
        Returns:
            Timestamp in format MM:SS.mmm or HH:MM:SS.mmm
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
        else:
            return f"{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    
    @staticmethod
    def segments_to_txt(segments: List[Dict]) -> str:
        """Convert segments to plain text format.
        
        Args:
            segments: List of subtitle segments
        
        Returns:
            Plain text string
        """
        return '\n'.join(segment['text'] for segment in segments)
    
    @staticmethod
    def merge_segments(
        segments: List[Dict],
        max_duration: float = 10.0,
        max_chars: int = 200
    ) -> List[Dict]:
        """Merge short segments together.
        
        Args:
            segments: List of subtitle segments
            max_duration: Maximum duration for merged segments
            max_chars: Maximum characters for merged segments
        
        Returns:
            List of merged segments
        """
        if not segments:
            return []
        
        merged = []
        current_segment = segments[0].copy()
        
        for next_segment in segments[1:]:
            # Check if we can merge with current segment
            merged_text = current_segment['text'] + ' ' + next_segment['text']
            merged_duration = next_segment['end'] - current_segment['start']
            
            if (len(merged_text) <= max_chars and 
                merged_duration <= max_duration and
                next_segment['start'] - current_segment['end'] <= 1.0):  # Gap <= 1 second
                
                # Merge segments
                current_segment['end'] = next_segment['end']
                current_segment['text'] = merged_text
            else:
                # Can't merge, add current segment and start new one
                merged.append(current_segment)
                current_segment = next_segment.copy()
        
        # Add the last segment
        merged.append(current_segment)
        
        # Update sequence numbers
        for i, segment in enumerate(merged, 1):
            segment['sequence'] = i
        
        return merged
    
    @staticmethod
    def split_long_segments(
        segments: List[Dict],
        max_duration: float = 5.0,
        max_chars: int = 100
    ) -> List[Dict]:
        """Split long segments into shorter ones.
        
        Args:
            segments: List of subtitle segments
            max_duration: Maximum duration for segments
            max_chars: Maximum characters for segments
        
        Returns:
            List of split segments
        """
        split_segments = []
        
        for segment in segments:
            duration = segment['end'] - segment['start']
            text = segment['text']
            
            # Check if segment needs splitting
            if duration <= max_duration and len(text) <= max_chars:
                split_segments.append(segment)
                continue
            
            # Split by sentences first
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) <= 1:
                # Can't split by sentences, split by words
                words = text.split()
                sentences = []
                current_sentence = []
                
                for word in words:
                    current_sentence.append(word)
                    if len(' '.join(current_sentence)) >= max_chars // 2:
                        sentences.append(' '.join(current_sentence))
                        current_sentence = []
                
                if current_sentence:
                    sentences.append(' '.join(current_sentence))
            
            # Create sub-segments
            time_per_char = duration / len(text) if text else 0
            current_start = segment['start']
            
            for sentence in sentences:
                sentence_duration = len(sentence) * time_per_char
                sentence_end = min(current_start + sentence_duration, segment['end'])
                
                split_segments.append({
                    'sequence': len(split_segments) + 1,
                    'start': current_start,
                    'end': sentence_end,
                    'text': sentence
                })
                
                current_start = sentence_end
        
        # Update sequence numbers
        for i, segment in enumerate(split_segments, 1):
            segment['sequence'] = i
        
        return split_segments
    
    @staticmethod
    def filter_segments(
        segments: List[Dict],
        min_duration: float = 0.1,
        min_chars: int = 1
    ) -> List[Dict]:
        """Filter out segments that are too short.
        
        Args:
            segments: List of subtitle segments
            min_duration: Minimum duration in seconds
            min_chars: Minimum number of characters
        
        Returns:
            Filtered list of segments
        """
        filtered = []
        
        for segment in segments:
            duration = segment['end'] - segment['start']
            text = segment['text'].strip()
            
            if duration >= min_duration and len(text) >= min_chars:
                filtered.append(segment)
        
        # Update sequence numbers
        for i, segment in enumerate(filtered, 1):
            segment['sequence'] = i
        
        return filtered
    
    @staticmethod
    def load_subtitle_file(file_path: Union[str, Path]) -> List[Dict]:
        """Load subtitle file and parse it.
        
        Args:
            file_path: Path to subtitle file
        
        Returns:
            List of subtitle segments
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Determine format by extension
            if file_path.suffix.lower() == '.srt':
                return SubtitleProcessor.parse_srt(content)
            elif file_path.suffix.lower() in ['.vtt', '.webvtt']:
                return SubtitleProcessor.parse_vtt(content)
            else:
                # Try to auto-detect format
                if content.strip().startswith('WEBVTT'):
                    return SubtitleProcessor.parse_vtt(content)
                else:
                    return SubtitleProcessor.parse_srt(content)
        
        except Exception as e:
            logger.error(f"Failed to load subtitle file {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def save_subtitle_file(
        segments: List[Dict],
        file_path: Union[str, Path],
        format_type: str = 'srt'
    ) -> None:
        """Save segments to subtitle file.
        
        Args:
            segments: List of subtitle segments
            file_path: Output file path
            format_type: Output format ('srt', 'vtt', 'txt')
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format_type.lower() == 'srt':
                content = SubtitleProcessor.segments_to_srt(segments)
            elif format_type.lower() in ['vtt', 'webvtt']:
                content = SubtitleProcessor.segments_to_vtt(segments)
            elif format_type.lower() == 'txt':
                content = SubtitleProcessor.segments_to_txt(segments)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Subtitle file saved: {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to save subtitle file {file_path}: {str(e)}")
            raise