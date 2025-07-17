"""YouTube monitoring CLI commands."""

import asyncio
import sys
from typing import Optional, Dict, Any

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def get_client(host: str, port: int, timeout: int) -> httpx.Client:
    """Get HTTP client for API requests."""
    base_url = f"http://{host}:{port}"
    return httpx.Client(base_url=base_url, timeout=timeout)


@click.group()
def youtube():
    """YouTube channel monitoring and processing commands."""
    pass


@youtube.command()
@click.argument('channel_id')
@click.argument('channel_name')
@click.option(
    '--engine', '-e',
    type=click.Choice(['openai_whisper', 'faster_whisper', 'whisperkit', 'whispercpp', 'alibaba_asr']),
    default='openai_whisper',
    help='Speech recognition engine to use'
)
@click.option(
    '--model', '-m',
    help='Model to use for transcription'
)
@click.option(
    '--language', '-l',
    default='auto',
    help='Language code for transcription'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['srt', 'vtt', 'txt']),
    default='srt',
    help='Output format for transcriptions'
)
@click.option(
    '--host',
    default='127.0.0.1',
    help='API server host'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='API server port'
)
@click.option(
    '--timeout',
    type=int,
    default=30,
    help='Request timeout in seconds'
)
@click.pass_context
def add(
    ctx,
    channel_id: str,
    channel_name: str,
    engine: str,
    model: Optional[str],
    language: str,
    format: str,
    host: str,
    port: int,
    timeout: int
):
    """Add a YouTube channel for monitoring.
    
    CHANNEL_ID: YouTube channel ID or username (e.g., @channelname)
    CHANNEL_NAME: Display name for the channel
    """
    
    transcription_config = {
        "engine": engine,
        "language": language,
        "output_format": format
    }
    
    if model:
        transcription_config["model"] = model
    
    request_data = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "transcription_config": transcription_config
    }
    
    try:
        with get_client(host, port, timeout) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Adding YouTube channel...", total=None)
                
                response = client.post("/api/v1/youtube/channels", json=request_data)
                
                progress.stop()
                
                if response.status_code == 200:
                    data = response.json()
                    console.print(f"[green]✓ {data['message']}[/green]")
                    
                    # Show configuration
                    config_table = Table(show_header=False, box=None)
                    config_table.add_row("[bold]Channel ID:[/bold]", channel_id)
                    config_table.add_row("[bold]Channel Name:[/bold]", channel_name)
                    config_table.add_row("[bold]Engine:[/bold]", engine)
                    config_table.add_row("[bold]Model:[/bold]", model or "default")
                    config_table.add_row("[bold]Language:[/bold]", language)
                    config_table.add_row("[bold]Format:[/bold]", format)
                    
                    console.print(Panel(config_table, title="Channel Configuration", border_style="green"))
                    
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('detail', f"HTTP {response.status_code}")
                    console.print(f"[red]✗ Failed to add channel: {error_msg}[/red]")
                    sys.exit(1)
                    
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to API server at {host}:{port}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error adding channel: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@youtube.command()
@click.option(
    '--host',
    default='127.0.0.1',
    help='API server host'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='API server port'
)
@click.option(
    '--timeout',
    type=int,
    default=30,
    help='Request timeout in seconds'
)
@click.pass_context
def list(
    ctx,
    host: str,
    port: int,
    timeout: int
):
    """List all monitored YouTube channels."""
    
    try:
        with get_client(host, port, timeout) as client:
            response = client.get("/api/v1/youtube/channels")
            
            if response.status_code == 200:
                channels = response.json()
                
                if not channels:
                    console.print("[yellow]No YouTube channels are being monitored[/yellow]")
                    return
                
                # Create table
                table = Table()
                table.add_column("Channel ID", style="bold")
                table.add_column("Name")
                table.add_column("Status")
                table.add_column("Last Check")
                table.add_column("Engine")
                table.add_column("Language")
                
                for channel in channels:
                    status = "[green]Enabled[/green]" if channel['enabled'] else "[red]Disabled[/red]"
                    last_check = channel['last_check'] or "Never"
                    if last_check != "Never":
                        # Format datetime
                        from datetime import datetime
                        try:
                            dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                            last_check = dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            pass
                    
                    config = channel.get('transcription_config', {})
                    engine = config.get('engine', 'Unknown')
                    language = config.get('language', 'Unknown')
                    
                    table.add_row(
                        channel['channel_id'],
                        channel['channel_name'],
                        status,
                        last_check,
                        engine,
                        language
                    )
                
                console.print(Panel(table, title="Monitored YouTube Channels", border_style="blue"))
                
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('detail', f"HTTP {response.status_code}")
                console.print(f"[red]✗ Failed to list channels: {error_msg}[/red]")
                sys.exit(1)
                
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to API server at {host}:{port}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error listing channels: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@youtube.command()
@click.argument('channel_id')
@click.option(
    '--host',
    default='127.0.0.1',
    help='API server host'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='API server port'
)
@click.option(
    '--timeout',
    type=int,
    default=30,
    help='Request timeout in seconds'
)
@click.pass_context
def remove(
    ctx,
    channel_id: str,
    host: str,
    port: int,
    timeout: int
):
    """Remove a YouTube channel from monitoring.
    
    CHANNEL_ID: YouTube channel ID to remove
    """
    
    try:
        with get_client(host, port, timeout) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Removing YouTube channel...", total=None)
                
                response = client.delete(f"/api/v1/youtube/channels/{channel_id}")
                
                progress.stop()
                
                if response.status_code == 200:
                    data = response.json()
                    console.print(f"[green]✓ {data['message']}[/green]")
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('detail', f"HTTP {response.status_code}")
                    console.print(f"[red]✗ Failed to remove channel: {error_msg}[/red]")
                    sys.exit(1)
                    
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to API server at {host}:{port}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error removing channel: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@youtube.command()
@click.argument('channel_id')
@click.option(
    '--enable/--disable',
    default=True,
    help='Enable or disable the channel'
)
@click.option(
    '--host',
    default='127.0.0.1',
    help='API server host'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='API server port'
)
@click.option(
    '--timeout',
    type=int,
    default=30,
    help='Request timeout in seconds'
)
@click.pass_context
def enable(
    ctx,
    channel_id: str,
    enable: bool,
    host: str,
    port: int,
    timeout: int
):
    """Enable or disable a YouTube channel.
    
    CHANNEL_ID: YouTube channel ID to enable/disable
    """
    
    try:
        with get_client(host, port, timeout) as client:
            action = "Enabling" if enable else "Disabling"
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"{action} YouTube channel...", total=None)
                
                response = client.put(
                    f"/api/v1/youtube/channels/{channel_id}/enable",
                    params={"enabled": enable}
                )
                
                progress.stop()
                
                if response.status_code == 200:
                    data = response.json()
                    console.print(f"[green]✓ {data['message']}[/green]")
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('detail', f"HTTP {response.status_code}")
                    console.print(f"[red]✗ Failed to update channel: {error_msg}[/red]")
                    sys.exit(1)
                    
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to API server at {host}:{port}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error updating channel: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@youtube.command()
@click.option(
    '--host',
    default='127.0.0.1',
    help='API server host'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='API server port'
)
@click.option(
    '--timeout',
    type=int,
    default=60,
    help='Request timeout in seconds'
)
@click.pass_context
def check(
    ctx,
    host: str,
    port: int,
    timeout: int
):
    """Manually check all channels for new videos."""
    
    try:
        with get_client(host, port, timeout) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Checking channels for new videos...", total=None)
                
                response = client.post("/api/v1/youtube/channels/check")
                
                progress.stop()
                
                if response.status_code == 200:
                    data = response.json()
                    console.print(f"[green]✓ {data['message']}[/green]")
                    
                    results = data.get('results', [])
                    if results:
                        # Show results
                        for result in results:
                            videos = result.get('videos_found', [])
                            if videos:
                                console.print(f"\n[bold]{result['channel_name']}:[/bold]")
                                for video in videos:
                                    console.print(f"  • {video['title']}")
                                    console.print(f"    [dim]URL: {video['url']}[/dim]")
                            else:
                                console.print(f"\n[dim]{result['channel_name']}: No new videos[/dim]")
                    else:
                        console.print("[dim]No new videos found in any channel[/dim]")
                        
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('detail', f"HTTP {response.status_code}")
                    console.print(f"[red]✗ Failed to check channels: {error_msg}[/red]")
                    sys.exit(1)
                    
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to API server at {host}:{port}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error checking channels: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@youtube.command()
@click.option(
    '--status',
    type=click.Choice(['pending', 'running', 'completed', 'failed', 'cancelled']),
    help='Filter tasks by status'
)
@click.option(
    '--limit',
    type=int,
    default=20,
    help='Maximum number of tasks to show'
)
@click.option(
    '--host',
    default='127.0.0.1',
    help='API server host'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='API server port'
)
@click.option(
    '--timeout',
    type=int,
    default=30,
    help='Request timeout in seconds'
)
@click.pass_context
def tasks(
    ctx,
    status: Optional[str],
    limit: int,
    host: str,
    port: int,
    timeout: int
):
    """List YouTube-related tasks."""
    
    try:
        with get_client(host, port, timeout) as client:
            params = {'limit': limit}
            if status:
                params['status'] = status
                
            response = client.get("/api/v1/youtube/tasks", params=params)
            
            if response.status_code == 200:
                tasks = response.json()
                
                if not tasks:
                    filter_msg = f" with status '{status}'" if status else ""
                    console.print(f"[yellow]No YouTube tasks found{filter_msg}[/yellow]")
                    return
                
                # Create table
                table = Table()
                table.add_column("ID", style="dim")
                table.add_column("Name")
                table.add_column("Status")
                table.add_column("Created")
                table.add_column("Duration")
                
                for task in tasks:
                    # Format status with color
                    task_status = task['status']
                    if task_status == 'completed':
                        status_display = "[green]Completed[/green]"
                    elif task_status == 'running':
                        status_display = "[blue]Running[/blue]"
                    elif task_status == 'failed':
                        status_display = "[red]Failed[/red]"
                    elif task_status == 'cancelled':
                        status_display = "[yellow]Cancelled[/yellow]"
                    else:
                        status_display = task_status.title()
                    
                    # Format timestamps
                    from datetime import datetime
                    try:
                        created_dt = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
                        created = created_dt.strftime('%m-%d %H:%M')
                    except:
                        created = "Unknown"
                    
                    # Calculate duration
                    duration = "—"
                    if task.get('started_at') and task.get('completed_at'):
                        try:
                            start_dt = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(task['completed_at'].replace('Z', '+00:00'))
                            duration_seconds = (end_dt - start_dt).total_seconds()
                            duration = f"{duration_seconds:.1f}s"
                        except:
                            pass
                    
                    table.add_row(
                        task['id'][:8] + "...",  # Truncate ID
                        task['name'],
                        status_display,
                        created,
                        duration
                    )
                
                title = "YouTube Tasks"
                if status:
                    title += f" ({status.title()})"
                
                console.print(Panel(table, title=title, border_style="blue"))
                
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('detail', f"HTTP {response.status_code}")
                console.print(f"[red]✗ Failed to list tasks: {error_msg}[/red]")
                sys.exit(1)
                
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to API server at {host}:{port}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error listing tasks: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@youtube.command()
@click.option(
    '--host',
    default='127.0.0.1',
    help='API server host'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='API server port'
)
@click.option(
    '--timeout',
    type=int,
    default=30,
    help='Request timeout in seconds'
)
@click.pass_context
def status(
    ctx,
    host: str,
    port: int,
    timeout: int
):
    """Show YouTube monitoring status."""
    
    try:
        with get_client(host, port, timeout) as client:
            response = client.get("/api/v1/youtube/status")
            
            if response.status_code == 200:
                data = response.json()
                
                # Show status
                status_table = Table(show_header=False, box=None)
                status_table.add_row("[bold]Monitored Channels:[/bold]", str(data['channels']))
                status_table.add_row("[bold]Processed Videos:[/bold]", str(data['processed_videos']))
                status_table.add_row("[bold]Active Tasks:[/bold]", str(data['active_tasks']))
                status_table.add_row("[bold]Completed Tasks:[/bold]", str(data['completed_tasks']))
                status_table.add_row("[bold]Failed Tasks:[/bold]", str(data['failed_tasks']))
                
                console.print(Panel(status_table, title="YouTube Monitoring Status", border_style="blue"))
                
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('detail', f"HTTP {response.status_code}")
                console.print(f"[red]✗ Failed to get status: {error_msg}[/red]")
                sys.exit(1)
                
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to API server at {host}:{port}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error getting status: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@youtube.command()
@click.argument('url')
@click.option(
    '--engine', '-e',
    type=click.Choice(['openai_whisper', 'faster_whisper', 'whisperkit', 'whispercpp', 'alibaba_asr']),
    default='openai_whisper',
    help='Speech recognition engine to use'
)
@click.option(
    '--model', '-m',
    help='Model to use for transcription (e.g., tiny, base, small, medium, large)'
)
@click.option(
    '--language', '-l',
    help='Language code for transcription (auto-detect if not specified)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['srt', 'vtt', 'txt', 'json']),
    default='srt',
    help='Output format for transcription'
)
@click.option(
    '--output', '-o',
    help='Output file path (auto-generated if not specified)'
)
@click.pass_context
def transcribe(
    ctx,
    url: str,
    engine: str,
    model: Optional[str],
    language: Optional[str],
    format: str,
    output: Optional[str]
):
    """Transcribe a YouTube video directly.
    
    URL: YouTube video URL to transcribe
    """
    
    try:
        from ...core.transcriber import TranscriptionService
        from pathlib import Path
        import time
        
        console.print(f"[blue]Starting YouTube transcription...[/blue]")
        console.print(f"[dim]URL: {url}[/dim]")
        console.print(f"[dim]Engine: {engine}[/dim]")
        console.print(f"[dim]Model: {model or 'default'}[/dim]")
        console.print(f"[dim]Language: {language or 'auto-detect'}[/dim]")
        console.print(f"[dim]Format: {format}[/dim]")
        console.print()
        
        # Initialize transcription service
        service = TranscriptionService()
        
        # Prepare transcription parameters
        transcribe_kwargs = {}
        if model:
            transcribe_kwargs['model_name'] = model
        if language:
            transcribe_kwargs['language'] = language
        
        # Start transcription with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Downloading and transcribing...", total=None)
            
            start_time = time.time()
            
            # Run transcription
            result = asyncio.run(
                service.transcribe_youtube(
                    url=url,
                    engine_name=engine,
                    output_format=format,
                    **transcribe_kwargs
                )
            )
            
            progress.stop()
            
            end_time = time.time()
            duration = end_time - start_time
        
        # Handle output file
        if output:
            output_path = Path(output)
            if result.output_path != output_path:
                # Move/copy to specified output path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.move(str(result.output_path), str(output_path))
                result.output_path = output_path
        
        # Show success message
        console.print(f"[green]✓ Transcription completed: {result.output_path}[/green]")
        console.print(f"[dim]Processing time: {duration:.2f} seconds[/dim]")
        
        # Show preview of transcription
        if result.output_path.exists():
            console.print("\n[bold]First few lines of transcription:[/bold]")
            with open(result.output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:6]  # Show first 6 lines
                preview = ''.join(lines).strip()
                if preview:
                    console.print(f"[dim]{preview}[/dim]")
                    if len(lines) == 6:
                        console.print("[dim]...[/dim]")
        
        console.print(f"\n[green]🎉 YouTube transcription completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Transcription failed: {e}[/red]")
        if ctx.obj and ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)