# Whisper Subtitle Generator Makefile

.PHONY: help install dev-install test lint format check clean build docker run stop logs

# Default target
help:
	@echo "Whisper Subtitle Generator - Available Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  install      - Install the project and dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  clean        - Clean build artifacts and cache"
	@echo ""
	@echo "Development:"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  check        - Run all quality checks"
	@echo ""
	@echo "Build:"
	@echo "  build        - Build desktop applications"
	@echo "  docker       - Build Docker image"
	@echo ""
	@echo "Run:"
	@echo "  run          - Start the web server"
	@echo "  run-dev      - Start development server with reload"
	@echo "  stop         - Stop the server"
	@echo "  logs         - Show server logs"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up    - Start with docker-compose"
	@echo "  docker-down  - Stop docker-compose"
	@echo "  docker-logs  - Show docker logs"

# Installation
install:
	@echo "Installing Whisper Subtitle Generator..."
	python install.py

dev-install: install
	@echo "Installing development dependencies..."
	pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy pre-commit
	pre-commit install

# Testing
test:
	@echo "Running tests..."
	python test_installation.py
	@if [ -d "tests" ]; then \
		pytest tests/ -v --cov=whisper_subtitle --cov-report=term-missing; \
	else \
		echo "No tests directory found, skipping pytest"; \
	fi

# Code quality
lint:
	@echo "Running linting checks..."
	flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
	@if command -v mypy >/dev/null 2>&1; then \
		mypy src/ --ignore-missing-imports; \
	else \
		echo "mypy not installed, skipping type checking"; \
	fi

format:
	@echo "Formatting code..."
	black src/
	isort src/
	@echo "Code formatting completed"

check: format lint test
	@echo "All quality checks completed"

# Build
build:
	@echo "Building desktop applications..."
	python build_app.py

docker:
	@echo "Building Docker image..."
	docker build -t whisper-subtitle:latest .

# Run
run:
	@echo "Starting Whisper Subtitle Generator server..."
	python -m whisper_subtitle.cli server start

run-dev:
	@echo "Starting development server with reload..."
	python -m whisper_subtitle.cli server start --reload --debug

stop:
	@echo "Stopping server..."
	python -m whisper_subtitle.cli server stop

logs:
	@echo "Showing server logs..."
	tail -f logs/whisper_subtitle.log 2>/dev/null || echo "No log file found"

# Docker operations
docker-up:
	@echo "Starting with docker-compose..."
	docker-compose up -d

docker-down:
	@echo "Stopping docker-compose..."
	docker-compose down

docker-logs:
	@echo "Showing docker logs..."
	docker-compose logs -f

docker-dev:
	@echo "Starting development environment with docker-compose..."
	docker-compose --profile dev up -d

# Cleanup
clean:
	@echo "Cleaning build artifacts and cache..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Cleanup completed"

# Quick commands
quick-test: format lint
	@echo "Quick test completed"

quick-start: install run
	@echo "Quick start completed"

# Help for specific engines
engines:
	@echo "Available Speech Recognition Engines:"
	@echo ""
	@echo "  openai_whisper  - OpenAI Whisper (all platforms)"
	@echo "  faster_whisper  - Faster Whisper (Windows/Linux)"
	@echo "  whisperkit      - WhisperKit (macOS M-series)"
	@echo "  whisper_cpp     - Whisper.cpp (all platforms)"
	@echo "  alibaba_asr     - Alibaba Cloud ASR (all platforms)"
	@echo ""
	@echo "Install specific engine:"
	@echo "  pip install -e '.[openai]'     # OpenAI Whisper"
	@echo "  pip install -e '.[faster]'     # Faster Whisper"
	@echo "  pip install -e '.[youtube]'    # YouTube support"
	@echo "  pip install -e '.[alibaba]'    # Alibaba ASR"
	@echo "  pip install -e '.[all]'        # All engines"

# System info
info:
	@echo "System Information:"
	@echo "Python version: $$(python --version)"
	@echo "Platform: $$(python -c 'import platform; print(platform.system())')"
	@echo "Architecture: $$(python -c 'import platform; print(platform.machine())')"
	@if command -v ffmpeg >/dev/null 2>&1; then \
		echo "FFmpeg: $$(ffmpeg -version | head -n1)"; \
	else \
		echo "FFmpeg: Not installed"; \
	fi
	@if [ -f ".env" ]; then \
		echo "Configuration: .env file found"; \
	else \
		echo "Configuration: .env file not found"; \
	fi

# Release
release:
	@echo "Preparing release..."
	make check
	make build
	make docker
	@echo "Release preparation completed"

# Development workflow
dev: dev-install
	@echo "Development environment ready!"
	@echo "Run 'make run-dev' to start the development server"

# CI/CD simulation
ci: clean dev-install check
	@echo "CI pipeline simulation completed"