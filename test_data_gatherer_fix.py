#!/usr/bin/env python3
"""
Test script to verify that the DataGatherer properly converts ScrapedPage objects to dictionaries.
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from src.core.data_gatherer import DataGatherer
from src.utils.gemini_client import GeminiClient

# Load environment variables
load_dotenv()

async def test_data_gatherer_scraping():
    """Test that DataGatherer properly handles ScrapedPage conversion."""
    
    print("🔍 Testing DataGatherer ScrapedPage handling")
    print("=" * 50)
    
    # Setup configuration
    config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_MODEL": "gemini-2.5-pro",
        "MAX_SEARCH_RESULTS": 3,
        "MAX_SCRAPING_DEPTH": 1,
        "MAX_LINKS_PER_PAGE": 2,
        "REQUEST_TIMEOUT": 30,
        "USER_AGENT": "Mozilla/5.0 (compatible; OdysseyEngine/1.0; Test)"
    }
    
    # Initialize components
    try:
        gemini_client = GeminiClient(config)
        data_gatherer = DataGatherer(gemini_client, config)
        print("✅ DataGatherer initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize DataGatherer: {e}")
        return False
    
    # Test direct web scraping (this calls the code we fixed)
    test_urls = [
        "https://httpbin.org/html",  # Simple HTML test page
        "https://httpbin.org/json",  # JSON response test
    ]
    
    print(f"\n🕷️ Testing web scraping with {len(test_urls)} URLs...")
    
    try:
        scraped_data = await data_gatherer._gather_web_scraping(test_urls)
        
        print("✅ Web scraping completed without errors")
        print(f"  - Scraped pages: {len(scraped_data.get('scraped_pages', []))}")
        print(f"  - Followed links: {len(scraped_data.get('followed_links', []))}")
        print(f"  - Errors: {len(scraped_data.get('errors', []))}")
        
        # Test JSON serialization of the result
        try:
            json_str = json.dumps(scraped_data, indent=2)
            print("✅ JSON serialization of scraped data successful!")
            
            # Check that scraped pages are dictionaries, not ScrapedPage objects
            for i, page in enumerate(scraped_data.get('scraped_pages', [])):
                if isinstance(page, dict):
                    print(f"  ✅ Page {i+1} is a dictionary (URL: {page.get('url', 'N/A')})")
                    print(f"     Success: {page.get('success', 'N/A')}")
                    print(f"     Title: {page.get('title', 'N/A')[:50]}...")
                else:
                    print(f"  ❌ Page {i+1} is not a dictionary: {type(page)}")
                    return False
                    
        except Exception as e:
            print(f"❌ JSON serialization failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Web scraping failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ All DataGatherer tests passed!")
    return True

async def test_minimal_research_flow():
    """Test a minimal research flow to ensure no ScrapedPage serialization issues."""
    
    print("\n🔍 Testing minimal research flow")
    print("-" * 30)
    
    # Setup configuration
    config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_MODEL": "gemini-2.5-pro",
        "MAX_SEARCH_RESULTS": 2,
        "MAX_SCRAPING_DEPTH": 1,
        "MAX_LINKS_PER_PAGE": 1,
        "REQUEST_TIMEOUT": 15,
        "USER_AGENT": "Mozilla/5.0 (compatible; OdysseyEngine/1.0; Test)"
    }
    
    try:
        gemini_client = GeminiClient(config)
        data_gatherer = DataGatherer(gemini_client, config)
        
        # Create a minimal intent result
        intent_result = {
            "research_questions": ["What is HTTP?"],
            "key_entities": ["HTTP", "protocol"],
            "domain": "technology",
            "complexity_level": "intermediate"
        }
        
        print("🔄 Running minimal data gathering...")
        
        # This will call _gather_web_scraping internally
        data_result = await data_gatherer.gather_data(intent_result)
        
        print("✅ Data gathering completed")
        
        # Test JSON serialization of the complete result
        try:
            json_str = json.dumps(data_result, indent=2)
            print("✅ Complete data result is JSON serializable!")
            
            # Check for ScrapedPage objects in web scraping results
            web_data = data_result.get('web_scraping', {})
            if web_data.get('scraped_pages'):
                print(f"  Found {len(web_data['scraped_pages'])} scraped pages")
                for page in web_data['scraped_pages']:
                    if not isinstance(page, dict):
                        print(f"  ❌ Found non-dict page: {type(page)}")
                        return False
                print("  ✅ All scraped pages are dictionaries")
            
        except Exception as e:
            print(f"❌ JSON serialization of complete result failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Minimal research flow failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("✅ Minimal research flow test passed!")
    return True

async def main():
    """Run all tests."""
    
    success = True
    
    # Test 1: Direct DataGatherer scraping
    success &= await test_data_gatherer_scraping()
    
    # Test 2: Minimal research flow
    success &= await test_minimal_research_flow()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ ALL TESTS PASSED! ScrapedPage JSON serialization is fixed.")
    else:
        print("❌ Some tests failed. Check the output above.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
