"""Social media CLI commands."""

import asyncio
import click
import logging
import json
from pathlib import Path
from typing import Optional, List

from ...services.social_media import SocialMediaService, MediaContent
from ...config.settings import get_settings

logger = logging.getLogger(__name__)


@click.group()
def social():
    """Social media integration commands."""
    pass


@social.command()
@click.option('--config-file', type=click.Path(exists=True, path_type=Path), help='Social media configuration file')
def platforms(config_file: Optional[Path]):
    """List available social media platforms."""
    try:
        config = {}
        if config_file:
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        service = SocialMediaService(config)
        available_platforms = service.get_available_platforms()
        
        click.echo("\n📱 Social Media Platforms:")
        click.echo("=" * 40)
        
        all_platforms = ['youtube', 'twitter']
        for platform in all_platforms:
            status = "✅ Available" if platform in available_platforms else "❌ Not configured"
            click.echo(f"{platform:10} - {status}")
        
        if not available_platforms:
            click.echo("\n💡 No platforms configured. Use 'wst social configure' to set up platforms.")
        
    except Exception as e:
        click.echo(f"❌ Error listing platforms: {e}", err=True)
        logger.error(f"Error listing platforms: {e}")


@social.command()
@click.argument('title')
@click.argument('description')
@click.option('--platforms', '-p', multiple=True, help='Target platforms (youtube, twitter)')
@click.option('--video-path', type=click.Path(exists=True, path_type=Path), help='Path to video file')
@click.option('--subtitle-path', type=click.Path(exists=True, path_type=Path), help='Path to subtitle file')
@click.option('--thumbnail-path', type=click.Path(exists=True, path_type=Path), help='Path to thumbnail image')
@click.option('--tags', help='Comma-separated tags')
@click.option('--language', default='en', help='Content language')
@click.option('--config-file', type=click.Path(exists=True, path_type=Path), help='Social media configuration file')
def publish(title: str, description: str, platforms: tuple, video_path: Optional[Path],
           subtitle_path: Optional[Path], thumbnail_path: Optional[Path], tags: Optional[str],
           language: str, config_file: Optional[Path]):
    """Publish content to social media platforms.
    
    TITLE: Content title
    DESCRIPTION: Content description
    """
    async def _publish_content():
        try:
            # Load configuration
            config = {}
            if config_file:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            
            # Initialize service
            service = SocialMediaService(config)
            
            # Parse tags
            tag_list = []
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',')]
            
            # Create media content
            content = MediaContent(
                title=title,
                description=description,
                video_path=str(video_path) if video_path else None,
                subtitle_path=str(subtitle_path) if subtitle_path else None,
                thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
                tags=tag_list,
                language=language
            )
            
            # Determine target platforms
            target_platforms = list(platforms) if platforms else service.get_available_platforms()
            
            if not target_platforms:
                click.echo("❌ No platforms specified or available. Configure platforms first.", err=True)
                return
            
            click.echo(f"📤 Publishing to platforms: {', '.join(target_platforms)}")
            click.echo(f"📝 Title: {title}")
            click.echo(f"📄 Description: {description[:100]}{'...' if len(description) > 100 else ''}")
            
            # Authenticate platforms
            auth_results = await service.authenticate_all()
            failed_auth = [platform for platform, success in auth_results.items() if not success]
            
            if failed_auth:
                click.echo(f"⚠️  Authentication failed for: {', '.join(failed_auth)}")
            
            # Publish to platforms
            results = await service.publish_to_multiple(target_platforms, content)
            
            # Display results
            click.echo("\n📊 Publishing Results:")
            click.echo("=" * 40)
            
            for result in results:
                if result.success:
                    click.echo(f"✅ {result.platform}: Published successfully")
                    if result.url:
                        click.echo(f"   🔗 URL: {result.url}")
                    if result.post_id:
                        click.echo(f"   🆔 ID: {result.post_id}")
                else:
                    click.echo(f"❌ {result.platform}: {result.error_message}")
                click.echo()
            
            # Save history
            history_file = Path.cwd() / "social_media_history.json"
            service.save_publish_history(str(history_file))
            click.echo(f"📝 Publishing history saved to: {history_file}")
            
        except Exception as e:
            click.echo(f"❌ Publishing error: {e}", err=True)
            logger.error(f"Publishing error: {e}")
    
    # Run async function
    asyncio.run(_publish_content())


