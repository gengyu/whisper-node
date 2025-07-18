"""Application settings and configuration."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application Configuration
    app_name: str = Field(default="Whisper Subtitle Generator", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path = Field(default=Path("./logs/app.log"), env="LOG_FILE")
    
    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # Directory settings
    base_dir: Path = Field(default_factory=lambda: Path.cwd(), description="Base directory")
    output_dir: Path = Field(default_factory=lambda: Path.cwd() / "output", description="Output directory")
    temp_dir: Path = Field(default_factory=lambda: Path.cwd() / "temp", description="Temporary directory")
    upload_dir: Path = Field(default_factory=lambda: Path.cwd() / "uploads", description="Upload directory")
    download_dir: Path = Field(default_factory=lambda: Path.cwd() / "downloads", description="Download directory")
    model_dir: Path = Field(default=Path("./models"), env="MODEL_DIR")
    
    # WhisperKit Configuration (macOS only)
    whisperkit_cli_path: Path = Field(default=Path("./bin/whisperkit-cli"), env="WHISPERKIT_CLI_PATH")
    whisperkit_model_path: Path = Field(default=Path("./models/whisperkit/large-v2"), env="WHISPERKIT_MODEL_PATH")
    
    # WhisperCpp Configuration
    whispercpp_model_path: Path = Field(default=Path("./models/whispercpp/ggml-large-v2.bin"), env="WHISPERCPP_MODEL_PATH")
    
    # Faster Whisper Configuration
    faster_whisper_model_size: str = Field(default="medium", env="FASTER_WHISPER_MODEL_SIZE")
    faster_whisper_device: str = Field(default="auto", env="FASTER_WHISPER_DEVICE")
    
    # OpenAI Whisper Configuration
    openai_whisper_model: str = Field(default="medium", env="OPENAI_WHISPER_MODEL")
    
    # Alibaba Cloud ASR Configuration
    alibaba_access_key_id: Optional[str] = Field(default=None, env="ALIBABA_ACCESS_KEY_ID")
    alibaba_access_key_secret: Optional[str] = Field(default=None, env="ALIBABA_ACCESS_KEY_SECRET")
    alibaba_app_key: Optional[str] = Field(default=None, env="ALIBABA_APP_KEY")
    
    # Alibaba Cloud Translation Configuration
    alibaba_translation_endpoint: str = Field(default="mt.cn-hangzhou.aliyuncs.com", env="ALIBABA_TRANSLATION_ENDPOINT")
    alibaba_translation_region: str = Field(default="cn-hangzhou", env="ALIBABA_TRANSLATION_REGION")
    
    # Social Media Integration Configuration
    # YouTube API
    youtube_api_key: Optional[str] = Field(default=None, env="YOUTUBE_API_KEY")
    youtube_client_id: Optional[str] = Field(default=None, env="YOUTUBE_CLIENT_ID")
    youtube_client_secret: Optional[str] = Field(default=None, env="YOUTUBE_CLIENT_SECRET")
    
    # Twitter API
    twitter_api_key: Optional[str] = Field(default=None, env="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(default=None, env="TWITTER_API_SECRET")
    twitter_access_token: Optional[str] = Field(default=None, env="TWITTER_ACCESS_TOKEN")
    twitter_access_token_secret: Optional[str] = Field(default=None, env="TWITTER_ACCESS_TOKEN_SECRET")
    
    # Social Media Publishing Settings
    social_media_history_file: Path = Field(default_factory=lambda: Path.cwd() / "social_media_history.json", env="SOCIAL_MEDIA_HISTORY_FILE")
    auto_publish_enabled: bool = Field(default=False, env="AUTO_PUBLISH_ENABLED")
    default_publish_platforms: List[str] = Field(default_factory=list, env="DEFAULT_PUBLISH_PLATFORMS")
    
    # Redis Configuration (for Celery)
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./whisper_subtitle.db", env="DATABASE_URL")
    
    # YouTube Download Configuration
    yt_dlp_output_template: str = Field(default="%(title)s.%(ext)s", env="YT_DLP_OUTPUT_TEMPLATE")
    yt_dlp_format: str = Field(default="best[height<=720]", env="YT_DLP_FORMAT")
    
    # Scheduled Tasks
    schedule_enabled: bool = Field(default=False, env="SCHEDULE_ENABLED")
    schedule_interval: int = Field(default=3600, env="SCHEDULE_INTERVAL")  # seconds
    youtube_channels: List[str] = Field(default=[], env="YOUTUBE_CHANNELS")
    
    # Security
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    
    # File settings
    max_file_size: int = Field(default=500 * 1024 * 1024, description="Maximum file size in bytes (500MB)")
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [
            # Audio formats
            ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma",
            # Video formats
            ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"
        ],
        description="Allowed file extensions"
    )
    
    # Engine settings
    default_engine: str = Field(default="openai_whisper", description="Default speech recognition engine")
    default_model: str = Field(default="base", description="Default model")
    default_language: str = Field(default="auto", description="Default language")
    default_output_format: str = Field(default="srt", description="Default output format")
    
    # Engine configurations
    engines: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "openai_whisper": {
                "enabled": True,
                "models": ["tiny", "base", "small", "medium", "large"],
                "default_model": "base",
                "languages": ["auto", "en", "zh", "ja", "ko", "es", "fr", "de", "it", "pt", "ru"],
                "device": "auto",  # auto, cpu, cuda
            },
            "faster_whisper": {
                "enabled": True,
                "models": ["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                "default_model": "base",
                "languages": ["auto", "en", "zh", "ja", "ko", "es", "fr", "de", "it", "pt", "ru"],
                "device": "auto",  # auto, cpu, cuda
                "compute_type": "auto",  # auto, int8, int16, float16, float32
            },
            "whisperkit": {
                "enabled": False,  # Only available on macOS with Apple Silicon
                "models": ["large-v2"],
                "default_model": "large-v2",
                "languages": ["auto", "en", "zh", "ja", "ko", "es", "fr", "de", "it", "pt", "ru"],
            },
            "whispercpp": {
                "enabled": False,
                "models": ["base", "small", "medium", "large-v2"],
                "default_model": "base",
                "languages": ["auto", "en", "zh", "ja", "ko", "es", "fr", "de", "it", "pt", "ru"],
            },
            "alibaba_asr": {
                "enabled": False,
                "models": ["general"],
                "default_model": "general",
                "languages": ["zh", "en"],
                "access_key_id": "",
                "access_key_secret": "",
                "region": "cn-shanghai",
            }
        },
        description="Engine configurations"
    )
    
    # Task settings
    max_concurrent_tasks: int = Field(default=3, description="Maximum concurrent tasks")
    task_timeout: int = Field(default=3600, description="Task timeout in seconds")
    cleanup_interval: int = Field(default=3600, description="Cleanup interval in seconds")
    max_task_age: int = Field(default=86400 * 7, description="Maximum task age in seconds (7 days)")
    
    # YouTube settings
    youtube_check_interval: int = Field(default=3600, description="YouTube check interval in seconds")
    youtube_max_videos: int = Field(default=10, description="Maximum videos to process per check")
    youtube_download_format: str = Field(default="bestaudio", description="YouTube download format")
    
    # API settings
    api_title: str = Field(default="Whisper Subtitle Generator API", description="API title")
    api_description: str = Field(default="API for speech recognition and subtitle generation", description="API description")
    api_version: str = Field(default="1.0.0", description="API version")
    
    # Security settings
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        description="CORS allowed origins"
    )
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "WHISPER_SUBTITLE_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields
        
    def __init__(self, **kwargs):
        """Initialize settings and create directories."""
        super().__init__(**kwargs)
        self._create_directories()
        
    def _create_directories(self):
        """Create necessary directories."""
        directories = [
            self.output_dir,
            self.temp_dir,
            self.upload_dir,
            self.download_dir,
            self.model_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Ensure log file directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def ensure_directories(self):
        """Ensure all necessary directories exist."""
        self._create_directories()
    
    def get_engine_config(self, engine_name: str) -> Dict[str, Any]:
        """Get configuration for a specific engine."""
        return self.engines.get(engine_name, {})
    
    def is_engine_enabled(self, engine_name: str) -> bool:
        """Check if an engine is enabled."""
        engine_config = self.get_engine_config(engine_name)
        return engine_config.get("enabled", False)
    
    def get_enabled_engines(self) -> List[str]:
        """Get list of enabled engines."""
        return [name for name, config in self.engines.items() if config.get("enabled", False)]
    
    def get_engine_models(self, engine_name: str) -> List[str]:
        """Get available models for an engine."""
        engine_config = self.get_engine_config(engine_name)
        return engine_config.get("models", [])
    
    def get_engine_languages(self, engine_name: str) -> List[str]:
        """Get supported languages for an engine."""
        engine_config = self.get_engine_config(engine_name)
        return engine_config.get("languages", [])
    
    # Compatibility properties for backward compatibility
    @property
    def uploads_dir(self) -> Path:
        """Alias for upload_dir."""
        return self.upload_dir
    
    @property
    def downloads_dir(self) -> Path:
        """Alias for download_dir."""
        return self.download_dir
    
    @property
    def models_dir(self) -> Path:
        """Models directory."""
        return self.base_dir / "models"
    
    @property
    def logs_dir(self) -> Path:
        """Logs directory."""
        return self.base_dir / "logs"
    
    @property
    def bin_dir(self) -> Path:
        """Binary files directory."""
        return self.base_dir / "bin"
    
    @property
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return os.uname().sysname == "Darwin"
    
    @property
    def is_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon (M1/M2)."""
        if not self.is_macos:
            return False
        try:
            import platform
            return platform.processor() == "arm" or "arm64" in platform.machine().lower()
        except Exception:
            return False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings