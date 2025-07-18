#!/usr/bin/env python3
"""Unit tests for translation service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from whisper_subtitle.services.translation import (
    TranslationService,
    TranslationConfig,
    SubtitleEntry
)


class TestTranslationService:
    """Test cases for TranslationService."""
    
    def test_init_without_config(self):
        """Test initialization without configuration."""
        service = TranslationService()
        assert not service.is_available()
        assert service.config is None
    
    def test_init_with_config(self):
        """Test initialization with configuration."""
        config = TranslationConfig(
            access_key_id="test_key",
            access_key_secret="test_secret",
            endpoint="test.endpoint.com",
            region="test-region"
        )
        service = TranslationService(config)
        assert service.config == config
        # Note: is_available() might still return False without actual credentials
    
    def test_get_supported_languages(self):
        """Test getting supported languages."""
        service = TranslationService()
        languages = service.get_supported_languages()
        
        assert isinstance(languages, dict)
        assert len(languages) > 0
        assert "en" in languages
        assert "zh" in languages
        assert "es" in languages
        assert "fr" in languages
        assert "de" in languages
        assert "ja" in languages
        assert "ko" in languages
        assert "ru" in languages
    
    def test_parse_srt_content(self):
        """Test parsing SRT content."""
        service = TranslationService()
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello, world!

2
00:00:04,000 --> 00:00:06,000
This is a test.

3
00:00:07,000 --> 00:00:09,000
Multiple lines
of subtitle text.
"""
        
        entries = service.parse_srt_content(srt_content)
        
        assert len(entries) == 3
        
        # Test first entry
        assert entries[0].index == 1
        assert entries[0].start_time == "00:00:01,000"
        assert entries[0].end_time == "00:00:03,000"
        assert entries[0].text == "Hello, world!"
        
        # Test second entry
        assert entries[1].index == 2
        assert entries[1].start_time == "00:00:04,000"
        assert entries[1].end_time == "00:00:06,000"
        assert entries[1].text == "This is a test."
        
        # Test third entry (multi-line)
        assert entries[2].index == 3
        assert entries[2].start_time == "00:00:07,000"
        assert entries[2].end_time == "00:00:09,000"
        assert entries[2].text == "Multiple lines\nof subtitle text."
    
    def test_parse_empty_srt_content(self):
        """Test parsing empty SRT content."""
        service = TranslationService()
        entries = service.parse_srt_content("")
        assert len(entries) == 0
    
    def test_parse_malformed_srt_content(self):
        """Test parsing malformed SRT content."""
        service = TranslationService()
        malformed_srt = "This is not a valid SRT format"
        entries = service.parse_srt_content(malformed_srt)
        assert len(entries) == 0
    
    def test_format_srt_content(self):
        """Test formatting SRT content."""
        service = TranslationService()
        entries = [
            SubtitleEntry(
                index=1,
                start_time="00:00:01,000",
                end_time="00:00:03,000",
                text="Hello, world!"
            ),
            SubtitleEntry(
                index=2,
                start_time="00:00:04,000",
                end_time="00:00:06,000",
                text="This is a test."
            )
        ]
        
        formatted = service.format_srt_content(entries)
        expected = """1
00:00:01,000 --> 00:00:03,000
Hello, world!

2
00:00:04,000 --> 00:00:06,000
This is a test.

"""
        
        assert formatted == expected
    
    def test_format_empty_entries(self):
        """Test formatting empty entries list."""
        service = TranslationService()
        formatted = service.format_srt_content([])
        assert formatted == ""
    
    @patch('whisper_subtitle.services.translation.TranslationService._get_alibaba_client')
    async def test_translate_text_success(self, mock_get_client):
        """Test successful text translation."""
        # Mock the Alibaba Cloud client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.body.data.translated = "Hola, mundo!"
        mock_client.translate_general_with_options = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        config = TranslationConfig(
            access_key_id="test_key",
            access_key_secret="test_secret",
            endpoint="test.endpoint.com",
            region="test-region"
        )
        service = TranslationService(config)
        
        result = await service.translate_text("Hello, world!", "en", "es")
        assert result == "Hola, mundo!"
    
    @patch('whisper_subtitle.services.translation.TranslationService._get_alibaba_client')
    async def test_translate_text_failure(self, mock_get_client):
        """Test text translation failure."""
        # Mock the Alibaba Cloud client to raise an exception
        mock_client = Mock()
        mock_client.translate_general_with_options = AsyncMock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_client
        
        config = TranslationConfig(
            access_key_id="test_key",
            access_key_secret="test_secret",
            endpoint="test.endpoint.com",
            region="test-region"
        )
        service = TranslationService(config)
        
        result = await service.translate_text("Hello, world!", "en", "es")
        assert result == "Hello, world!"  # Should return original text on failure
    
    async def test_translate_text_without_config(self):
        """Test text translation without configuration."""
        service = TranslationService()
        result = await service.translate_text("Hello, world!", "en", "es")
        assert result == "Hello, world!"  # Should return original text
    
    @patch('whisper_subtitle.services.translation.TranslationService.translate_text')
    async def test_translate_batch(self, mock_translate_text):
        """Test batch translation."""
        # Mock translate_text to return translated versions
        mock_translate_text.side_effect = [
            "Hola, mundo!",
            "Esta es una prueba."
        ]
        
        service = TranslationService()
        texts = ["Hello, world!", "This is a test."]
        
        results = await service.translate_batch(texts, "en", "es")
        
        assert len(results) == 2
        assert results[0] == "Hola, mundo!"
        assert results[1] == "Esta es una prueba."
        assert mock_translate_text.call_count == 2
    
    @patch('whisper_subtitle.services.translation.TranslationService.translate_batch')
    async def test_translate_srt_file(self, mock_translate_batch):
        """Test SRT file translation."""
        # Mock translate_batch to return translated texts
        mock_translate_batch.return_value = [
            "Hola, mundo!",
            "Esta es una prueba."
        ]
        
        service = TranslationService()
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello, world!