@social.command()
@click.option('--platform', help='Filter by platform')
@click.option('--config-file', type=click.Path(exists=True, path_type=Path), help='Social media configuration file')
def history(platform: Optional[str], config_file: Optional[Path]):
    """Show publishing history."""
    try:
        # Load configuration
        config = {}
        if config_file:
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        # Initialize service
        service = SocialMediaService(config)
        
        # Load history
        history_file = Path.cwd() / "social_media_history.json"
        if history_file.exists():
            service.load_publish_history(str(history_file))
        
        # Get history
        publish_history = service.get_publish_history(platform)
        
        if not publish_history:
            click.echo("📭 No publishing history found.")
            return
        
        click.echo(f"\n📚 Publishing History{f' ({platform})' if platform else ''}:")
        click.echo("=" * 50)
        
        for i, result in enumerate(publish_history, 1):
            status = "✅ Success" if result.success else "❌ Failed"
            click.echo(f"{i:2}. {result.platform:10} - {status}")
            
            if result.success:
                if result.url:
                    click.echo(f"    🔗 URL: {result.url}")
                if result.post_id:
                    click.echo(f"    🆔 ID: {result.post_id}")
                if result.metadata and 'title' in result.metadata:
                    click.echo(f"    📝 Title: {result.metadata['title']}")
            else:
                click.echo(f"    ❌ Error: {result.error_message}")
            
            click.echo()
        
    except Exception as e:
        click.echo(f"❌ Error showing history: {e}", err=True)
        logger.error(f"Error showing history: {e}")


@social.command()
@click.argument('platform')
@click.argument('post_id')
@click.option('--config-file', type=click.Path(exists=True, path_type=Path), help='Social media configuration file')
def status(platform: str, post_id: str, config_file: Optional[Path]):
    """Check status of a published post.
    
    PLATFORM: Platform name (youtube, twitter)
    POST_ID: Post/video ID
    """
    async def _check_status():
        try:
            # Load configuration
            config = {}
            if config_file:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            
            # Initialize service
            service = SocialMediaService(config)
            
            # Check status
            post_status = await service.get_post_status(platform, post_id)
            
            if 'error' in post_status:
                click.echo(f"❌ Error: {post_status['error']}", err=True)
                return
            
            click.echo(f"\n📊 Post Status ({platform}):")
            click.echo("=" * 30)
            click.echo(f"🆔 ID: {post_id}")
            
            for key, value in post_status.items():
                if key != 'id':
                    click.echo(f"{key.title()}: {value}")
            
        except Exception as e:
            click.echo(f"❌ Status check error: {e}", err=True)
            logger.error(f"Status check error: {e}")
    
    # Run async function
    asyncio.run(_check_status())


@social.command()
@click.option('--output', '-o', type=click.Path(path_type=Path), default='social_config.json', help='Output configuration file')
def configure(output: Path):
    """Create a social media configuration file template."""
    try:
        config_template = {
            "youtube": {
                "api_key": "YOUR_YOUTUBE_API_KEY",
                "client_id": "YOUR_YOUTUBE_CLIENT_ID",
                "client_secret": "YOUR_YOUTUBE_CLIENT_SECRET"
            },
            "twitter": {
                "api_key": "YOUR_TWITTER_API_KEY",
                "api_secret": "YOUR_TWITTER_API_SECRET",
                "access_token": "YOUR_TWITTER_ACCESS_TOKEN",
                "access_token_secret": "YOUR_TWITTER_ACCESS_TOKEN_SECRET"
            }
        }
        
        with open(output, 'w') as f:
            json.dump(config_template, f, indent=2)
        
        click.echo(f"✅ Configuration template created: {output}")
        click.echo("\n📝 Please edit the file and add your API credentials:")
        click.echo(f"   nano {output}")
        click.echo("\n🔑 Required credentials:")
        click.echo("   YouTube: API key, Client ID, Client Secret")
        click.echo("   Twitter: API key, API secret, Access token, Access token secret")
        
    except Exception as e:
        click.echo(f"❌ Error creating configuration: {e}", err=True)
        logger.error(f"Error creating configuration: {e}")


if __name__ == '__main__':
    social()