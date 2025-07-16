#!/usr/bin/env python3
"""Test script to verify the installation and basic functionality."""

import sys
import os
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def test_imports():
    """Test if all modules can be imported."""
    print("Testing imports...")
    
    try:
        # Core modules
        from whisper_subtitle.config.settings import Settings
        from whisper_subtitle.core.transcription import TranscriptionService
        from whisper_subtitle.core.engines.base import BaseEngine
        print("✓ Core modules imported successfully")
        
        # API modules
        from whisper_subtitle.api.main import app
        from whisper_subtitle.api.routes import upload, models, youtube
        print("✓ API modules imported successfully")
        
        # CLI modules
        from whisper_subtitle.cli.main import cli
        from whisper_subtitle.cli.commands import transcribe, server, youtube as youtube_cli
        print("✓ CLI modules imported successfully")
        
        # Task modules
        from whisper_subtitle.tasks.scheduler import TaskScheduler
        from whisper_subtitle.tasks.youtube_fetcher import YouTubeFetcher
        print("✓ Task modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_settings():
    """Test settings initialization."""
    print("\nTesting settings...")
    
    try:
        from whisper_subtitle.config.settings import Settings
        settings = Settings()
        
        # Check basic settings
        assert hasattr(settings, 'output_dir')
        assert hasattr(settings, 'temp_dir')
        assert hasattr(settings, 'upload_dir')
        assert hasattr(settings, 'download_dir')
        
        print(f"✓ Settings initialized successfully")
        print(f"  - Output dir: {settings.output_dir}")
        print(f"  - Temp dir: {settings.temp_dir}")
        print(f"  - Upload dir: {settings.upload_dir}")
        print(f"  - Download dir: {settings.download_dir}")
        
        return True
        
    except Exception as e:
        print(f"✗ Settings error: {e}")
        return False

def test_engines():
    """Test engine availability."""
    print("\nTesting engines...")
    
    try:
        from whisper_subtitle.core.engines.registry import registry
        
        engines = registry.list_engines()
        
        print(f"✓ Found {len(engines)} engines:")
        for engine_name in engines:
            engine_info = registry.get_engine_info(engine_name)
            status = "Ready" if engine_info and engine_info.get('ready', False) else "Not Ready"
            print(f"  - {engine_name}: {status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Engine error: {e}")
        return False

def test_cli():
    """Test CLI functionality."""
    print("\nTesting CLI...")
    
    try:
        from whisper_subtitle.cli.main import cli
        
        # Test CLI help (this should not raise an exception)
        import click.testing
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        if result.exit_code == 0:
            print("✓ CLI help command works")
            return True
        else:
            print(f"✗ CLI help failed with exit code {result.exit_code}")
            return False
            
    except Exception as e:
        print(f"✗ CLI error: {e}")
        return False

def test_api():
    """Test API initialization."""
    print("\nTesting API...")
    
    try:
        from whisper_subtitle.api.main import app
        
        # Check if app is a FastAPI instance
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        
        print("✓ FastAPI app initialized successfully")
        print(f"  - Title: {app.title}")
        print(f"  - Version: {app.version}")
        
        return True
        
    except Exception as e:
        print(f"✗ API error: {e}")
        return False

def main():
    """Run all tests."""
    print("Whisper Subtitle Generator - Installation Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_settings,
        test_engines,
        test_cli,
        test_api,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The installation looks good.")
        print("\nNext steps:")
        print("1. Install speech recognition engines:")
        print("   pip install openai-whisper")
        print("   pip install faster-whisper")
        print("2. Start the server:")
        print("   python -m whisper_subtitle.cli server start")
        print("3. Or use the CLI:")
        print("   python -m whisper_subtitle.cli --help")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())