#!/usr/bin/env python3
"""Build desktop application using PyInstaller."""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def build_desktop_app():
    """Build desktop application for current platform."""
    print("Building Whisper Subtitle Generator Desktop App...")
    
    # Get current directory
    project_dir = Path(__file__).parent
    src_dir = project_dir / "src"
    
    # Create build directory
    build_dir = project_dir / "build"
    dist_dir = project_dir / "dist"
    
    # Clean previous builds
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # Create main entry point for desktop app
    desktop_main = project_dir / "desktop_main.py"
    
    desktop_main_content = '''#!/usr/bin/env python3
"""Desktop application entry point."""

import sys
import os
import threading
import webbrowser
import time
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from whisper_subtitle.api.main import app
from whisper_subtitle.config.settings import settings
import uvicorn


def start_server():
    """Start the FastAPI server."""
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )


def open_browser():
    """Open browser after server starts."""
    time.sleep(2)  # Wait for server to start
    webbrowser.open("http://127.0.0.1:8000")


def main():
    """Main entry point for desktop app."""
    print("Starting Whisper Subtitle Generator...")
    
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start server (this will block)
    start_server()


if __name__ == "__main__":
    main()
'''
    
    with open(desktop_main, 'w', encoding='utf-8') as f:
        f.write(desktop_main_content)
    
    # PyInstaller command
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "WhisperSubtitleGenerator",
        "--icon", "icon.ico" if os.name == 'nt' else "icon.icns",
        "--add-data", f"{src_dir}{os.pathsep}src",
        "--add-data", f"{src_dir}/whisper_subtitle/web{os.pathsep}whisper_subtitle/web",
        "--hidden-import", "whisper_subtitle",
        "--hidden-import", "whisper_subtitle.api",
        "--hidden-import", "whisper_subtitle.cli",
        "--hidden-import", "whisper_subtitle.core",
        "--hidden-import", "whisper_subtitle.engines",
        "--hidden-import", "whisper_subtitle.tasks",
        "--hidden-import", "whisper_subtitle.utils",
        "--hidden-import", "uvicorn",
        "--hidden-import", "fastapi",
        "--collect-all", "whisper_subtitle",
        str(desktop_main)
    ]
    
    # Remove icon parameter if icon files don't exist
    icon_ico = project_dir / "icon.ico"
    icon_icns = project_dir / "icon.icns"
    if not icon_ico.exists() and not icon_icns.exists():
        # Remove icon parameters
        pyinstaller_cmd = [cmd for cmd in pyinstaller_cmd if not cmd.endswith(('.ico', '.icns'))]
        pyinstaller_cmd = [cmd for cmd in pyinstaller_cmd if cmd != '--icon']
    
    print(f"Running: {' '.join(pyinstaller_cmd)}")
    
    try:
        subprocess.run(pyinstaller_cmd, check=True, cwd=project_dir)
        print("\n✅ Desktop application built successfully!")
        print(f"📁 Application location: {dist_dir}")
        
        # Platform-specific instructions
        if sys.platform == "darwin":
            print("🍎 macOS: Run the .app file in the dist folder")
        elif sys.platform == "win32":
            print("🪟 Windows: Run the .exe file in the dist folder")
        else:
            print("🐧 Linux: Run the executable file in the dist folder")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ PyInstaller not found. Install it with: pip install pyinstaller")
        return False
    
    # Clean up
    if desktop_main.exists():
        desktop_main.unlink()
    
    return True


if __name__ == "__main__":
    success = build_desktop_app()
    sys.exit(0 if success else 1)