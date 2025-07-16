#!/usr/bin/env python3
"""
Core Functionality Test for Whisper Subtitle Generator

This script tests the core functionality of the Whisper Subtitle Generator
to ensure all components are working correctly.
"""

import os
import sys
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def print_header(title: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_step(step: str, status: str = "RUNNING") -> None:
    """Print a test step with status."""
    status_colors = {
        "RUNNING": "\033[93m",  # Yellow
        "PASS": "\033[92m",     # Green
        "FAIL": "\033[91m",     # Red
        "SKIP": "\033[94m",     # Blue
    }
    reset_color = "\033[0m"
    color = status_colors.get(status, "")
    print(f"  {color}[{status:^7}]{reset_color} {step}")

def test_imports() -> bool:
    """Test if all core modules can be imported."""
    print_header("Testing Core Module Imports")
    
    modules_to_test = [
        "whisper_subtitle.config.settings",
        "whisper_subtitle.core.registry",
        "whisper_subtitle.core.transcription",
        "whisper_subtitle.engines.openai_whisper",
        "whisper_subtitle.engines.faster_whisper",
        "whisper_subtitle.engines.whisperkit",
        "whisper_subtitle.engines.whisper_cpp",
        "whisper_subtitle.engines.alibaba_asr",
        "whisper_subtitle.cli.main",
        "whisper_subtitle.api.main",
        "whisper_subtitle.tasks.scheduler",
        "whisper_subtitle.tasks.youtube",
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            print_step(f"Importing {module}", "RUNNING")
            __import__(module)
            print_step(f"Importing {module}", "PASS")
        except ImportError as e:
            print_step(f"Importing {module}: {e}", "FAIL")
            failed_imports.append(module)
        except Exception as e:
            print_step(f"Importing {module}: {e}", "FAIL")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import {len(failed_imports)} modules:")
        for module in failed_imports:
            print(f"   - {module}")
        return False
    
    print(f"\n✅ All {len(modules_to_test)} modules imported successfully!")
    return True

def test_settings() -> bool:
    """Test settings initialization."""
    print_header("Testing Settings Configuration")
    
    try:
        print_step("Initializing settings", "RUNNING")
        from whisper_subtitle.config.settings import Settings
        
        settings = Settings()
        print_step("Initializing settings", "PASS")
        
        # Test basic settings
        print_step(f"Host: {settings.host}", "PASS")
        print_step(f"Port: {settings.port}", "PASS")
        print_step(f"Debug: {settings.debug}", "PASS")
        print_step(f"Upload dir: {settings.uploads_dir}", "PASS")
        print_step(f"Output dir: {settings.output_dir}", "PASS")
        
        return True
        
    except Exception as e:
        print_step(f"Settings initialization failed: {e}", "FAIL")
        return False

def test_engine_registry() -> bool:
    """Test engine registry functionality."""
    print_header("Testing Engine Registry")
    
    try:
        print_step("Initializing engine registry", "RUNNING")
        from whisper_subtitle.core.registry import EngineRegistry
        from whisper_subtitle.config.settings import Settings
        
        settings = Settings()
        registry = EngineRegistry()
        print_step("Initializing engine registry", "PASS")
        
        # Test listing engines
        print_step("Listing available engines", "RUNNING")
        engines = registry.list_engines()
        print_step(f"Found {len(engines)} engines", "PASS")
        
        for engine_name in engines:
            print_step(f"  - {engine_name}", "PASS")
        
        # Test getting a specific engine
        if "openai_whisper" in engines:
            print_step("Getting OpenAI Whisper engine", "RUNNING")
            engine = registry.get_engine("openai_whisper")
            print_step("Getting OpenAI Whisper engine", "PASS")
        
        return True
        
    except Exception as e:
        print_step(f"Engine registry test failed: {e}", "FAIL")
        return False

def test_cli_commands() -> bool:
    """Test CLI command functionality."""
    print_header("Testing CLI Commands")
    
    commands_to_test = [
        ["python3", "-m", "whisper_subtitle.cli", "--help"],
        ["python3", "-m", "whisper_subtitle.cli", "info"],
        ["python3", "-m", "whisper_subtitle.cli", "check"],
    ]
    
    failed_commands = []
    
    for cmd in commands_to_test:
        cmd_str = " ".join(cmd)
        try:
            print_step(f"Running: {cmd_str}", "RUNNING")
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path(__file__).parent / "src")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(__file__).parent,
                env=env
            )
            
            if result.returncode == 0:
                print_step(f"Command succeeded: {cmd_str}", "PASS")
            else:
                print_step(f"Command failed: {cmd_str} (exit code: {result.returncode})", "FAIL")
                failed_commands.append(cmd_str)
                
        except subprocess.TimeoutExpired:
            print_step(f"Command timed out: {cmd_str}", "FAIL")
            failed_commands.append(cmd_str)
        except Exception as e:
            print_step(f"Command error: {cmd_str} - {e}", "FAIL")
            failed_commands.append(cmd_str)
    
    if failed_commands:
        print(f"\n❌ {len(failed_commands)} CLI commands failed:")
        for cmd in failed_commands:
            print(f"   - {cmd}")
        return False
    
    print(f"\n✅ All {len(commands_to_test)} CLI commands passed!")
    return True

