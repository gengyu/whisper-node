#!/usr/bin/env python3
"""Setup script for Whisper Subtitle Generator."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8') if (this_directory / "README.md").exists() else ""

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="whisper-subtitle",
    version="0.1.0",
    description="A comprehensive subtitle generation tool using multiple speech recognition engines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Whisper Subtitle Team",
    author_email="contact@whispersubtitle.com",
    url="https://github.com/whisper-subtitle/whisper-subtitle",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "whisper_subtitle.web": ["*.html", "*.css", "*.js"],
        "whisper_subtitle.config": ["*.yaml", "*.yml"],
    },
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "openai": [
            "openai-whisper>=20231117",
        ],
        "faster": [
            "faster-whisper>=0.9.0",
        ],
        "whisperkit": [
            # WhisperKit dependencies will be added when available
        ],
        "whispercpp": [
            "whispercpp>=1.0.0",
        ],
        "alibaba": [
            "alibabacloud-nls-python-sdk>=1.0.0",
        ],
        "youtube": [
            "yt-dlp>=2023.11.16",
        ],
        "all": [
            "openai-whisper>=20231117",
            "faster-whisper>=0.9.0",
            "whispercpp>=1.0.0",
            "alibabacloud-nls-python-sdk>=1.0.0",
            "yt-dlp>=2023.11.16",
        ],
    },
    entry_points={
        "console_scripts": [
            "whisper-subtitle=whisper_subtitle.cli.main:cli",
            "wst=whisper_subtitle.cli.main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="whisper subtitle transcription speech-recognition audio video",
    project_urls={
        "Bug Reports": "https://github.com/whisper-subtitle/whisper-subtitle/issues",
        "Source": "https://github.com/whisper-subtitle/whisper-subtitle",
        "Documentation": "https://whisper-subtitle.readthedocs.io/",
    },
)