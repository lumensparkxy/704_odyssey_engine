"""
Example usage of the Odyssey Engine programmatically.

This example shows how to use the research engine directly in code
rather than through the CLI interface.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.engine import ResearchEngine
from dotenv import load_dotenv


async def main():
    """Example of programmatic usage."""
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_MODEL": "gemini-2.5-pro",
        "CONFIDENCE_THRESHOLD": 75,
        "MAX_SCRAPING_DEPTH": 3,
        "SESSION_STORAGE_PATH": "./sessions",
        "REPORTS_OUTPUT_PATH": "./reports",
        "DEFAULT_REPORT_TONE": "formal_accessible"
    }
    
    # Check API key
    if not config["GEMINI_API_KEY"]:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your API key in .env file or environment")
        return
    
    # Initialize research engine
    engine = ResearchEngine(config)
    
    # Example research query
    query = "What are the latest developments in quantum computing and their potential impact on cybersecurity?"
    
    print(f"🔍 Starting research: {query}")
    print("-" * 80)
    
    try:
        # Start research session
        session_id = await engine.start_research_session(query)
        print(f"📝 Session ID: {session_id}")
        
        # Conduct research
        result = await engine.conduct_research(session_id)
        
        if result["status"] == "needs_clarification":
            print("\n🤔 The engine needs clarification:")
            questions = result.get("questions", [])
            
            # For this example, provide automatic responses
            user_responses = {}
            for question_data in questions:
                question = question_data.get("question", "")
                print(f"   Q: {question}")
                
                # Provide sample responses (in real usage, you'd get user input)
                if "time" in question.lower():
                    response = "2023-2024"
                elif "specific" in question.lower():
                    response = "Focus on practical applications"
                elif "scope" in question.lower():
                    response = "Global perspective"
                else:
                    response = "Please provide comprehensive coverage"
                
                user_responses[question] = response
                print(f"   A: {response}")
            
            # Continue research with responses
            print("\n🔄 Continuing research with responses...")
            result = await engine.conduct_research(session_id, user_responses)
        
        if result["status"] == "completed":
            print("\n✅ Research completed successfully!")
            
            # Show results
            report = result.get("report", {})
            confidence = result.get("confidence", {})
            
            print(f"\n📊 Overall Confidence: {confidence.get('overall_confidence', 0):.1f}%")
            print(f"📄 Report saved to: {report.get('file_path', 'Unknown')}")
            print(f"📝 Word count: {report.get('word_count', 0):,}")
            
            # Show confidence breakdown
            breakdown = confidence.get("confidence_breakdown", {})
            if breakdown:
                print("\n🎯 Confidence Breakdown:")
                for stage, conf in breakdown.items():
                    stage_name = stage.replace("_", " ").title()
                    print(f"   {stage_name}: {conf}")
            
            # Show a sample of the report content
            if report.get("content"):
                content = report["content"]
                lines = content.split('\n')
                preview_lines = lines[:20]  # First 20 lines
                
                print("\n📖 Report Preview:")
                print("-" * 60)
                for line in preview_lines:
                    print(line)
                
                if len(lines) > 20:
                    print(f"\n... ({len(lines) - 20} more lines)")
                    print(f"\nFull report available at: {report.get('file_path')}")
        
        else:
            print(f"❌ Research failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Error during research: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
