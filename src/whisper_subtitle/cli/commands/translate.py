"""Translation CLI commands."""

import asyncio
import click
import logging
from pathlib import Path
from typing import Optional

from ...services.translation import TranslationService, TranslationConfig
from ...config.settings import get_settings

logger = logging.getLogger(__name__)


@click.group()
def translate():
    """Translation commands for subtitle files."""
    pass


@translate.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--source-lang', '-s', default='auto', help='Source language code (auto for auto-detection)')
@click.option('--target-lang', '-t', default='en', help='Target language code')
@click.option('--access-key-id', help='Alibaba Cloud Access Key ID')
@click.option('--access-key-secret', help='Alibaba Cloud Access Key Secret')
@click.option('--endpoint', default='mt.cn-hangzhou.aliyuncs.com', help='Alibaba Cloud endpoint')
@click.option('--region-id', default='cn-hangzhou', help='Alibaba Cloud region ID')
def file(input_file: Path, output_file: Path, source_lang: str, target_lang: str,
         access_key_id: Optional[str], access_key_secret: Optional[str],
         endpoint: str, region_id: str):
    """Translate a subtitle file.
    
    INPUT_FILE: Path to the input SRT file
    OUTPUT_FILE: Path to save the translated SRT file
    """
    async def _translate_file():
        try:
            # Get configuration
            settings = get_settings()
            
            # Use provided credentials or fall back to settings
            config = TranslationConfig(
                access_key_id=access_key_id or getattr(settings, 'ALIBABA_ACCESS_KEY_ID', None),
                access_key_secret=access_key_secret or getattr(settings, 'ALIBABA_ACCESS_KEY_SECRET', None),
                endpoint=endpoint,
                region_id=region_id
            )
            
            if not config.access_key_id or not config.access_key_secret:
                click.echo("Error: Alibaba Cloud credentials not provided. Use --access-key-id and --access-key-secret options or set environment variables.", err=True)
                return
            
            # Initialize translation service
            translation_service = TranslationService(config)
            
            if not translation_service.is_available():
                click.echo("Error: Translation service is not available. Please check your Alibaba Cloud configuration.", err=True)
                return
            
            click.echo(f"Translating {input_file} from {source_lang} to {target_lang}...")
            
            # Translate file
            success = await translation_service.translate_subtitle_file_path(
                str(input_file), str(output_file), source_lang, target_lang
            )
            
            if success:
                click.echo(f"✅ Translation completed successfully: {output_file}")
            else:
                click.echo("❌ Translation failed. Check logs for details.", err=True)
                
        except Exception as e:
            click.echo(f"❌ Translation error: {e}", err=True)
            logger.error(f"Translation error: {e}")
    
    # Run async function
    asyncio.run(_translate_file())


@translate.command()
@click.argument('text')
@click.option('--source-lang', '-s', default='auto', help='Source language code (auto for auto-detection)')
@click.option('--target-lang', '-t', default='en', help='Target language code')
@click.option('--access-key-id', help='Alibaba Cloud Access Key ID')
@click.option('--access-key-secret', help='Alibaba Cloud Access Key Secret')
@click.option('--endpoint', default='mt.cn-hangzhou.aliyuncs.com', help='Alibaba Cloud endpoint')
@click.option('--region-id', default='cn-hangzhou', help='Alibaba Cloud region ID')
def text(text: str, source_lang: str, target_lang: str,
         access_key_id: Optional[str], access_key_secret: Optional[str],
         endpoint: str, region_id: str):
    """Translate a single text.
    
    TEXT: Text to translate
    """
    async def _translate_text():
        try:
            # Get configuration
            settings = get_settings()
            
            # Use provided credentials or fall back to settings
            config = TranslationConfig(
                access_key_id=access_key_id or getattr(settings, 'ALIBABA_ACCESS_KEY_ID', None),
                access_key_secret=access_key_secret or getattr(settings, 'ALIBABA_ACCESS_KEY_SECRET', None),
                endpoint=endpoint,
                region_id=region_id
            )
            
            if not config.access_key_id or not config.access_key_secret:
                click.echo("Error: Alibaba Cloud credentials not provided. Use --access-key-id and --access-key-secret options or set environment variables.", err=True)
                return
            
            # Initialize translation service
            translation_service = TranslationService(config)
            
            if not translation_service.is_available():
                click.echo("Error: Translation service is not available. Please check your Alibaba Cloud configuration.", err=True)
                return
            
            click.echo(f"Translating text from {source_lang} to {target_lang}...")
            
            # Translate text
            translated_text = await translation_service.translate_text(text, source_lang, target_lang)
            
            click.echo(f"\n📝 Original: {text}")
            click.echo(f"🌐 Translated: {translated_text}")
                
        except Exception as e:
            click.echo(f"❌ Translation error: {e}", err=True)
            logger.error(f"Translation error: {e}")
    
    # Run async function
    asyncio.run(_translate_text())


