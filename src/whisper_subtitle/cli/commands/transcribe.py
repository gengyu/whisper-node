"""Transcription CLI commands."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from ...core.service import TranscriptionService
from ...utils.subtitle import SubtitleProcessor

console = Console()


@click.command()
@click.argument('input_path', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file path (default: same as input with .srt extension)'
)
@click.option(
    '--engine', '-e',
    type=click.Choice(['openai_whisper', 'faster_whisper', 'whisperkit', 'whispercpp', 'alibaba_asr']),
    default='openai_whisper',
    help='Speech recognition engine to use'
)
@click.option(
    '--model', '-m',
    help='Model to use (default: base for most engines)'
)
@click.option(
    '--language', '-l',
    help='Language code (e.g., en, zh, auto for auto-detection)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['srt', 'vtt', 'txt']),
    default='srt',
    help='Output format'
)
@click.option(
    '--merge-short',
    is_flag=True,
    help='Merge short segments'
)
@click.option(
    '--split-long',
    is_flag=True,
    help='Split long segments'
)
@click.option(
    '--filter-segments',
    is_flag=True,
    help='Filter out very short or empty segments'
)
@click.option(
    '--min-duration',
    type=float,
    default=0.5,
    help='Minimum segment duration in seconds (for filtering)'
)
@click.option(
    '--max-duration',
    type=float,
    default=30.0,
    help='Maximum segment duration in seconds (for splitting)'
)
@click.option(
    '--max-chars',
    type=int,
    default=100,
    help='Maximum characters per segment (for splitting)'
)
@click.pass_context
def transcribe(
    ctx,
    input_path: Path,
    output: Optional[Path],
    engine: str,
    model: Optional[str],
    language: Optional[str],
    format: str,
    merge_short: bool,
    split_long: bool,
    filter_segments: bool,
    min_duration: float,
    max_duration: float,
    max_chars: int
):
    """Transcribe audio or video file to subtitles.
    
    INPUT_PATH: Path to the audio or video file to transcribe.
    """
    
    async def run_transcription():
        service = None
        try:
            # Initialize transcription service
            console.print("[bold blue]Initializing transcription service...[/bold blue]")
            service = TranscriptionService()
            
            # Check if engine is available
            engines = await service.get_available_engines()
            if engine not in engines:
                console.print(f"[red]Engine '{engine}' is not available[/red]")
                available = [name for name, info in engines.items() if info['ready']]
                if available:
                    console.print(f"Available engines: {', '.join(available)}")
                return False
            
            if not engines[engine]['ready']:
                console.print(f"[red]Engine '{engine}' is not ready[/red]")
                if 'error' in engines[engine]:
                    console.print(f"Error: {engines[engine]['error']}")
                return False
            
            # Set default model if not specified
            if not model:
                engine_instance = await service.get_engine(engine)
                available_models = await engine_instance.get_available_models()
                if available_models:
                    model = available_models[0]  # Use first available model
                    console.print(f"[dim]Using default model: {model}[/dim]")
            
            # Set default language if not specified
            if not language:
                language = 'auto'
                console.print(f"[dim]Using auto language detection[/dim]")
            
            # Determine output path
            if not output:
                output = input_path.with_suffix(f'.{format}')
            
            # Show transcription info
            info_table = Table(show_header=False, box=None)
            info_table.add_row("[bold]Input:[/bold]", str(input_path))
            info_table.add_row("[bold]Output:[/bold]", str(output))
            info_table.add_row("[bold]Engine:[/bold]", engine)
            info_table.add_row("[bold]Model:[/bold]", model or 'default')
            info_table.add_row("[bold]Language:[/bold]", language)
            info_table.add_row("[bold]Format:[/bold]", format)
            
            console.print(Panel(info_table, title="Transcription Settings", border_style="blue"))
            
            # Start transcription with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Transcribing...", total=None)
                
                try:
                    result = await service.transcribe_file(
                        file_path=str(input_path),
                        engine=engine,
                        model=model,
                        language=language,
                        output_format=format
                    )
                    
                    progress.update(task, completed=100, total=100)
                    
                except Exception as e:
                    progress.stop()
                    console.print(f"[red]Transcription failed: {e}[/red]")
                    return False
            
            if not result.success:
                console.print(f"[red]Transcription failed: {result.error}[/red]")
                return False
            
            # Post-process segments if requested
            segments = result.segments
            
            if filter_segments:
                console.print("[dim]Filtering segments...[/dim]")
                segments = SubtitleProcessor.filter_segments(
                    segments,
                    min_duration=min_duration,
                    min_chars=1
                )
            
            if merge_short:
                console.print("[dim]Merging short segments...[/dim]")
                segments = SubtitleProcessor.merge_short_segments(
                    segments,
                    max_duration=max_duration
                )
            
            if split_long:
                console.print("[dim]Splitting long segments...[/dim]")
                segments = SubtitleProcessor.split_long_segments(
                    segments,
                    max_duration=max_duration,
                    max_chars=max_chars
                )
            
            # Save output
            console.print(f"[dim]Saving to {output}...[/dim]")
            
            try:
                if format == 'srt':
                    content = SubtitleProcessor.segments_to_srt(segments)
                elif format == 'vtt':
                    content = SubtitleProcessor.segments_to_vtt(segments)
                else:  # txt
                    content = SubtitleProcessor.segments_to_text(segments)
                
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                console.print(f"[green]✓ Transcription completed successfully![/green]")
                console.print(f"[green]Output saved to: {output}[/green]")
                
                # Show statistics
                stats_table = Table(show_header=False, box=None)
                stats_table.add_row("[bold]Segments:[/bold]", str(len(segments)))
                stats_table.add_row("[bold]Duration:[/bold]", f"{result.duration:.1f}s" if result.duration else "Unknown")
                stats_table.add_row("[bold]Language:[/bold]", result.language or "Unknown")
                
                console.print(Panel(stats_table, title="Transcription Statistics", border_style="green"))
                
                return True
                
            except Exception as e:
                console.print(f"[red]Error saving output: {e}[/red]")
                return False
        
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            if ctx.obj.get('verbose'):
                console.print_exception()
            return False
        
        finally:
            if service:
                await service.cleanup()
    
    # Run the async function
    success = asyncio.run(run_transcription())
    if not success:
        sys.exit(1)


@click.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    help='Output directory (default: same as input)'
)
@click.option(
    '--pattern',
    default='*.{mp3,wav,flac,m4a,mp4,avi,mov,mkv}',
    help='File pattern to match'
)
@click.option(
    '--engine', '-e',
    type=click.Choice(['openai_whisper', 'faster_whisper', 'whisperkit', 'whispercpp', 'alibaba_asr']),
    default='openai_whisper',
    help='Speech recognition engine to use'
)
@click.option(
    '--model', '-m',
    help='Model to use'
)
@click.option(
    '--language', '-l',
    help='Language code'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['srt', 'vtt', 'txt']),
    default='srt',
    help='Output format'
)
@click.option(
    '--max-concurrent',
    type=int,
    default=2,
    help='Maximum concurrent transcriptions'
)
@click.option(
    '--skip-existing',
    is_flag=True,
    help='Skip files that already have transcriptions'
)
@click.pass_context
def batch(
    ctx,
    input_dir: Path,
    output_dir: Optional[Path],
    pattern: str,
    engine: str,
    model: Optional[str],
    language: Optional[str],
    format: str,
    max_concurrent: int,
    skip_existing: bool
):
    """Batch transcribe multiple files in a directory.
    
    INPUT_DIR: Directory containing audio/video files to transcribe.
    """
    
    async def run_batch_transcription():
        service = None
        try:
            # Find files to process
            extensions = ['mp3', 'wav', 'flac', 'm4a', 'mp4', 'avi', 'mov', 'mkv', 'webm']
            files = []
            
            for ext in extensions:
                files.extend(input_dir.glob(f'*.{ext}'))
                files.extend(input_dir.glob(f'*.{ext.upper()}'))
            
            if not files:
                console.print(f"[yellow]No audio/video files found in {input_dir}[/yellow]")
                return True
            
            # Set output directory
            if not output_dir:
                output_dir = input_dir
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # Filter out files that already have transcriptions
            if skip_existing:
                files_to_process = []
                for file_path in files:
                    output_path = output_dir / f"{file_path.stem}.{format}"
                    if not output_path.exists():
                        files_to_process.append(file_path)
                    else:
                        console.print(f"[dim]Skipping {file_path.name} (already exists)[/dim]")
                files = files_to_process
            
            if not files:
                console.print("[yellow]No files to process[/yellow]")
                return True
            
            console.print(f"[bold blue]Found {len(files)} files to transcribe[/bold blue]")
            
            # Initialize service
            service = TranscriptionService()
            
            # Process files with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                
                main_task = progress.add_task("Processing files...", total=len(files))
                
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def process_file(file_path: Path):
                    async with semaphore:
                        try:
                            output_path = output_dir / f"{file_path.stem}.{format}"
                            
                            result = await service.transcribe_file(
                                file_path=str(file_path),
                                engine=engine,
                                model=model,
                                language=language,
                                output_format=format
                            )
                            
                            if result.success:
                                # Save output
                                if format == 'srt':
                                    content = result.to_srt()
                                elif format == 'vtt':
                                    content = result.to_vtt()
                                else:
                                    content = result.to_text()
                                
                                with open(output_path, 'w', encoding='utf-8') as f:
                                    f.write(content)
                                
                                console.print(f"[green]✓ {file_path.name}[/green]")
                                return True
                            else:
                                console.print(f"[red]✗ {file_path.name}: {result.error}[/red]")
                                return False
                        
                        except Exception as e:
                            console.print(f"[red]✗ {file_path.name}: {e}[/red]")
                            return False
                        
                        finally:
                            progress.advance(main_task)
                
                # Process all files
                tasks = [process_file(file_path) for file_path in files]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successes
                successes = sum(1 for result in results if result is True)
                failures = len(files) - successes
                
                console.print(f"\n[bold]Batch transcription completed![/bold]")
                console.print(f"[green]Successful: {successes}[/green]")
                if failures > 0:
                    console.print(f"[red]Failed: {failures}[/red]")
                
                return failures == 0
        
        except Exception as e:
            console.print(f"[red]Batch transcription failed: {e}[/red]")
            if ctx.obj.get('verbose'):
                console.print_exception()
            return False
        
        finally:
            if service:
                await service.cleanup()
    
    # Run the async function
    success = asyncio.run(run_batch_transcription())
    if not success:
        sys.exit(1)