def test_api_initialization() -> bool:
    """Test API initialization."""
    print_header("Testing API Initialization")
    
    try:
        print_step("Importing FastAPI app", "RUNNING")
        from whisper_subtitle.api.main import app
        print_step("Importing FastAPI app", "PASS")
        
        print_step("Checking app routes", "RUNNING")
        routes = [route.path for route in app.routes]
        print_step(f"Found {len(routes)} routes", "PASS")
        
        # Check for essential routes
        essential_routes = [
            "/",
            "/api/v1/health",
            "/api/v1/transcribe",
            "/api/v1/engines",
        ]
        
        missing_routes = []
        for route in essential_routes:
            if any(r.startswith(route) for r in routes):
                print_step(f"Route exists: {route}", "PASS")
            else:
                print_step(f"Route missing: {route}", "FAIL")
                missing_routes.append(route)
        
        if missing_routes:
            print(f"\n❌ Missing essential routes: {missing_routes}")
            return False
        
        return True
        
    except Exception as e:
        print_step(f"API initialization failed: {e}", "FAIL")
        return False

def test_directory_structure() -> bool:
    """Test if required directories exist or can be created."""
    print_header("Testing Directory Structure")
    
    try:
        from whisper_subtitle.config.settings import Settings
        settings = Settings()
        
        directories = [
            settings.uploads_dir,
            settings.downloads_dir,
            settings.output_dir,
            settings.temp_dir,
            settings.models_dir,
            settings.logs_dir,
            settings.bin_dir,
        ]
        
        for directory in directories:
            print_step(f"Checking directory: {directory}", "RUNNING")
            
            dir_path = Path(directory)
            if dir_path.exists():
                print_step(f"Directory exists: {directory}", "PASS")
            else:
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print_step(f"Directory created: {directory}", "PASS")
                except Exception as e:
                    print_step(f"Failed to create directory: {directory} - {e}", "FAIL")
                    return False
        
        return True
        
    except Exception as e:
        print_step(f"Directory structure test failed: {e}", "FAIL")
        return False

def test_ffmpeg_availability() -> bool:
    """Test if FFmpeg is available."""
    print_header("Testing FFmpeg Availability")
    
    try:
        print_step("Checking FFmpeg installation", "RUNNING")
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print_step(f"FFmpeg found: {version_line}", "PASS")
            return True
        else:
            print_step("FFmpeg not found or not working", "FAIL")
            return False
            
    except subprocess.TimeoutExpired:
        print_step("FFmpeg check timed out", "FAIL")
        return False
    except FileNotFoundError:
        print_step("FFmpeg not installed", "FAIL")
        return False
    except Exception as e:
        print_step(f"FFmpeg check failed: {e}", "FAIL")
        return False

def main() -> None:
    """Run all tests."""
    print("🎬 Whisper Subtitle Generator - Core Functionality Test")
    print("=" * 60)
    
    tests = [
        ("Module Imports", test_imports),
        ("Settings Configuration", test_settings),
        ("Engine Registry", test_engine_registry),
        ("Directory Structure", test_directory_structure),
        ("FFmpeg Availability", test_ffmpeg_availability),
        ("CLI Commands", test_cli_commands),
        ("API Initialization", test_api_initialization),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_step(f"Test {test_name} crashed: {e}", "FAIL")
            results.append((test_name, False))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print_step(test_name, status)
    
    print(f"\n{'='*60}")
    if passed == total:
        print(f"🎉 ALL TESTS PASSED! ({passed}/{total})")
        print("✅ Whisper Subtitle Generator is ready to use!")
        sys.exit(0)
    else:
        print(f"❌ SOME TESTS FAILED! ({passed}/{total} passed)")
        print("🔧 Please check the failed tests and fix any issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()