@translate.command()
def languages():
    """List supported languages."""
    translation_service = TranslationService()
    supported_languages = translation_service.get_supported_languages()
    
    click.echo("\n🌐 Supported Languages:")
    click.echo("=" * 40)
    
    for code, name in supported_languages.items():
        click.echo(f"{code:8} - {name}")
    
    click.echo("\n💡 Use 'auto' for automatic language detection")


@translate.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument('output_dir', type=click.Path(path_type=Path))
@click.option('--source-lang', '-s', default='auto', help='Source language code (auto for auto-detection)')
@click.option('--target-lang', '-t', default='en', help='Target language code')
@click.option('--pattern', default='*.srt', help='File pattern to match (default: *.srt)')
@click.option('--access-key-id', help='Alibaba Cloud Access Key ID')
@click.option('--access-key-secret', help='Alibaba Cloud Access Key Secret')
@click.option('--endpoint', default='mt.cn-hangzhou.aliyuncs.com', help='Alibaba Cloud endpoint')
@click.option('--region-id', default='cn-hangzhou', help='Alibaba Cloud region ID')
def batch(input_dir: Path, output_dir: Path, source_lang: str, target_lang: str,
          pattern: str, access_key_id: Optional[str], access_key_secret: Optional[str],
          endpoint: str, region_id: str):
    """Translate multiple subtitle files in a directory.
    
    INPUT_DIR: Directory containing subtitle files
    OUTPUT_DIR: Directory to save translated files
    """
    async def _translate_batch():
        try:
            # Get configuration
            settings = get_settings()
            
            # Use provided credentials or fall back to settings
            config = TranslationConfig(
                access_key_id=access_key_id or getattr(settings, 'ALIBABA_ACCESS_KEY_ID', None),
                access_key_secret=access_key_secret or getattr(settings, 'ALIBABA_ACCESS_KEY_SECRET', None),
                endpoint=endpoint,
                region_id=region_id
            )
            
            if not config.access_key_id or not config.access_key_secret:
                click.echo("Error: Alibaba Cloud credentials not provided. Use --access-key-id and --access-key-secret options or set environment variables.", err=True)
                return
            
            # Initialize translation service
            translation_service = TranslationService(config)
            
            if not translation_service.is_available():
                click.echo("Error: Translation service is not available. Please check your Alibaba Cloud configuration.", err=True)
                return
            
            # Find subtitle files
            subtitle_files = list(input_dir.glob(pattern))
            
            if not subtitle_files:
                click.echo(f"No files found matching pattern '{pattern}' in {input_dir}")
                return
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            click.echo(f"Found {len(subtitle_files)} files to translate from {source_lang} to {target_lang}")
            
            # Translate each file
            successful = 0
            failed = 0
            
            for subtitle_file in subtitle_files:
                output_file = output_dir / f"{subtitle_file.stem}_{target_lang}{subtitle_file.suffix}"
                
                click.echo(f"\n📄 Translating: {subtitle_file.name}")
                
                success = await translation_service.translate_subtitle_file_path(
                    str(subtitle_file), str(output_file), source_lang, target_lang
                )
                
                if success:
                    click.echo(f"  ✅ Saved: {output_file.name}")
                    successful += 1
                else:
                    click.echo(f"  ❌ Failed: {subtitle_file.name}")
                    failed += 1
            
            click.echo(f"\n📊 Batch translation completed:")
            click.echo(f"  ✅ Successful: {successful}")
            click.echo(f"  ❌ Failed: {failed}")
                
        except Exception as e:
            click.echo(f"❌ Batch translation error: {e}", err=True)
            logger.error(f"Batch translation error: {e}")
    
    # Run async function
    asyncio.run(_translate_batch())


if __name__ == '__main__':
    translate()