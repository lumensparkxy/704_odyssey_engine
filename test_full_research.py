#!/usr/bin/env python3
"""
Simple test script to run a complete research session and verify JSON parsing improvements.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.engine import ResearchEngine
import configparser


async def test_research_session():
    """Test a complete research session to verify the JSON parsing improvements."""
    
    # Load configuration
    config = configparser.ConfigParser()
    config.read('config/default.conf')
    
    # Convert ConfigParser to dict
    config_dict = {}
    for section in config.sections():
        config_dict.update(dict(config.items(section)))
    
    try:
        # Initialize the research engine
        engine = ResearchEngine(config_dict)
        
        # Start a research session
        print("🚀 Starting test research session...")
        session_id = await engine.start_research_session("What are the benefits of meditation?")
        print(f"✅ Session created: {session_id}")
        
        # Conduct research
        print("🔍 Conducting research...")
        result = await engine.conduct_research(session_id)
        
        if result["status"] == "completed":
            print("✅ Research completed successfully!")
            print(f"📄 Report generated: {result['report']['file_path']}")
            print(f"📊 Overall confidence: {result['confidence']['overall_confidence']:.1f}%")
            
            # Check if we had any JSON parsing issues
            session_data = result["session_data"]
            stages = session_data.get("stages", {})
            
            analysis_stage = stages.get("analysis", {})
            if analysis_stage.get("status") == "completed":
                themes = analysis_stage.get("result", {}).get("themes", [])
                conflicts = analysis_stage.get("result", {}).get("conflicts", [])
                
                print(f"🎯 Themes identified: {len(themes)}")
                print(f"⚡ Conflicts identified: {len(conflicts)}")
                
                # Check if fallback themes were used (indicates JSON parsing failed)
                if len(themes) == 2 and themes[0].get("title") == "General Information":
                    print("⚠️  Fallback themes were used (JSON parsing may have failed)")
                else:
                    print("✅ Custom themes were successfully generated")
                    
        elif result["status"] == "needs_clarification":
            print("❓ Research needs clarification")
            print("Questions:", result.get("questions", []))
        else:
            print(f"❌ Research failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_research_session())
    if success:
        print("\n🎉 JSON parsing improvements test completed!")
    else:
        print("\n💥 Test failed!")
        sys.exit(1)
