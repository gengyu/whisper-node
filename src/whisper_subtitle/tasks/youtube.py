"""YouTube任务模块，提供向后兼容性。"""

# 从实际实现模块导入功能
from .youtube_fetcher import YouTubeFetcher, YouTubeChannel, VideoFetchResult

# 定义模块公开的接口
__all__ = ['YouTubeFetcher', 'YouTubeChannel', 'VideoFetchResult']