"""Server CLI commands."""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

import click
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...config.settings import settings

console = Console()


@click.command()
@click.option(
    '--host',
    default='127.0.0.1',
    help='Host to bind to'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='Port to bind to'
)
@click.option(
    '--reload',
    is_flag=True,
    help='Enable auto-reload for development'
)
@click.option(
    '--workers',
    type=int,
    default=1,
    help='Number of worker processes'
)
@click.option(
    '--log-level',
    type=click.Choice(['critical', 'error', 'warning', 'info', 'debug', 'trace']),
    default='info',
    help='Log level'
)
@click.option(
    '--access-log/--no-access-log',
    default=True,
    help='Enable/disable access log'
)
@click.option(
    '--ssl-keyfile',
    type=click.Path(exists=True, path_type=Path),
    help='SSL key file for HTTPS'
)
@click.option(
    '--ssl-certfile',
    type=click.Path(exists=True, path_type=Path),
    help='SSL certificate file for HTTPS'
)
@click.pass_context
def server(
    ctx,
    host: str,
    port: int,
    reload: bool,
    workers: int,
    log_level: str,
    access_log: bool,
    ssl_keyfile: Optional[Path],
    ssl_certfile: Optional[Path]
):
    """Start the Whisper Subtitle Generator API server."""
    
    # Validate SSL configuration
    if ssl_keyfile or ssl_certfile:
        if not (ssl_keyfile and ssl_certfile):
            console.print("[red]Both --ssl-keyfile and --ssl-certfile must be provided for HTTPS[/red]")
            sys.exit(1)
    
    # Show server configuration
    config_table = Table(show_header=False, box=None)
    config_table.add_row("[bold]Host:[/bold]", host)
    config_table.add_row("[bold]Port:[/bold]", str(port))
    config_table.add_row("[bold]Workers:[/bold]", str(workers))
    config_table.add_row("[bold]Log Level:[/bold]", log_level)
    config_table.add_row("[bold]Reload:[/bold]", "Yes" if reload else "No")
    config_table.add_row("[bold]Access Log:[/bold]", "Yes" if access_log else "No")
    
    if ssl_keyfile and ssl_certfile:
        config_table.add_row("[bold]SSL:[/bold]", "Enabled")
        config_table.add_row("[bold]Key File:[/bold]", str(ssl_keyfile))
        config_table.add_row("[bold]Cert File:[/bold]", str(ssl_certfile))
        protocol = "https"
    else:
        config_table.add_row("[bold]SSL:[/bold]", "Disabled")
        protocol = "http"
    
    console.print(Panel(config_table, title="Server Configuration", border_style="blue"))
    
    # Show URLs
    urls_table = Table(show_header=False, box=None)
    urls_table.add_row("[bold]API:[/bold]", f"{protocol}://{host}:{port}/api/v1")
    urls_table.add_row("[bold]Docs:[/bold]", f"{protocol}://{host}:{port}/docs")
    urls_table.add_row("[bold]Web UI:[/bold]", f"{protocol}://{host}:{port}/")
    urls_table.add_row("[bold]Health:[/bold]", f"{protocol}://{host}:{port}/health")
    
    console.print(Panel(urls_table, title="Available URLs", border_style="green"))
    
    # Show directories
    dirs_table = Table(show_header=False, box=None)
    dirs_table.add_row("[bold]Upload:[/bold]", str(settings.upload_dir))
    dirs_table.add_row("[bold]Output:[/bold]", str(settings.output_dir))
    dirs_table.add_row("[bold]Temp:[/bold]", str(settings.temp_dir))
    dirs_table.add_row("[bold]Downloads:[/bold]", "downloads")
    
    console.print(Panel(dirs_table, title="Working Directories", border_style="yellow"))
    
    console.print("\n[bold green]Starting server...[/bold green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    # Prepare uvicorn configuration
    config = {
        "app": "whisper_subtitle.api.main:app",
        "host": host,
        "port": port,
        "log_level": log_level,
        "access_log": access_log,
        "reload": reload,
    }
    
    # Add SSL configuration if provided
    if ssl_keyfile and ssl_certfile:
        config.update({
            "ssl_keyfile": str(ssl_keyfile),
            "ssl_certfile": str(ssl_certfile)
        })
    
    # Add workers only if not in reload mode
    if not reload and workers > 1:
        config["workers"] = workers
    
    try:
        # Run the server
        uvicorn.run(**config)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Server error: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@click.command()
@click.option(
    '--host',
    default='127.0.0.1',
    help='Host to bind to'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='Port to bind to'
)
@click.option(
    '--timeout',
    type=int,
    default=30,
    help='Timeout for health check in seconds'
)
@click.pass_context
def health(ctx, host: str, port: int, timeout: int):
    """Check server health status."""
    import httpx
    
    url = f"http://{host}:{port}/health"
    
    console.print(f"[dim]Checking server health at {url}...[/dim]")
    
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                console.print("[green]✓ Server is healthy[/green]")
                
                # Show server info
                info_table = Table(show_header=False, box=None)
                info_table.add_row("[bold]Status:[/bold]", data.get('status', 'unknown'))
                info_table.add_row("[bold]Timestamp:[/bold]", data.get('timestamp', 'unknown'))
                
                if 'uptime' in data:
                    info_table.add_row("[bold]Uptime:[/bold]", f"{data['uptime']:.1f}s")
                
                console.print(Panel(info_table, title="Server Health", border_style="green"))
                
            else:
                console.print(f"[red]✗ Server returned status code: {response.status_code}[/red]")
                sys.exit(1)
                
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to server at {url}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except httpx.TimeoutException:
        console.print(f"[red]✗ Health check timed out after {timeout}s[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Health check failed: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)


@click.command()
@click.option(
    '--host',
    default='127.0.0.1',
    help='Host to connect to'
)
@click.option(
    '--port', '-p',
    type=int,
    default=8000,
    help='Port to connect to'
)
@click.option(
    '--timeout',
    type=int,
    default=30,
    help='Timeout for requests in seconds'
)
@click.pass_context
def status(ctx, host: str, port: int, timeout: int):
    """Show detailed server status and statistics."""
    import httpx
    
    base_url = f"http://{host}:{port}"
    
    console.print(f"[dim]Fetching server status from {base_url}...[/dim]")
    
    try:
        with httpx.Client(timeout=timeout) as client:
            # Get API info
            info_response = client.get(f"{base_url}/api/v1/info")
            if info_response.status_code != 200:
                console.print(f"[red]✗ Cannot fetch server info: {info_response.status_code}[/red]")
                sys.exit(1)
            
            info_data = info_response.json()
            
            # Show basic info
            basic_table = Table(show_header=False, box=None)
            basic_table.add_row("[bold]Name:[/bold]", info_data.get('name', 'Unknown'))
            basic_table.add_row("[bold]Version:[/bold]", info_data.get('version', 'Unknown'))
            basic_table.add_row("[bold]Description:[/bold]", info_data.get('description', 'Unknown'))
            
            console.print(Panel(basic_table, title="Server Information", border_style="blue"))
            
            # Show engine status
            engines_response = client.get(f"{base_url}/api/v1/engines")
            if engines_response.status_code == 200:
                engines_data = engines_response.json()
                
                engines_table = Table()
                engines_table.add_column("Engine", style="bold")
                engines_table.add_column("Status")
                engines_table.add_column("Models")
                engines_table.add_column("Languages")
                
                for engine in engines_data:
                    status_icon = "[green]✓[/green]" if engine['ready'] else "[red]✗[/red]"
                    models_count = len(engine.get('models', []))
                    languages_count = len(engine.get('languages', []))
                    
                    engines_table.add_row(
                        engine['name'],
                        status_icon,
                        str(models_count),
                        str(languages_count)
                    )
                
                console.print(Panel(engines_table, title="Speech Recognition Engines", border_style="green"))
            
            # Show scheduler status if available
            scheduler_status = info_data.get('scheduler_status', {})
            if scheduler_status:
                scheduler_table = Table(show_header=False, box=None)
                scheduler_table.add_row("[bold]Running:[/bold]", "Yes" if scheduler_status.get('running') else "No")
                scheduler_table.add_row("[bold]Total Tasks:[/bold]", str(scheduler_status.get('total_tasks', 0)))
                scheduler_table.add_row("[bold]Pending:[/bold]", str(scheduler_status.get('pending_tasks', 0)))
                scheduler_table.add_row("[bold]Running:[/bold]", str(scheduler_status.get('running_tasks', 0)))
                scheduler_table.add_row("[bold]Completed:[/bold]", str(scheduler_status.get('completed_tasks', 0)))
                scheduler_table.add_row("[bold]Failed:[/bold]", str(scheduler_status.get('failed_tasks', 0)))
                
                console.print(Panel(scheduler_table, title="Task Scheduler", border_style="yellow"))
            
            # Show YouTube status if available
            youtube_status = info_data.get('youtube_status', {})
            if youtube_status:
                youtube_table = Table(show_header=False, box=None)
                youtube_table.add_row("[bold]Channels:[/bold]", str(youtube_status.get('channels', 0)))
                youtube_table.add_row("[bold]Processed Videos:[/bold]", str(youtube_status.get('processed_videos', 0)))
                youtube_table.add_row("[bold]Active Tasks:[/bold]", str(youtube_status.get('active_tasks', 0)))
                youtube_table.add_row("[bold]Completed Tasks:[/bold]", str(youtube_status.get('completed_tasks', 0)))
                youtube_table.add_row("[bold]Failed Tasks:[/bold]", str(youtube_status.get('failed_tasks', 0)))
                
                console.print(Panel(youtube_table, title="YouTube Monitoring", border_style="magenta"))
            
            console.print("[green]✓ Server status retrieved successfully[/green]")
            
    except httpx.ConnectError:
        console.print(f"[red]✗ Cannot connect to server at {base_url}[/red]")
        console.print("[dim]Make sure the server is running[/dim]")
        sys.exit(1)
    except httpx.TimeoutException:
        console.print(f"[red]✗ Request timed out after {timeout}s[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Status check failed: {e}[/red]")
        if ctx.obj.get('verbose'):
            console.print_exception()
        sys.exit(1)