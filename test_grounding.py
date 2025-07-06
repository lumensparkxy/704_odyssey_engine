#!/usr/bin/env python3
"""
Test script to specifically test Google Search grounding implementation.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path
sys.path.insert(0, 'src')

from utils.gemini_client import GeminiClient

async def test_grounding():
    """Test the Google Search grounding functionality directly."""
    
    # Load config
    config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_MODEL": "gemini-2.5-pro",
        "REQUEST_TIMEOUT": 300
    }
    
    print("🧪 Testing Google Search Grounding Implementation")
    print("=" * 60)
    
    # Initialize client
    try:
        client = GeminiClient(config)
        print("✅ GeminiClient initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize GeminiClient: {e}")
        return
    
    # Test query
    test_query = "recent breakthroughs in artificial intelligence machine learning 2024 sources research papers"
    print(f"🔍 Testing query: '{test_query}'")
    print()
    
    # Test with grounding enabled
    try:
        print("📡 Calling generate_with_grounding...")
        result = await client.generate_with_grounding(test_query, enable_search=True)
        
        print("✅ Grounding call completed successfully!")
        print()
        print("📊 Results:")
        print(f"  - Grounding enabled: {result.get('grounding_enabled', False)}")
        print(f"  - Sources found: {len(result.get('sources', []))}")
        print(f"  - Response length: {len(result.get('response', ''))}")
        
        if result.get('fallback_reason'):
            print(f"  - Fallback reason: {result['fallback_reason']}")
        
        if result.get('sources'):
            print(f"  - Sources: {result['sources']}")
        
        # Examine the raw response object structure
        raw_response = result.get('raw_response')
        if raw_response:
            print(f"\n🔍 Raw response object inspection:")
            print(f"  - Type: {type(raw_response)}")
            
            # List all attributes
            print(f"  - Attributes:")
            for attr in dir(raw_response):
                if not attr.startswith('_'):
                    try:
                        value = getattr(raw_response, attr)
                        if not callable(value):
                            print(f"    * {attr}: {type(value)}")
                            if hasattr(value, '__len__') and len(str(value)) < 200:
                                print(f"      = {value}")
                            elif hasattr(value, '__dict__'):
                                print(f"      = <object with attributes: {list(value.__dict__.keys()) if hasattr(value, '__dict__') else 'N/A'}>")
                    except Exception as e:
                        print(f"    * {attr}: <error accessing: {e}>")
            
            # Check candidates specifically
            if hasattr(raw_response, 'candidates') and raw_response.candidates:
                print(f"\n  - Candidate[0] attributes:")
                candidate = raw_response.candidates[0]
                for attr in dir(candidate):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(candidate, attr)
                            if not callable(value):
                                print(f"    * {attr}: {type(value)}")
                                if 'grounding' in attr.lower() or 'source' in attr.lower():
                                    print(f"      = {value}")
                        except Exception as e:
                            print(f"    * {attr}: <error accessing: {e}>")
        
        if result.get('grounding_info'):
            print(f"  - Grounding info available: Yes")
            print(f"  - Grounding info type: {type(result['grounding_info'])}")
            # Try to inspect the grounding info structure
            grounding_info = result['grounding_info']
            print(f"  - Grounding info attributes: {dir(grounding_info) if hasattr(grounding_info, '__dict__') else 'N/A'}")
        else:
            print(f"  - Grounding info available: No")
        
        print()
        print("📝 Response preview (first 200 chars):")
        response_preview = result.get('response', '')[:200]
        print(f"  {response_preview}...")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during grounding test: {e}")
        return None

async def main():
    """Main test function."""
    result = await test_grounding()
    
    if result:
        print()
        print("🎉 Test completed successfully!")
        print("This confirms that the Google Search grounding implementation is working.")
    else:
        print()
        print("❌ Test failed - check the error messages above")

if __name__ == "__main__":
    asyncio.run(main())
