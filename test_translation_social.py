#!/usr/bin/env python3
"""Test script for translation and social media services."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from whisper_subtitle.services.translation import TranslationService, TranslationConfig
from whisper_subtitle.services.social_media import SocialMediaService, MediaContent


async def test_translation_service():
    """Test translation service functionality."""
    print("\n🌐 Testing Translation Service")
    print("=" * 40)
    
    # Test without credentials (should show unavailable)
    translation_service = TranslationService()
    
    print(f"Translation service available: {translation_service.is_available()}")
    
    # Test supported languages
    languages = translation_service.get_supported_languages()
    print(f"Supported languages: {len(languages)} languages")
    print(f"Sample languages: {list(languages.items())[:5]}")
    
    # Test SRT parsing
    sample_srt = """1
00:00:01,000 --> 00:00:03,000
Hello, this is a test subtitle.

2
00:00:04,000 --> 00:00:06,000
This is the second subtitle line.

3
00:00:07,000 --> 00:00:09,000
And this is the third one.
"""
    
    entries = translation_service.parse_srt_content(sample_srt)
    print(f"\nParsed {len(entries)} subtitle entries:")
    for entry in entries:
        print(f"  {entry.index}: {entry.start_time} -> {entry.end_time} | {entry.text}")
    
    # Test formatting back to SRT
    formatted_srt = translation_service.format_srt_content(entries)
    print(f"\nFormatted SRT content (first 200 chars):")
    print(formatted_srt[:200] + "...")
    
    print("✅ Translation service basic functionality test completed")


async def test_social_media_service():
    """Test social media service functionality."""
    print("\n📱 Testing Social Media Service")
    print("=" * 40)
    
    # Test without credentials (should show unavailable platforms)
    social_service = SocialMediaService()
    
    available_platforms = social_service.get_available_platforms()
    print(f"Available platforms: {available_platforms}")
    
    # Test with mock configuration
    mock_config = {
        "youtube": {
            "api_key": "mock_api_key",
            "client_id": "mock_client_id",
            "client_secret": "mock_client_secret"
        },
        "twitter": {
            "api_key": "mock_api_key",
            "api_secret": "mock_api_secret",
            "access_token": "mock_access_token",
            "access_token_secret": "mock_access_token_secret"
        }
    }
    
    social_service_with_config = SocialMediaService(mock_config)
    available_platforms_with_config = social_service_with_config.get_available_platforms()
    print(f"Available platforms with mock config: {available_platforms_with_config}")
    
    # Test authentication
    auth_results = await social_service_with_config.authenticate_all()
    print(f"Authentication results: {auth_results}")
    
    # Test content creation
    test_content = MediaContent(
        title="Test Video Title",
        description="This is a test video description for social media publishing.",
        tags=["test", "video", "subtitle", "ai"],
        language="en"
    )
    
    print(f"\nTest content created:")
    print(f"  Title: {test_content.title}")
    print(f"  Description: {test_content.description[:50]}...")
    print(f"  Tags: {test_content.tags}")
    print(f"  Language: {test_content.language}")
    
    # Test publishing to available platforms
    if available_platforms_with_config:
        print(f"\nTesting publishing to platforms: {available_platforms_with_config}")
        
        results = await social_service_with_config.publish_to_multiple(
            available_platforms_with_config, test_content
        )
        
        print("Publishing results:")
        for result in results:
            status = "✅ Success" if result.success else "❌ Failed"
            print(f"  {result.platform}: {status}")
            if result.success:
                print(f"    URL: {result.url}")
                print(f"    Post ID: {result.post_id}")
            else:
                print(f"    Error: {result.error_message}")
    
    # Test history
    history = social_service_with_config.get_publish_history()
    print(f"\nPublish history: {len(history)} entries")
    
    print("✅ Social media service basic functionality test completed")


async def test_cli_integration():
    """Test CLI integration."""
    print("\n🖥️  Testing CLI Integration")
    print("=" * 40)
    
    # Test translation CLI help
    import subprocess
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "whisper_subtitle.cli", "translate", "--help"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Translation CLI help command works")
            print(f"Output preview: {result.stdout[:200]}...")
        else:
            print(f"❌ Translation CLI help failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Translation CLI test error: {e}")
    
    # Test social media CLI help
    try:
        result = subprocess.run(
            [sys.executable, "-m", "whisper_subtitle.cli", "social", "--help"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Social media CLI help command works")
            print(f"Output preview: {result.stdout[:200]}...")
        else:
            print(f"❌ Social media CLI help failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Social media CLI test error: {e}")
    
    print("✅ CLI integration test completed")


async def main():
    """Main test function."""
    print("🧪 Testing Translation and Social Media Services")
    print("=" * 60)
    
    try:
        await test_translation_service()
        await test_social_media_service()
        await test_cli_integration()
        
        print("\n🎉 All tests completed successfully!")
        print("\n📝 Next steps:")
        print("1. Configure Alibaba Cloud credentials for translation")
        print("2. Configure social media API credentials")
        print("3. Test with real translation and publishing")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)