#!/usr/bin/env python3
"""\
Odyssey Engine - Simple Research Script

This is a simplified version that allows you to run research with minimal setup.
Just edit the variables below and run the script.

Usage:
1. Edit the RESEARCH_QUERY variable below
2. Run: python scripts/simple_research.py
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _ensure_src_on_path() -> None:
    """Ensure the repository's `src/` directory is on sys.path.

    This script lives in `scripts/`, so the repo root is one directory up.
    """

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))


_ensure_src_on_path()

from core.engine import ResearchEngine  # noqa: E402


# ========================================
# EDIT THESE VARIABLES
# ========================================

# Your research question
RESEARCH_QUERY = """
What are the key factors that influence employee productivity in remote work environments?
"""

# If you get clarification questions, add them here after the first run
CLARIFICATION_RESPONSES = {
    # Example:
    # "What specific industry or type of work are you focusing on?": "Technology and knowledge work",
    # "What time period should I focus on?": "Post-COVID era (2020-2025)",
}


def load_config() -> dict:
    """Load basic configuration."""
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found!")
        print("Please set your Gemini API key in the .env file")
        print("Example: GEMINI_API_KEY=your_api_key_here")
        sys.exit(1)

    return {
        "GEMINI_API_KEY": api_key,
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
        "CONFIDENCE_THRESHOLD": int(os.getenv("CONFIDENCE_THRESHOLD", "75")),
        "MAX_SCRAPING_DEPTH": int(os.getenv("MAX_SCRAPING_DEPTH", "3")),
        "MAX_SEARCH_RESULTS": int(os.getenv("MAX_SEARCH_RESULTS", "10")),
        "MAX_FOLLOW_UP_QUESTIONS": int(os.getenv("MAX_FOLLOW_UP_QUESTIONS", "5")),
        "MAX_REMOTE_CALLS": int(os.getenv("MAX_REMOTE_CALLS", "10")),
        "SESSION_STORAGE_PATH": os.getenv("SESSION_STORAGE_PATH", "./sessions"),
        "REPORTS_OUTPUT_PATH": os.getenv("REPORTS_OUTPUT_PATH", "./reports"),
        "USER_AGENT": os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; OdysseyEngine/1.0)"),
        "REQUEST_TIMEOUT": int(os.getenv("REQUEST_TIMEOUT", "30")),
        "MAX_CONCURRENT_REQUESTS": int(os.getenv("MAX_CONCURRENT_REQUESTS", "5")),
        "DEFAULT_REPORT_TONE": os.getenv("DEFAULT_REPORT_TONE", "formal_accessible"),
        "INCLUDE_CONFIDENCE_SCORES": os.getenv("INCLUDE_CONFIDENCE_SCORES", "true").lower() == "true",
        "INCLUDE_SOURCE_RELIABILITY": os.getenv("INCLUDE_SOURCE_RELIABILITY", "true").lower() == "true",
    }


async def main() -> None:
    """Run the research."""
    if not RESEARCH_QUERY.strip():
        print("❌ Please edit RESEARCH_QUERY in this script!")
        return

    print("🔍 Starting Odyssey Engine Research...")
    print(f"📋 Query: {RESEARCH_QUERY.strip()}")
    print("")

    try:
        # Initialize
        config = load_config()
        engine = ResearchEngine(config)

        # Start research
        session_id = await engine.start_research_session(RESEARCH_QUERY.strip())
        print(f"📝 Session ID: {session_id}")

        # Conduct research
        print("🔍 Conducting research (this may take a few minutes)...")
        result = await engine.conduct_research(session_id)

        # Handle clarification
        if result.get("status") == "needs_clarification":
            print("🤔 Clarification needed:")
            questions = result.get("questions", [])

            for i, q_data in enumerate(questions, 1):
                print(f"   {i}. {q_data.get('question', '')}")

            if CLARIFICATION_RESPONSES:
                print("✅ Using pre-configured responses...")
                result = await engine.conduct_research(session_id, CLARIFICATION_RESPONSES)
            else:
                print(
                    "\n❌ Please add responses to CLARIFICATION_RESPONSES and run again.")
                return

        # Show results
        if result.get("status") == "completed":
            print("✅ Research completed!")

            report = result.get("report", {})
            confidence = result.get("confidence", {})

            if confidence:
                overall_conf = confidence.get("overall_confidence", 0)
                print(f"📊 Confidence: {overall_conf:.1f}%")

            if report:
                print(f"📄 Report saved: {report.get('file_path', '')}")
                print(f"📝 Word count: {report.get('word_count', 0):,}")
        else:
            print(f"❌ Research failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
