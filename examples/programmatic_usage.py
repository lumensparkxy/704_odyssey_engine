"""Example usage of the Odyssey Engine programmatically.

This example shows how to use the research engine directly in code
rather than through the CLI interface.
"""

import asyncio
import os
import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """Ensure the repository's `src/` directory is on sys.path."""
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))


_ensure_src_on_path()

from core.engine import ResearchEngine  # noqa: E402
from dotenv import load_dotenv  # noqa: E402


async def main() -> None:
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
        "DEFAULT_REPORT_TONE": "formal_accessible",
    }

    if not config["GEMINI_API_KEY"]:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your API key in .env file or environment")
        return

    engine = ResearchEngine(config)
    query = "What are the latest developments in quantum computing and their potential impact on cybersecurity?"

    print(f"🔍 Starting research: {query}")
    print("-" * 80)

    try:
        session_id = await engine.start_research_session(query)
        print(f"📝 Session ID: {session_id}")

        result = await engine.conduct_research(session_id)

        if result["status"] == "needs_clarification":
            print("\n🤔 The engine needs clarification:")
            questions = result.get("questions", [])

            user_responses = {}
            for question_data in questions:
                question = question_data.get("question", "")
                print(f"   Q: {question}")

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

            print("\n🔄 Continuing research with responses...")
            result = await engine.conduct_research(session_id, user_responses)

        if result["status"] == "completed":
            print("\n✅ Research completed successfully!")

            report = result.get("report", {})
            confidence = result.get("confidence", {})

            print(
                f"\n📊 Overall Confidence: {confidence.get('overall_confidence', 0):.1f}%")
            print(f"📄 Report saved to: {report.get('file_path', 'Unknown')}")
            print(f"📝 Word count: {report.get('word_count', 0):,}")

            breakdown = confidence.get("confidence_breakdown", {})
            if breakdown:
                print("\n🎯 Confidence Breakdown:")
                for stage, conf in breakdown.items():
                    stage_name = stage.replace("_", " ").title()
                    print(f"   {stage_name}: {conf}")

            if report.get("content"):
                content = report["content"]
                lines = content.split("\n")
                preview_lines = lines[:20]

                print("\n📖 Report Preview:")
                print("-" * 60)
                for line in preview_lines:
                    print(line)

                if len(lines) > 20:
                    print(f"\n... ({len(lines) - 20} more lines)")
                    print(
                        f"\nFull report available at: {report.get('file_path')}")
        else:
            print(f"❌ Research failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error during research: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
