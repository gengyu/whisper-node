#!/usr/bin/env python3
"""Unit tests for social media service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path
import json
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from whisper_subtitle.services.social_media import (
    SocialMediaService,
    MediaContent,
    PublishResult,
    SocialMediaPlatform,
    YouTubePlatform,
    TwitterPlatform
)


class TestMediaContent:
    """Test cases for MediaContent."""
    
    def test_media_content_creation(self):
        """Test creating MediaContent."""
        content = MediaContent(
            title="Test Video",
            description="This is a test video",
            tags=["test", "video"],
            language="en"
        )
        
        assert content.title == "Test Video"
        assert content.description == "This is a test video"
        assert content.tags == ["test", "video"]
        assert content.language == "en"
        assert content.video_path is None
        assert content.subtitle_path is None
        assert content.thumbnail_path is None
    
    def test_media_content_with_paths(self):
        """Test creating MediaContent with file paths."""
        content = MediaContent(
            title="Test Video",
            description="This is a test video",
            video_path="/path/to/video.mp4",
            subtitle_path="/path/to/subtitle.srt",
            thumbnail_path="/path/to/thumbnail.jpg"
        )
        
        assert content.video_path == "/path/to/video.mp4"
        assert content.subtitle_path == "/path/to/subtitle.srt"
        assert content.thumbnail_path == "/path/to/thumbnail.jpg"


class TestPublishResult:
    """Test cases for PublishResult."""
    
    def test_publish_result_success(self):
        """Test creating successful PublishResult."""
        result = PublishResult(
            platform="youtube",
            success=True,
            post_id="yt_123456",
            url="https://www.youtube.com/watch?v=yt_123456"
        )
        
        assert result.platform == "youtube"
        assert result.success is True
        assert result.post_id == "yt_123456"
        assert result.url == "https://www.youtube.com/watch?v=yt_123456"
        assert result.error_message is None
    
    def test_publish_result_failure(self):
        """Test creating failed PublishResult."""
        result = PublishResult(
            platform="twitter",
            success=False,
            error_message="Authentication failed"
        )
        
        assert result.platform == "twitter"
        assert result.success is False
        assert result.post_id is None
        assert result.url is None
        assert result.error_message == "Authentication failed"


class TestYouTubePlatform:
    """Test cases for YouTubePlatform."""
    
    def test_youtube_platform_init(self):
        """Test YouTubePlatform initialization."""
        config = {
            "api_key": "test_api_key",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        platform = YouTubePlatform(config)
        
        assert platform.name == "youtube"
        assert platform.config == config
    
    def test_youtube_platform_is_available(self):
        """Test YouTubePlatform availability check."""
        # With complete config
        config = {
            "api_key": "test_api_key",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        platform = YouTubePlatform(config)
        assert platform.is_available() is True
        
        # With incomplete config
        incomplete_config = {"api_key": "test_api_key"}
        platform_incomplete = YouTubePlatform(incomplete_config)
        assert platform_incomplete.is_available() is False
        
        # With empty config
        platform_empty = YouTubePlatform({})
        assert platform_empty.is_available() is False
    
    async def test_youtube_platform_authenticate(self):
        """Test YouTubePlatform authentication."""
        config = {
            "api_key": "test_api_key",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        platform = YouTubePlatform(config)
        
        # Mock authentication (always returns True in our implementation)
        result = await platform.authenticate()
        assert result is True
    
    async def test_youtube_platform_publish(self):
        """Test YouTubePlatform publishing."""
        config = {
            "api_key": "test_api_key",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        platform = YouTubePlatform(config)
        
        content = MediaContent(
            title="Test Video",
            description="This is a test video",
            tags=["test", "video"]
        )
        
        result = await platform.publish(content)
        
        assert result.platform == "youtube"
        assert result.success is True
        assert result.post_id.startswith("yt_")
        assert "youtube.com" in result.url


class TestTwitterPlatform:
    """Test cases for TwitterPlatform."""
    
    def test_twitter_platform_init(self):
        """Test TwitterPlatform initialization."""
        config = {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "access_token": "test_access_token",
            "access_token_secret": "test_access_token_secret"
        }
        platform = TwitterPlatform(config)
        
        assert platform.name == "twitter"
        assert platform.config == config
    
    def test_twitter_platform_is_available(self):
        """Test TwitterPlatform availability check."""
        # With complete config
        config = {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "access_token": "test_access_token",
            "access_token_secret": "test_access_token_secret"
        }
        platform = TwitterPlatform(config)
        assert platform.is_available() is True
        
        # With incomplete config
        incomplete_config = {"api_key": "test_api_key"}
        platform_incomplete = TwitterPlatform(incomplete_config)
        assert platform_incomplete.is_available() is False
        
        # With empty config
        platform_empty = TwitterPlatform({})
        assert platform_empty.is_available() is False
    
    async def test_twitter_platform_authenticate(self):
        """Test TwitterPlatform authentication."""
        config = {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "access_token": "test_access_token",
            "access_token_secret": "test_access_token_secret"
        }
        platform = TwitterPlatform(config)
        
        # Mock authentication (always returns True in our implementation)
        result = await platform.authenticate()
        assert result is True
    
    async def test_twitter_platform_publish(self):
        """Test TwitterPlatform publishing."""
        config = {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "access_token": "test_access_token",
            "access_token_secret": "test_access_token_secret"
        }
        platform = TwitterPlatform(config)
        
        content = MediaContent(
            title="Test Video",
            description="This is a test video",
            tags=["test", "video"]
        )
        
        result = await platform.publish(content)
        
        assert result.platform == "twitter"
        assert result.success is True
        assert result.post_id.startswith("tw_")
        assert "twitter.com" in result.url


class TestSocialMediaService:
    """Test cases for SocialMediaService."""
    
    def test_social_media_service_init_empty(self):
        """Test SocialMediaService initialization with empty config."""
        service = SocialMediaService()
        
        assert len(service.platforms) == 0
        assert service.get_available_platforms() == []
    
    def test_social_media_service_init_with_config(self):
        """Test SocialMediaService initialization with configuration."""
        config = {
            "youtube": {
                "api_key": "test_api_key",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            },
            "twitter": {
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "access_token": "test_access_token",
                "access_token_secret": "test_access_token_secret"
            }
        }
        service = SocialMediaService(config)
        
        assert len(service.platforms) == 2
        assert "youtube" in service.platforms
        assert "twitter" in service.platforms
        assert set(service.get_available_platforms()) == {"youtube", "twitter"}
    
    def test_social_media_service_init_partial_config(self):
        """Test SocialMediaService initialization with partial configuration."""
        config = {
            "youtube": {
                "api_key": "test_api_key"  # Incomplete config
            },
            "twitter": {
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "access_token": "test_access_token",
                "access_token_secret": "test_access_token_secret"
            }
        }
        service = SocialMediaService(config)
        
        assert len(service.platforms) == 2
        # Only Twitter should be available with complete config
        assert service.get_available_platforms() == ["twitter"]
    
    async def test_authenticate_all(self):
        """Test authenticating all platforms."""
        config = {
            "youtube": {
                "api_key": "test_api_key",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            },
            "twitter": {
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "access_token": "test_access_token",
                "access_token_secret": "test_access_token_secret"
            }
        }
        service = SocialMediaService(config)
        
        results = await service.authenticate_all()
        
        assert "youtube" in results
        assert "twitter" in results
        assert results["youtube"] is True
        assert results["twitter"] is True
    
    async def test_publish_to_platform(self):
        """Test publishing to a specific platform."""
        config = {
            "youtube": {
                "api_key": "test_api_key",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            }
        }
        service = SocialMediaService(config)
        
        content = MediaContent(
            title="Test Video",
            description="This is a test video",
            tags=["test", "video"]
        )
        
        result = await service.publish_to_platform("youtube", content)
        
        assert result.platform == "youtube"
        assert result.success is True
        assert result.post_id.startswith("yt_")
    
    async def test_publish_to_nonexistent_platform(self):
        """Test publishing to a non-existent platform."""
        service = SocialMediaService()
        
        content = MediaContent(
            title="Test Video",
            description="This is a test video"
        )
        
        result = await service.publish_to_platform("nonexistent", content)
        
        assert result.platform == "nonexistent"
        assert result.success is False
        assert "not available" in result.error_message
    
    async def test_publish_to_multiple(self):
        """Test publishing to multiple platforms."""
        config = {
            "youtube": {
                "api_key": "test_api_key",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            },
            "twitter": {
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "access_token": "test_access_token",
                "access_token_secret": "test_access_token_secret"
            }
        }
        service = SocialMediaService(config)
        
        content = MediaContent(
            title="Test Video",
            description="This is a test video",
            tags=["test", "video"]
        )
        
        results = await service.publish_to_multiple(["youtube", "twitter"], content)
        
        assert len(results) == 2
        
        # Check YouTube result
        youtube_result = next(r for r in results if r.platform == "youtube")
        assert youtube_result.success is True
        assert youtube_result.post_id.startswith("yt_")
        
        # Check Twitter result
        twitter_result = next(r for r in results if r.platform == "twitter")
        assert twitter_result.success is True
        assert twitter_result.post_id.startswith("tw_")
    
    def test_publish_history_empty(self):
        """Test getting empty publish history."""
        service = SocialMediaService()
        history = service.get_publish_history()
        assert len(history) == 0
    
    def test_publish_history_with_temp_file(self):
        """Test publish history with temporary file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            # Create a temporary history file
            history_data = [
                {
                    "timestamp": "2023-01-01T12:00:00",
                    "platform": "youtube",
                    "success": True,
                    "post_id": "yt_123456",
                    "url": "https://www.youtube.com/watch?v=yt_123456",
                    "content_title": "Test Video"
                }
            ]
            json.dump(history_data, f)
            temp_file_path = f.name
        
        try:
            service = SocialMediaService(history_file=temp_file_path)
            history = service.get_publish_history()
            
            assert len(history) == 1
            assert history[0]["platform"] == "youtube"
            assert history[0]["success"] is True
            assert history[0]["post_id"] == "yt_123456"
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    async def test_publish_history_recording(self):
        """Test that publishing records history."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file_path = f.name
        
        try:
            config = {
                "youtube": {
                    "api_key": "test_api_key",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret"
                }
            }
            service = SocialMediaService(config, history_file=temp_file_path)
            
            content = MediaContent(
                title="Test Video",
                description="This is a test video"
            )
            
            # Publish content
            await service.publish_to_platform("youtube", content)
            
            # Check history
            history = service.get_publish_history()
            assert len(history) == 1
            assert history[0]["platform"] == "youtube"
            assert history[0]["content_title"] == "Test Video"
        finally:
            # Clean up
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)


if __name__ == "__main__":
    pytest.main([__file__])