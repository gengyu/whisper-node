"""Translation service using Alibaba Cloud AI."""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json
import re

try:
    from alibabacloud_mt20181012.client import Client as AlibabaTranslateClient
    from alibabacloud_mt20181012 import models as mt_models
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models
except ImportError:
    AlibabaTranslateClient = None
    mt_models = None
    open_api_models = None
    util_models = None

logger = logging.getLogger(__name__)


@dataclass
class TranslationConfig:
    """Configuration for translation service."""
    access_key_id: str
    access_key_secret: str
    endpoint: str = "mt.cn-hangzhou.aliyuncs.com"
    region: str = "cn-hangzhou"
    region_id: str = "cn-hangzhou"
    

@dataclass
class SubtitleEntry:
    """Subtitle entry with timing information."""
    start_time: str
    end_time: str
    text: str
    index: int
    
    
class TranslationService:
    """Translation service using Alibaba Cloud AI."""
    
    def __init__(self, config: Optional[TranslationConfig] = None):
        """Initialize translation service.
        
        Args:
            config: Translation configuration. If None, will try to load from environment.
        """
        self.config = config
        self.client = None
        
        if config and AlibabaTranslateClient:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Alibaba Cloud translation client."""
        try:
            config = open_api_models.Config(
                access_key_id=self.config.access_key_id,
                access_key_secret=self.config.access_key_secret
            )
            config.endpoint = self.config.endpoint
            self.client = AlibabaTranslateClient(config)
            logger.info("Alibaba Cloud translation client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Alibaba Cloud client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if translation service is available."""
        return self.client is not None and AlibabaTranslateClient is not None
    
    def _get_alibaba_client(self):
        """Get Alibaba Cloud translation client.
        
        Returns:
            Mock client for testing purposes
        """
        # Mock implementation for testing
        class MockClient:
            async def translate_general_with_options(self, request, runtime=None):
                class MockResponse:
                    class MockBody:
                        class MockData:
                            translated = "Mock translated text"
                        data = MockData()
                    body = MockBody()
                return MockResponse()
        
        return MockClient()
    
    async def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
        """Translate a single text.
        
        Args:
            text: Text to translate
            source_lang: Source language code (auto for auto-detection)
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        if not self.is_available():
            logger.warning("Translation service not available, returning original text")
            return text
        
        if not text.strip():
            return text
        
        try:
            request = mt_models.TranslateGeneralRequest(
                format_type="text",
                source_language=source_lang,
                target_language=target_lang,
                source_text=text,
                scene="general"
            )
            
            runtime = util_models.RuntimeOptions()
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.translate_general_with_options(request, runtime)
            )
            
            if response.body.code == "200":
                return response.body.data.translated
            else:
                logger.error(f"Translation failed: {response.body.message}")
                return text
                
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text
    
    async def translate_batch(self, texts: List[str], source_lang: str = "auto", target_lang: str = "en", 
                            batch_size: int = 10) -> List[str]:
        """Translate multiple texts in batches.
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        results = []
        
        # Process in batches to avoid rate limiting
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.translate_text(text, source_lang, target_lang) for text in batch],
                return_exceptions=True
            )
            
            # Handle exceptions in batch results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Translation failed for text {i+j}: {result}")
                    results.append(batch[j])  # Return original text on error
                else:
                    results.append(result)
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(texts):
                await asyncio.sleep(0.5)
        
        return results
    
    async def translate_srt_file(self, srt_content: str, source_lang: str = "auto", target_lang: str = "en") -> str:
        """Translate an entire SRT file while preserving timing.
        
        Args:
            srt_content: SRT file content as string
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated SRT content with preserved timing
        """
        if not srt_content.strip():
            return ""
        
        # Parse SRT content
        entries = self.parse_srt_content(srt_content)
        if not entries:
            return ""
        
        # Extract texts for translation
        texts = [entry.text for entry in entries]
        
        # Translate all texts
        translated_texts = await self.translate_batch(texts, source_lang, target_lang)
        
        # Update entries with translated texts
        for entry, translated_text in zip(entries, translated_texts):
            entry.text = translated_text
        
        # Format back to SRT
        return self.format_srt_content(entries)
    
    def parse_srt_content(self, srt_content: str) -> List[SubtitleEntry]:
        """Parse SRT subtitle content into structured entries.
        
        Args:
            srt_content: Raw SRT content as string
            
        Returns:
            List of SubtitleEntry objects
        """
        entries = []
        
        # Split content into blocks
        blocks = srt_content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            try:
                # Parse index
                index = int(lines[0])
                
                # Parse timing
                timing_line = lines[1]
                if ' --> ' not in timing_line:
                    continue
                
                start_time, end_time = timing_line.split(' --> ')
                
                # Parse text (may be multiple lines)
                text = '\n'.join(lines[2:])
                
                entries.append(SubtitleEntry(
                    index=index,
                    start_time=start_time.strip(),
                    end_time=end_time.strip(),
                    text=text
                ))
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse SRT block: {block[:50]}... Error: {e}")
                continue
        
        return entries
    
    def format_srt_content(self, entries: List[SubtitleEntry]) -> str:
        """Format subtitle entries back to SRT format.
        
        Args:
            entries: List of SubtitleEntry objects
            
        Returns:
            Formatted SRT content as string
        """
        if not entries:
            return ""
        
        srt_blocks = []
        for entry in entries:
            block = []
            block.append(str(entry.index))
            block.append(f"{entry.start_time} --> {entry.end_time}")
            block.append(entry.text)
            srt_blocks.append("\n".join(block))
        
        return "\n\n".join(srt_blocks) + "\n\n"
    
    async def translate_subtitle_file(self, srt_content: str, source_lang: str = "auto", 
                                    target_lang: str = "en") -> str:
        """Translate an entire SRT subtitle file while preserving timing.
        
        Args:
            srt_content: Raw SRT file content
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated SRT content with preserved timing
        """
        # Parse SRT content
        entries = self.parse_srt_content(srt_content)
        
        if not entries:
            logger.warning("No subtitle entries found to translate")
            return srt_content
        
        # Extract texts for translation
        texts = [entry.text for entry in entries]
        
        # Translate all texts
        logger.info(f"Translating {len(texts)} subtitle entries from {source_lang} to {target_lang}")
        translated_texts = await self.translate_batch(texts, source_lang, target_lang)
        
        # Update entries with translated texts
        for entry, translated_text in zip(entries, translated_texts):
            entry.text = translated_text
        
        # Format back to SRT
        return self.format_srt_content(entries)
    
    async def translate_subtitle_file_path(self, input_path: str, output_path: str, 
                                         source_lang: str = "auto", target_lang: str = "en") -> bool:
        """Translate a subtitle file and save to output path.
        
        Args:
            input_path: Path to input SRT file
            output_path: Path to save translated SRT file
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read input file
            with open(input_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # Translate content
            translated_content = await self.translate_subtitle_file(srt_content, source_lang, target_lang)
            
            # Write output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(translated_content)
            
            logger.info(f"Successfully translated subtitle file: {input_path} -> {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to translate subtitle file {input_path}: {e}")
            return False
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported language codes and names.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        return {
            "auto": "Auto Detect",
            "zh": "Chinese (Simplified)",
            "zh-tw": "Chinese (Traditional)",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
            "de": "German",
            "tr": "Turkish",
            "ru": "Russian",
            "pt": "Portuguese",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "th": "Thai",
            "ms": "Malay",
            "ar": "Arabic",
            "hi": "Hindi"
        }