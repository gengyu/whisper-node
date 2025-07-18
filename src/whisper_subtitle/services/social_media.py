"""Social media integration service for automated publishing."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MediaContent:
    """Media content for social media posting."""
    title: str
    description: str
    video_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    tags: List[str] = None
    language: str = "en"
    duration: Optional[float] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class PublishResult:
    """Result of social media publishing."""
    success: bool
    platform: str
    post_id: Optional[str] = None
    url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SocialMediaPlatform(ABC):
    """Abstract base class for social media platforms."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform_name = self.__class__.__name__.replace('Platform', '').lower()
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the platform."""
        pass
    
    @abstractmethod
    async def publish_content(self, content: MediaContent) -> PublishResult:
        """Publish content to the platform."""
        pass
    
    @abstractmethod
    async def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """Get status of a published post."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if platform integration is available."""
        pass


class YouTubePlatform(SocialMediaPlatform):
    """YouTube platform integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "youtube"
        self.api_key = config.get('api_key')
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.authenticated = False
    
    async def authenticate(self) -> bool:
        """Authenticate with YouTube API."""
        try:
            # Mock authentication for now
            # In real implementation, use Google OAuth2
            if self.api_key and self.client_id and self.client_secret:
                self.authenticated = True
                logger.info("YouTube authentication successful")
                return True
            else:
                logger.error("YouTube credentials not provided")
                return False
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            return False
    
    async def publish_content(self, content: MediaContent) -> PublishResult:
        """Publish content to YouTube."""
        if not self.authenticated:
            await self.authenticate()
        
        if not self.authenticated:
            return PublishResult(
                success=False,
                platform="youtube",
                error_message="Authentication failed"
            )
        
        try:
            # Mock YouTube upload
            # In real implementation, use YouTube Data API v3
            logger.info(f"Publishing to YouTube: {content.title}")
            
            # Simulate upload process
            await asyncio.sleep(1)
            
            mock_video_id = f"yt_{hash(content.title) % 1000000}"
            mock_url = f"https://www.youtube.com/watch?v={mock_video_id}"
            
            return PublishResult(
                success=True,
                platform="youtube",
                post_id=mock_video_id,
                url=mock_url,
                metadata={
                    "title": content.title,
                    "description": content.description,
                    "tags": content.tags,
                    "language": content.language,
                    "duration": content.duration
                }
            )
            
        except Exception as e:
            logger.error(f"YouTube publishing failed: {e}")
            return PublishResult(
                success=False,
                platform="youtube",
                error_message=str(e)
            )
    
    async def publish(self, content: MediaContent) -> PublishResult:
        """Alias for publish_content for compatibility."""
        return await self.publish_content(content)
    
    async def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """Get YouTube video status."""
        try:
            # Mock status check
            return {
                "id": post_id,
                "status": "published",
                "views": 0,
                "likes": 0,
                "comments": 0
            }
        except Exception as e:
            logger.error(f"Failed to get YouTube post status: {e}")
            return {}
    
    def is_available(self) -> bool:
        """Check if YouTube integration is available."""
        return bool(self.api_key and self.client_id and self.client_secret)


class TwitterPlatform(SocialMediaPlatform):
    """Twitter platform integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "twitter"
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.access_token = config.get('access_token')
        self.access_token_secret = config.get('access_token_secret')
        self.authenticated = False
    
    async def authenticate(self) -> bool:
        """Authenticate with Twitter API."""
        try:
            # Mock authentication
            if all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
                self.authenticated = True
                logger.info("Twitter authentication successful")
                return True
            else:
                logger.error("Twitter credentials not provided")
                return False
        except Exception as e:
            logger.error(f"Twitter authentication failed: {e}")
            return False
    
    async def publish_content(self, content: MediaContent) -> PublishResult:
        """Publish content to Twitter."""
        if not self.authenticated:
            await self.authenticate()
        
        if not self.authenticated:
            return PublishResult(
                success=False,
                platform="twitter",
                error_message="Authentication failed"
            )
        
        try:
            # Mock Twitter post
            logger.info(f"Publishing to Twitter: {content.title}")
            
            # Create tweet text
            tweet_text = f"{content.title}\n\n{content.description[:200]}..."
            if content.tags:
                hashtags = ' '.join([f"#{tag}" for tag in content.tags[:3]])
                tweet_text += f"\n\n{hashtags}"
            
            # Simulate post
            await asyncio.sleep(0.5)
            
            mock_tweet_id = f"tw_{hash(content.title) % 1000000}"
            mock_url = f"https://twitter.com/user/status/{mock_tweet_id}"
            
            return PublishResult(
                success=True,
                platform="twitter",
                post_id=mock_tweet_id,
                url=mock_url,
                metadata={
                    "text": tweet_text,
                    "hashtags": content.tags
                }
            )
            
        except Exception as e:
            logger.error(f"Twitter publishing failed: {e}")
            return PublishResult(
                success=False,
                platform="twitter",
                error_message=str(e)
            )
    
    async def publish(self, content: MediaContent) -> PublishResult:
        """Alias for publish_content for compatibility."""
        return await self.publish_content(content)
    
    async def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """Get Twitter post status."""
        try:
            # Mock status check
            return {
                "id": post_id,
                "status": "published",
                "retweets": 0,
                "likes": 0,
                "replies": 0
            }
        except Exception as e:
            logger.error(f"Failed to get Twitter post status: {e}")
            return {}
    
    def is_available(self) -> bool:
        """Check if Twitter integration is available."""
        return all([self.api_key, self.api_secret, self.access_token, self.access_token_secret])


class SocialMediaService:
    """Main service for social media integration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, history_file: Optional[str] = None):
        """Initialize social media service.
        
        Args:
            config: Configuration dictionary with platform settings
            history_file: Path to history file for storing publish records
        """
        self.config = config or {}
        self.platforms: Dict[str, SocialMediaPlatform] = {}
        self.publish_history: List[PublishResult] = []
        self.history_file = history_file
        
        self._initialize_platforms()
        
        # Load existing history if file exists
        if self.history_file:
            self.load_publish_history(self.history_file)
    
    def _initialize_platforms(self):
        """Initialize available social media platforms."""
        # Initialize YouTube
        youtube_config = self.config.get('youtube', {})
        if youtube_config:
            self.platforms['youtube'] = YouTubePlatform(youtube_config)
        
        # Initialize Twitter
        twitter_config = self.config.get('twitter', {})
        if twitter_config:
            self.platforms['twitter'] = TwitterPlatform(twitter_config)
        
        logger.info(f"Initialized {len(self.platforms)} social media platforms")
    
    def get_available_platforms(self) -> List[str]:
        """Get list of available and configured platforms."""
        return [name for name, platform in self.platforms.items() if platform.is_available()]
    
    async def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate with all configured platforms."""
        results = {}
        
        for name, platform in self.platforms.items():
            try:
                results[name] = await platform.authenticate()
            except Exception as e:
                logger.error(f"Authentication failed for {name}: {e}")
                results[name] = False
        
        return results
    
    async def publish_to_platform(self, platform_name: str, content: MediaContent) -> PublishResult:
        """Publish content to a specific platform.
        
        Args:
            platform_name: Name of the platform (youtube, twitter, etc.)
            content: Media content to publish
            
        Returns:
            Publishing result
        """
        if platform_name not in self.platforms:
            return PublishResult(
                success=False,
                platform=platform_name,
                error_message=f"Platform {platform_name} not available"
            )
        
        platform = self.platforms[platform_name]
        
        if not platform.is_available():
            return PublishResult(
                success=False,
                platform=platform_name,
                error_message=f"Platform {platform_name} not available (missing credentials)"
            )
        
        try:
            result = await platform.publish_content(content)
            # Add timestamp and content title to result
            from datetime import datetime
            result.timestamp = datetime.now()
            result.content_title = content.title
            self.publish_history.append(result)
            
            # Auto-save history if file is configured
            if self.history_file:
                self.save_publish_history(self.history_file)
            
            return result
        except Exception as e:
            logger.error(f"Publishing to {platform_name} failed: {e}")
            return PublishResult(
                success=False,
                platform=platform_name,
                error_message=str(e)
            )
    
    async def publish_to_multiple(self, platforms: List[str], content: MediaContent) -> List[PublishResult]:
        """Publish content to multiple platforms simultaneously.
        
        Args:
            platforms: List of platform names
            content: Media content to publish
            
        Returns:
            List of publishing results
        """
        tasks = []
        
        for platform_name in platforms:
            task = self.publish_to_platform(platform_name, content)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(PublishResult(
                    success=False,
                    platform=platforms[i],
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def get_post_status(self, platform_name: str, post_id: str) -> Dict[str, Any]:
        """Get status of a published post.
        
        Args:
            platform_name: Name of the platform
            post_id: ID of the post
            
        Returns:
            Post status information
        """
        if platform_name not in self.platforms:
            return {"error": f"Platform {platform_name} not configured"}
        
        try:
            return await self.platforms[platform_name].get_post_status(post_id)
        except Exception as e:
            logger.error(f"Failed to get post status from {platform_name}: {e}")
            return {"error": str(e)}
    
    def get_publish_history(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get publishing history.
        
        Args:
            platform: Filter by platform name (optional)
            
        Returns:
            List of publish history entries as dictionaries
        """
        history = self.publish_history
        if platform:
            history = [result for result in self.publish_history if result.platform == platform]
        
        return [{
            "timestamp": result.timestamp.isoformat() if hasattr(result, 'timestamp') else None,
            "platform": result.platform,
            "success": result.success,
            "post_id": result.post_id,
            "url": result.url,
            "error_message": result.error_message,
            "content_title": getattr(result, 'content_title', None)
        } for result in history]
    
    def get_publish_history_dict(self) -> List[Dict[str, Any]]:
        """Get publishing history as dictionary format.
        
        Returns:
            List of publish history entries as dictionaries
        """
        return [{
            "timestamp": getattr(result, 'timestamp', None),
            "platform": result.platform,
            "success": result.success,
            "post_id": result.post_id,
            "url": result.url,
            "error_message": result.error_message,
            "content_title": getattr(result, 'content_title', None)
        } for result in self.publish_history]
    
    def save_publish_history(self, file_path: str):
        """Save publish history to file.
        
        Args:
            file_path: Path to save the history
        """
        try:
            history_data = []
            for result in self.publish_history:
                history_data.append({
                    "success": result.success,
                    "platform": result.platform,
                    "post_id": result.post_id,
                    "url": result.url,
                    "error_message": result.error_message,
                    "metadata": result.metadata
                })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Publish history saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save publish history: {e}")
    
    def load_publish_history(self, file_path: str):
        """Load publish history from file.
        
        Args:
            file_path: Path to load the history from
        """
        try:
            if not Path(file_path).exists():
                logger.warning(f"Publish history file not found: {file_path}")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            self.publish_history = []
            for item in history_data:
                result = PublishResult(
                    success=item.get('success', False),
                    platform=item.get('platform', ''),
                    post_id=item.get('post_id'),
                    url=item.get('url'),
                    error_message=item.get('error_message'),
                    metadata=item.get('metadata', {})
                )
                self.publish_history.append(result)
            
            logger.info(f"Loaded {len(self.publish_history)} publish history entries")
            
        except Exception as e:
            logger.error(f"Failed to load publish history: {e}")