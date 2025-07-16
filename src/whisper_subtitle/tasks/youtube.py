"""YouTube tasks for backward compatibility."""

# Import from the actual implementation
from .youtube_fetcher import YouTubeFetcher, YouTubeChannel, VideoFetchResult

__all__ = ['YouTubeFetcher', 'YouTubeChannel', 'VideoFetchResult']