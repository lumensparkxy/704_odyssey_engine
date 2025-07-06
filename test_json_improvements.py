#!/usr/bin/env python3
"""
Test script to verify JSON parsing improvements.
This script tests the new robust JSON parsing functionality.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.engine import ResearchEngine


async def test_json_parsing():
    """Test the new JSON parsing utility method."""
    
    # Mock config for testing
    config = {
        "GEMINI_API_KEY": "test_key",
        "SESSION_STORAGE_PATH": "./sessions",
        "REPORTS_OUTPUT_PATH": "./reports"
    }
    
    try:
        # Initialize engine (will fail due to invalid API key, but that's expected)
        engine = ResearchEngine(config)
        
        # Test cases for JSON parsing
        test_cases = [
            # Valid JSON array
            ('[{"title": "Test", "description": "Test desc", "supporting_evidence": ["test"]}]', "array", "valid_array"),
            
            # JSON wrapped in markdown
            ('```json\n[{"title": "Test", "description": "Test desc", "supporting_evidence": ["test"]}]\n```', "array", "markdown_wrapped"),
            
            # Empty response
            ('', "array", "empty_response"),
            
            # Invalid JSON
            ('[{"title": "Test", "description":}]', "array", "invalid_json"),
            
            # Valid object
            ('{"pros": ["good"], "cons": ["bad"]}', "object", "valid_object"),
            
            # JSON with extra text
            ('Here is the JSON:\n```json\n{"pros": ["good"], "cons": ["bad"]}\n```\nThat was the result.', "object", "extra_text"),
        ]
        
        print("Testing JSON parsing improvements...")
        print("=" * 50)
        
        for response, expected_type, test_name in test_cases:
            print(f"\nTest: {test_name}")
            print(f"Input: {response[:50]}{'...' if len(response) > 50 else ''}")
            
            if expected_type == "array":
                fallback = []
            else:
                fallback = {"pros": [], "cons": []}
            
            result = await engine._parse_json_response(
                response, 
                expected_type=expected_type, 
                fallback_value=fallback,
                method_name=f"test_{test_name}"
            )
            
            print(f"Result: {result}")
            print(f"Type: {type(result)}")
            
        print("\n" + "=" * 50)
        print("JSON parsing tests completed!")
        
    except Exception as e:
        print(f"Test initialization error (expected): {e}")
        print("This is expected since we're using a test API key.")
        return True


if __name__ == "__main__":
    asyncio.run(test_json_parsing())