2
00:00:04,000 --> 00:00:06,000
This is a test.
"""
        
        result = await service.translate_srt_file(srt_content, "en", "es")
        
        # Check that the result contains translated text with preserved timing
        assert "Hola, mundo!" in result
        assert "Esta es una prueba." in result
        assert "00:00:01,000 --> 00:00:03,000" in result
        assert "00:00:04,000 --> 00:00:06,000" in result
    
    async def test_translate_empty_srt_file(self):
        """Test translating empty SRT file."""
        service = TranslationService()
        result = await service.translate_srt_file("", "en", "es")
        assert result == ""


class TestSubtitleEntry:
    """Test cases for SubtitleEntry."""
    
    def test_subtitle_entry_creation(self):
        """Test creating a SubtitleEntry."""
        entry = SubtitleEntry(
            index=1,
            start_time="00:00:01,000",
            end_time="00:00:03,000",
            text="Hello, world!"
        )
        
        assert entry.index == 1
        assert entry.start_time == "00:00:01,000"
        assert entry.end_time == "00:00:03,000"
        assert entry.text == "Hello, world!"
    
    def test_subtitle_entry_equality(self):
        """Test SubtitleEntry equality."""
        entry1 = SubtitleEntry(
            index=1,
            start_time="00:00:01,000",
            end_time="00:00:03,000",
            text="Hello, world!"
        )
        entry2 = SubtitleEntry(
            index=1,
            start_time="00:00:01,000",
            end_time="00:00:03,000",
            text="Hello, world!"
        )
        entry3 = SubtitleEntry(
            index=2,
            start_time="00:00:01,000",
            end_time="00:00:03,000",
            text="Hello, world!"
        )
        
        assert entry1 == entry2
        assert entry1 != entry3


class TestTranslationConfig:
    """Test cases for TranslationConfig."""
    
    def test_translation_config_creation(self):
        """Test creating a TranslationConfig."""
        config = TranslationConfig(
            access_key_id="test_key",
            access_key_secret="test_secret",
            endpoint="test.endpoint.com",
            region="test-region"
        )
        
        assert config.access_key_id == "test_key"
        assert config.access_key_secret == "test_secret"
        assert config.endpoint == "test.endpoint.com"
        assert config.region == "test-region"
    
    def test_translation_config_defaults(self):
        """Test TranslationConfig with default values."""
        config = TranslationConfig(
            access_key_id="test_key",
            access_key_secret="test_secret"
        )
        
        assert config.access_key_id == "test_key"
        assert config.access_key_secret == "test_secret"
        assert config.endpoint == "mt.cn-hangzhou.aliyuncs.com"
        assert config.region == "cn-hangzhou"


if __name__ == "__main__":
    pytest.main([__file__])