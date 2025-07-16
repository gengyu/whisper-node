#!/usr/bin/env python3
"""Installation script for Whisper Subtitle Generator."""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(cmd, check=True, shell=False):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(cmd, check=check, shell=shell, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            raise
        return e


def check_python_version():
    """Check if Python version is compatible."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True


def install_python_dependencies():
    """Install Python dependencies."""
    print("\nInstalling Python dependencies...")
    
    # Use pip with mirror for faster installation in China
    pip_cmd = [
        sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
        "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
    ]
    
    try:
        run_command(pip_cmd)
        print("✅ Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python dependencies")
        return False


def install_ffmpeg():
    """Install FFmpeg based on platform."""
    print("\nInstalling FFmpeg...")
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        # Check if Homebrew is installed
        try:
            run_command(["brew", "--version"])
            run_command(["brew", "install", "ffmpeg"])
            print("✅ FFmpeg installed via Homebrew")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Homebrew not found. Please install Homebrew first or install FFmpeg manually")
            return False
    
    elif system == "linux":
        # Try different package managers
        package_managers = [
            (["apt", "update"], ["apt", "install", "-y", "ffmpeg"]),
            (["yum", "install", "-y", "epel-release"], ["yum", "install", "-y", "ffmpeg"]),
            (["dnf", "install", "-y", "ffmpeg"]),
            (["pacman", "-S", "--noconfirm", "ffmpeg"]),
        ]
        
        for commands in package_managers:
            try:
                if len(commands) == 2:
                    run_command(commands[0])
                    run_command(commands[1])
                else:
                    run_command(commands[0])
                print("✅ FFmpeg installed successfully")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        print("❌ Could not install FFmpeg automatically. Please install manually")
        return False
    
    elif system == "windows":
        print("🪟 Windows: Please download FFmpeg from https://ffmpeg.org/download.html")
        print("   and add it to your PATH, or place ffmpeg.exe in the bin/ directory")
        return False
    
    else:
        print(f"❌ Unsupported platform: {system}")
        return False


def setup_whisperkit_macos():
    """Setup WhisperKit for macOS."""
    if platform.system() != "Darwin":
        return True
    
    print("\nSetting up WhisperKit for macOS...")
    
    # Check if we're on Apple Silicon
    try:
        result = run_command(["uname", "-m"])
        if "arm64" not in result.stdout:
            print("⚠️  WhisperKit requires Apple Silicon (M1/M2/M3) Mac")
            return True
    except:
        pass
    
    # Check if WhisperKit CLI is available
    whisperkit_cli = Path("bin/whisperkit-cli")
    if not whisperkit_cli.exists():
        print("📥 WhisperKit CLI not found. Please install manually:")
        print("   1. Visit: https://github.com/argmaxinc/WhisperKit")
        print("   2. Download the latest release")
        print("   3. Place whisperkit-cli in the bin/ directory")
        return False
    
    print("✅ WhisperKit setup complete")
    return True


def create_directories():
    """Create necessary directories."""
    print("\nCreating directories...")
    
    directories = [
        "uploads",
        "downloads", 
        "output",
        "temp",
        "models",
        "logs",
        "bin"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return True


def create_env_file():
    """Create .env file with default settings."""
    print("\nCreating .env file...")
    
    env_file = Path(".env")
    if env_file.exists():
        print("⚠️  .env file already exists, skipping")
        return True
    
    env_content = '''# Whisper Subtitle Generator Configuration

# Server Settings
HOST=127.0.0.1
PORT=8000
DEBUG=false

# Directory Settings
UPLOAD_DIR=./uploads
OUTPUT_DIR=./output
TEMP_DIR=./temp
DOWNLOAD_DIR=./downloads

# File Settings
MAX_FILE_SIZE=524288000  # 500MB

# Engine Settings
# OpenAI Whisper
OPENAI_WHISPER_MODEL_DIR=./models/openai_whisper

# Faster Whisper
FASTER_WHISPER_MODEL_DIR=./models/faster_whisper
FASTER_WHISPER_DEVICE=auto
FASTER_WHISPER_COMPUTE_TYPE=auto

# WhisperKit (macOS only)
WHISPERKIT_CLI_PATH=./bin/whisperkit-cli
WHISPERKIT_MODEL_PATH=./models/whisperkit/large-v2

# WhisperCpp
WHISPERCPP_MODEL_PATH=./models/whispercpp/ggml-large-v2.bin
WHISPERCPP_EXECUTABLE_PATH=./bin/whisper

# Alibaba Cloud ASR (optional)
# ALIBABA_ACCESS_KEY_ID=your_access_key_id
# ALIBABA_ACCESS_KEY_SECRET=your_access_key_secret
# ALIBABA_APP_KEY=your_app_key

# YouTube Settings
YOUTUBE_DL_FORMAT=best[height<=720]
YOUTUBE_DL_EXTRACT_FLAT=false

# Logging
LOG_LEVEL=INFO
'''
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ .env file created")
    return True


def test_installation():
    """Test the installation."""
    print("\nTesting installation...")
    
    try:
        # Test imports
        sys.path.insert(0, str(Path("src")))
        
        from whisper_subtitle.config.settings import Settings
        settings = Settings()
        print("✅ Settings loaded successfully")
        
        from whisper_subtitle.core.engines.registry import registry
        engines = registry.list_engines()
        print(f"✅ Found {len(engines)} engines: {', '.join(engines)}")
        
        from whisper_subtitle.api.main import app
        print("✅ API app initialized")
        
        print("\n🎉 Installation completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        return False


def main():
    """Main installation function."""
    print("🎤 Whisper Subtitle Generator - Installation Script")
    print("=" * 50)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Create directories
    if not create_directories():
        success = False
    
    # Install Python dependencies
    if not install_python_dependencies():
        success = False
    
    # Install FFmpeg
    if not install_ffmpeg():
        print("⚠️  FFmpeg installation failed, but continuing...")
    
    # Setup WhisperKit for macOS
    if not setup_whisperkit_macos():
        print("⚠️  WhisperKit setup incomplete, but continuing...")
    
    # Create .env file
    if not create_env_file():
        success = False
    
    # Test installation
    if not test_installation():
        success = False
    
    if success:
        print("\n🎉 Installation completed successfully!")
        print("\nNext steps:")
        print("1. Run: python -m whisper_subtitle.cli --help")
        print("2. Start server: python -m whisper_subtitle.cli server")
        print("3. Open browser: http://localhost:8000")
        print("4. Build desktop app: python build_app.py")
    else:
        print("\n❌ Installation completed with some errors")
        print("Please check the error messages above and fix them manually")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)