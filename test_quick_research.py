#!/usr/bin/env python3
"""
Quick test to verify a research session completes without JSON serialization errors.
"""

import asyncio
import os
from dotenv import load_dotenv

# Add src to path
import sys
sys.path.insert(0, '/Users/admin/learn_python/704_odyssey_engine/src')

from core.engine import ResearchEngine

# Load environment variables
load_dotenv()

async def test_quick_research():
    """Test a quick research session to ensure no JSON errors."""
    
    print("🔍 Testing Quick Research Session")
    print("=" * 40)
    
    try:
        # Setup configuration
        config = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "GEMINI_MODEL": "gemini-2.5-pro",
            "MAX_SEARCH_RESULTS": 2,
            "MAX_SCRAPING_DEPTH": 1,
            "MAX_LINKS_PER_PAGE": 1,
            "REQUEST_TIMEOUT": 30,
            "USER_AGENT": "Mozilla/5.0 (compatible; OdysseyEngine/1.0)",
            "SESSION_STORAGE_PATH": "./sessions",
            "REPORTS_OUTPUT_PATH": "./reports"
        }
        
        # Initialize the research engine
        engine = ResearchEngine(config)
        print("✅ Research engine initialized")
        
        # Create a simple research session
        session_id = await engine.start_research_session("What is HTTP protocol?")
        print(f"✅ Session created: {session_id[:8]}...")
        
        # Conduct research
        print("🔄 Starting research...")
        result = await engine.conduct_research(session_id)
        
        if result.get("status") == "completed":
            print("✅ Research completed successfully!")
            print(f"  - Status: {result.get('status')}")
            print(f"  - Report generated: {bool(result.get('report_path'))}")
        elif result.get("status") == "needs_clarification":
            print("⚠️ Research needs clarification (expected for some queries)")
            print(f"  - Status: {result.get('status')}")
            print(f"  - Questions: {len(result.get('clarifying_questions', []))}")
        else:
            print(f"⚠️ Research completed with status: {result.get('status')}")
        
        print("✅ No JSON serialization errors occurred!")
        
    except TypeError as e:
        if "JSON serializable" in str(e):
            print(f"❌ JSON serialization error still exists: {e}")
            return False
        else:
            print(f"❌ Other TypeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Research failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_quick_research())
    
    print("\n" + "=" * 40)
    if success:
        print("✅ SUCCESS: JSON serialization issue is resolved!")
    else:
        print("❌ FAILED: JSON serialization issue persists.")
