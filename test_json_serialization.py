#!/usr/bin/env python3
"""
Test script to verify ScrapedPage JSON serialization is working.
"""

import asyncio
import json
from src.utils.web_scraper import ScrapedPage

def test_scraped_page_serialization():
    """Test that ScrapedPage objects can be converted to JSON."""
    
    # Create a sample ScrapedPage object
    page = ScrapedPage(
        url="https://example.com",
        title="Example Page",
        content="This is example content for testing.",
        links=["https://example.com/link1", "https://example.com/link2"],
        metadata={"author": "Test Author", "date": "2025-07-06"},
        scrape_time=1234567890.123,
        success=True,
        error=None
    )
    
    print("Original ScrapedPage object:")
    print(f"  URL: {page.url}")
    print(f"  Title: {page.title}")
    print(f"  Success: {page.success}")
    print()
    
    # Convert to dictionary
    page_dict = page.to_dict()
    print("Converted to dictionary:")
    print(f"  Type: {type(page_dict)}")
    print(f"  Keys: {list(page_dict.keys())}")
    print()
    
    # Test JSON serialization
    try:
        json_str = json.dumps(page_dict, indent=2)
        print("✅ JSON serialization successful!")
        print("JSON output:")
        print(json_str)
        
        # Test deserialization
        parsed_back = json.loads(json_str)
        print("\n✅ JSON deserialization successful!")
        print(f"  Parsed URL: {parsed_back['url']}")
        print(f"  Parsed Title: {parsed_back['title']}")
        
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False
    
    return True

def test_scraped_page_list_serialization():
    """Test that a list of ScrapedPage objects can be serialized."""
    
    pages = [
        ScrapedPage(
            url=f"https://example{i}.com",
            title=f"Example Page {i}",
            content=f"Content for page {i}",
            links=[f"https://example{i}.com/link1"],
            metadata={"id": i},
            scrape_time=1234567890.123 + i,
            success=True,
            error=None
        ) for i in range(3)
    ]
    
    print("\nTesting list of ScrapedPage objects:")
    
    # Convert all to dictionaries
    page_dicts = [page.to_dict() for page in pages]
    
    # Test JSON serialization of the list
    try:
        json_str = json.dumps(page_dicts, indent=2)
        print("✅ List JSON serialization successful!")
        print(f"Serialized {len(page_dicts)} pages")
        
        # Test deserialization
        parsed_back = json.loads(json_str)
        print(f"✅ Parsed back {len(parsed_back)} pages")
        
    except Exception as e:
        print(f"❌ List JSON serialization failed: {e}")
        return False
    
    return True

def test_complex_data_structure():
    """Test serialization in a more complex data structure like DataGatherer uses."""
    
    page = ScrapedPage(
        url="https://example.com",
        title="Example Page",
        content="Example content",
        links=["https://example.com/link1"],
        metadata={"type": "article"},
        scrape_time=1234567890.123,
        success=True,
        error=None
    )
    
    # Simulate the structure used in DataGatherer
    scraped_data = {
        "scraped_pages": [page.to_dict()],  # This is how we're fixing it
        "followed_links": [],
        "depth_map": {"https://example.com": 1},
        "errors": []
    }
    
    print("\nTesting complex data structure:")
    
    try:
        json_str = json.dumps(scraped_data, indent=2)
        print("✅ Complex structure JSON serialization successful!")
        print("Structure contains:")
        print(f"  - {len(scraped_data['scraped_pages'])} scraped pages")
        print(f"  - {len(scraped_data['followed_links'])} followed links")
        print(f"  - {len(scraped_data['depth_map'])} depth mappings")
        
    except Exception as e:
        print(f"❌ Complex structure JSON serialization failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 Testing ScrapedPage JSON Serialization")
    print("=" * 50)
    
    success = True
    
    success &= test_scraped_page_serialization()
    success &= test_scraped_page_list_serialization()
    success &= test_complex_data_structure()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! JSON serialization is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above.")
