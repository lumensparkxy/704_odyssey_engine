#!/usr/bin/env python3
"""
Test script to check if GoogleSearch max_remote_calls parameter is configurable.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
import sys
sys.path.insert(0, '/Users/admin/learn_python/704_odyssey_engine/src')

from utils.gemini_client import GeminiClient

async def test_max_remote_calls_config():
    """Test if max_remote_calls can be configured."""
    
    print("🔧 Testing MAX_REMOTE_CALLS Configuration")
    print("=" * 50)
    
    # Test with different values
    test_values = [5, 10, 15]
    
    for max_calls in test_values:
        print(f"\n🧪 Testing with MAX_REMOTE_CALLS = {max_calls}")
        
        config = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "GEMINI_MODEL": "gemini-2.5-pro",
            "MAX_REMOTE_CALLS": max_calls,
            "REQUEST_TIMEOUT": 30
        }
        
        try:
            client = GeminiClient(config)
            print(f"✅ GeminiClient initialized with MAX_REMOTE_CALLS={max_calls}")
            
            # Test a simple grounding query
            result = await client.generate_with_grounding(
                "What is Python programming language?",
                enable_search=True
            )
            
            print(f"  - Grounding enabled: {result.get('grounding_enabled')}")
            print(f"  - Sources found: {len(result.get('sources', []))}")
            print(f"  - Response length: {len(result.get('response', ''))}")
            
            if result.get('fallback_reason'):
                print(f"  - Fallback reason: {result['fallback_reason']}")
            
        except Exception as e:
            print(f"❌ Error with MAX_REMOTE_CALLS={max_calls}: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Test completed. Check the logs for 'AFC is enabled with max remote calls' messages.")
    print("If the number changes, the configuration is working!")

if __name__ == "__main__":
    asyncio.run(test_max_remote_calls_config())
