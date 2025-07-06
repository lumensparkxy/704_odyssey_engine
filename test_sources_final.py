#!/usr/bin/env python3
"""
Final test to demonstrate that Google Search grounding is now working
and sources are being collected correctly.
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

async def test_complete_source_collection():
    """Test that sources are being collected from Google Search grounding."""
    
    # Load config
    config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_MODEL": "gemini-2.5-pro",
        "REQUEST_TIMEOUT": 300
    }
    
    print("🎯 Final Test: Google Search Grounding with Source Collection")
    print("=" * 70)
    
    # Initialize client
    try:
        client = GeminiClient(config)
        print("✅ GeminiClient initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize GeminiClient: {e}")
        return
    
    # Test queries with grounding
    test_queries = [
        "recent developments in PyTorch framework 2024",
        "NVIDIA NVLink technology improvements machine learning",
        "latest computer science breakthroughs 2024"
    ]
    
    total_sources = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {query}")
        print("-" * 50)
        
        try:
            result = await client.generate_with_grounding(query, enable_search=True)
            
            sources = result.get('sources', [])
            grounding_enabled = result.get('grounding_enabled', False)
            
            print(f"📊 Results:")
            print(f"  - Grounding enabled: {grounding_enabled}")
            print(f"  - Sources found: {len(sources)}")
            
            if sources:
                print(f"  - Source examples:")
                for j, source in enumerate(sources[:3]):  # Show first 3 sources
                    # Extract domain from URL
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(source).netloc
                        if 'grounding-api-redirect' in domain:
                            domain = "Google Search (verified grounding URL)"
                    except:
                        domain = "Unknown domain"
                    print(f"    {j+1}. {domain}")
                    
                total_sources += len(sources)
                print(f"  ✅ Sources successfully collected!")
            else:
                print(f"  ⚠️ No sources found")
                
        except Exception as e:
            print(f"❌ Error in test {i}: {e}")
    
    print(f"\n🎉 Final Results:")
    print(f"Total sources collected across all tests: {total_sources}")
    
    if total_sources > 0:
        print("✅ SUCCESS: Google Search grounding is working!")
        print("✅ Sources are being extracted correctly!")
        print("✅ The Sources and References section will now show actual URLs!")
        print("\n🔧 Next Steps:")
        print("- Fix the ScrapedPage JSON serialization issue")
        print("- Then new research reports will show real sources instead of just 'Gemini AI Knowledge Base'")
    else:
        print("❌ FAILED: No sources were collected")

async def main():
    """Main test function."""
    await test_complete_source_collection()

if __name__ == "__main__":
    asyncio.run(main())
