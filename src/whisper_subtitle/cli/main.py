"""Main CLI entry point for the whisper subtitle generator."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler

from ..config.settings import settings
from .commands import transcribe, server, youtube, translate, social

console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration.
    
    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure rich logging
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_path=verbose
            )
        ]
    )
    
    # Reduce noise from external libraries
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("yt_dlp").setLevel(logging.WARNING)


@click.group()
@click.option(
    "--verbose", "-v", 
    is_flag=True, 
    help="Enable verbose logging"
)
@click.option(
    "--config", "-c", 
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file"
)
@click.pass_context
def cli(ctx, verbose: bool, config: Optional[Path]):
    """Whisper Subtitle Generator CLI.
    
    A powerful tool for generating subtitles from audio and video files
    using various speech recognition engines.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Setup logging
    setup_logging(verbose)
    
    # Load configuration if provided
    if config:
        try:
            # Load custom configuration
            # This would require implementing config file loading
            console.print(f"[yellow]Loading configuration from: {config}[/yellow]")
        except Exception as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
            sys.exit(1)
    
    # Store configuration in context
    ctx.obj['verbose'] = verbose
    ctx.obj['config'] = config
    
    # Ensure required directories exist
    try:
        settings.ensure_directories()
    except Exception as e:
        console.print(f"[red]Error creating directories: {e}[/red]")
        sys.exit(1)


# Add command groups
cli.add_command(transcribe.transcribe)
cli.add_command(server.server)
cli.add_command(youtube.youtube)
cli.add_command(translate.translate)
cli.add_command(social.social)


@cli.command()
@click.pass_context
def info(ctx):
    """Show system information and configuration."""
    from ..core.service import TranscriptionService
    
    console.print("[bold blue]Whisper Subtitle Generator[/bold blue]")
    console.print("[dim]A powerful tool for generating subtitles from audio and video files[/dim]\n")
    
    # Show configuration
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Upload directory: {settings.upload_dir}")
    console.print(f"  Output directory: {settings.output_dir}")
    console.print(f"  Temp directory: {settings.temp_dir}")
    console.print(f"  Max file size: {settings.max_file_size // (1024 * 1024)}MB")
    console.print(f"  CORS origins: {settings.cors_origins}")
    console.print()
    
    # Show available engines
    async def show_engines():
        try:
            service = TranscriptionService(settings)
            from ..core.engines.registry import registry
            engines_info = registry.get_all_engines_info()
            
            console.print("[bold]Available Engines:[/bold]")
            for engine_name, engine_info in engines_info.items():
                status = "[green]✓[/green]" if engine_info.get('ready', False) else "[red]✗[/red]"
                console.print(f"  {status} {engine_name}: {engine_info.get('description', 'No description')}")
                
                if engine_info.get('ready', False):
                    models = engine_info.get('models', [])
                    if models:
                        console.print(f"    Models: {', '.join(models[:5])}{'...' if len(models) > 5 else ''}")
            
        except Exception as e:
            console.print(f"[red]Error checking engines: {e}[/red]")
    
    # Run async function
    asyncio.run(show_engines())


@cli.command()
@click.option(
    "--engine", "-e",
    type=click.Choice(['openai_whisper', 'faster_whisper', 'whisperkit', 'whispercpp', 'alibaba_asr']),
    help="Speech recognition engine to check"
)
@click.pass_context
def check(ctx, engine: Optional[str]):
    """Check engine availability and models."""
    from ..core.service import TranscriptionService
    
    async def check_engines():
        try:
            service = TranscriptionService(settings)
            
            if engine:
                # Check specific engine
                console.print(f"[bold]Checking engine: {engine}[/bold]")
                
                try:
                    engine_instance = await service.get_engine(engine)
                    
                    if await engine_instance.is_ready():
                        console.print(f"[green]✓ {engine} is ready[/green]")
                        
                        # Show models
                        models = await engine_instance.get_available_models()
                        if models:
                            console.print(f"Available models: {', '.join(models)}")
                        
                        # Show languages
                        languages = await engine_instance.get_supported_languages()
                        if languages:
                            console.print(f"Supported languages: {', '.join(languages[:10])}{'...' if len(languages) > 10 else ''}")
                    else:
                        console.print(f"[red]✗ {engine} is not ready[/red]")
                        
                except Exception as e:
                    console.print(f"[red]✗ Error checking {engine}: {e}[/red]")
            else:
                # Check all engines
                from ..core.engines.registry import registry
                engines_info = registry.get_all_engines_info()
                
                console.print("[bold]Engine Status:[/bold]")
                for engine_name, engine_info in engines_info.items():
                    status = "[green]✓[/green]" if engine_info.get('ready', False) else "[red]✗[/red]"
                    console.print(f"  {status} {engine_name}")
                    
                    if not engine_info.get('ready', False) and 'error' in engine_info:
                        console.print(f"    [dim]Error: {engine_info['error']}[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(check_engines())


@cli.command()
@click.option(
    "--days", "-d",
    type=int,
    default=7,
    help="Remove files older than this many days"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting"
)
@click.pass_context
def cleanup(ctx, days: int, dry_run: bool):
    """Clean up old temporary and output files."""
    from datetime import datetime, timedelta
    import os
    
    cutoff_time = datetime.now() - timedelta(days=days)
    
    directories_to_clean = [
        settings.temp_dir,
        settings.output_dir,
        "downloads"  # YouTube downloads
    ]
    
    total_size = 0
    total_files = 0
    
    for directory in directories_to_clean:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
        
        console.print(f"[bold]Checking directory: {directory}[/bold]")
        
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                try:
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        total_files += 1
                        
                        size_str = f"{file_size / 1024 / 1024:.1f}MB" if file_size > 1024*1024 else f"{file_size / 1024:.1f}KB"
                        
                        if dry_run:
                            console.print(f"  [yellow]Would delete:[/yellow] {file_path.name} ({size_str})")
                        else:
                            console.print(f"  [red]Deleting:[/red] {file_path.name} ({size_str})")
                            file_path.unlink()
                            
                except Exception as e:
                    console.print(f"  [red]Error processing {file_path}: {e}[/red]")
    
    total_size_str = f"{total_size / 1024 / 1024:.1f}MB" if total_size > 1024*1024 else f"{total_size / 1024:.1f}KB"
    
    if dry_run:
        console.print(f"\n[yellow]Would delete {total_files} files ({total_size_str}) older than {days} days[/yellow]")
    else:
        console.print(f"\n[green]Deleted {total_files} files ({total_size_str}) older than {days} days[/green]")


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        if '--verbose' in sys.argv or '-v' in sys.argv:
            console.print_exception()
        sys.exit(1)


if __name__ == '__main__':
    main()