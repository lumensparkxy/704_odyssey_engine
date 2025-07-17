#!/usr/bin/env python3
"""
Odyssey Engine - Direct Research Script

This script allows you to conduct research directly by specifying your query
and input variables in the file itself, bypassing the interactive CLI.

Usage:
1. Edit the RESEARCH_QUERY variable below with your research question
2. Edit the CLARIFICATION_RESPONSES if needed (usually can be left empty)
3. Run: python new_research.py
"""

from dotenv import load_dotenv
from utils.storage import SessionStorage
from core.engine import ResearchEngine
import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


# ========================================
# CONFIGURATION - EDIT THESE VALUES
# ========================================

# Your main research query - edit this with your research question
RESEARCH_QUERY = """
You are an expert technical writer and security researcher.  
Your task: draft a complete academic paper (~8,000 words) on **adversarial perturbation images** -- how they are created, why they fool vision and vision-language models, and their broader implications.

* Audience & style
- Written for a computer-vision / ML-security conference (e.g. CVPR, IEEE S&P).
- Use formal academic tone, LaTeX-friendly markdown, and IEEE citation style: [Author, Year].

* Deliverables
1. **Title** (catchy but precise)  
2. **Abstract** (<=250 words)  
3. **Section-level outline**  
4. **Full paper draft**  
   - *Introduction* -> motivation, concise problem statement  
   - *Background & Related Work* -> >=15 seminal papers (Goodfellow 2014, Carlini 2017, Brown 2018 "Patch", Croce 2020 AutoAttack, etc.)  
   - *Threat Model & Assumptions* -> define white-box, black-box, physical-world attacks  
   - *Attack Methodology*  
        - Gradient-based (FGSM, PGD, CW)  
        - Query-based / score-based  
        - Steganographic & text-overlay tactics (brief)  
   - *Case Studies & Reproduction*  
        - Include PyTorch pseudocode snippets  
        - Datasets: ImageNet, MS-COCO, custom human-perception panels  
   - *Implications*  
        - Model reliability & fairness  
        - Security (autonomous vehicles, medical imaging, content moderation, biometrics)  
        - Societal & ethical considerations  
   - *Defences & Mitigations*  
        - Adversarial training, randomized smoothing, feature denoising  
        - Robustness benchmarks (AutoAttack, RobustBench)  
   - *Open Challenges & Future Work*  
   - *Conclusion*  
5. **Figures**  
   - Text description + caption for:  
        - Decision-boundary sketch  
        - Before/after adversarial example (dog->wine)  
        - Defence comparison bar-chart  
6. **Bibliography** - >=30 references, formatted.

* Constraints
- Cite all claims with [Author, Year]; include DOI or arXiv IDs in the bibliography.
- Provide every equation in LaTeX math mode.
- Keep code blocks concise (<=25 lines each).

* Extras (optional, add if helpful)
- Short "Plain-English Summary" for a non-technical audience.
- Checklist of ethical disclosure steps.
"""

# If you know the engine will ask clarifying questions, you can pre-answer them here
# Usually you can leave this empty and run the script to see what questions are asked
CLARIFICATION_RESPONSES = {
    # Example format:
    # "What specific aspect of AI interests you most?": "Focus on practical applications and business impact",
    # "What time period should I focus on?": "2024-2025",
    # "What industries are you most interested in?": "Technology, healthcare, finance"
}

# Optional: Override default configuration
CONFIG_OVERRIDES = {
    # "CONFIDENCE_THRESHOLD": 80,
    # "MAX_SEARCH_RESULTS": 15,
    # "MAX_SCRAPING_DEPTH": 3,
    # "DEFAULT_REPORT_TONE": "formal_accessible",
    # "INCLUDE_CONFIDENCE_SCORES": True,
    # "INCLUDE_SOURCE_RELIABILITY": True,
}

# ========================================
# SCRIPT LOGIC - DON'T EDIT BELOW UNLESS YOU KNOW WHAT YOU'RE DOING
# ========================================


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables with overrides."""
    config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
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
        "INCLUDE_SOURCE_RELIABILITY": os.getenv("INCLUDE_SOURCE_RELIABILITY", "true").lower() == "true"
    }

    # Apply overrides
    config.update(CONFIG_OVERRIDES)

    return config


def validate_config(config: Dict[str, Any]) -> None:
    """Validate configuration before starting research."""
    if not config.get("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY not found!")
        print("Please set your Gemini API key in the .env file or environment variables.")
        print("Example: GEMINI_API_KEY=your_api_key_here")
        sys.exit(1)


def print_config_info(config: Dict[str, Any]) -> None:
    """Print configuration information."""
    print("🔧 Configuration:")
    print(f"   Model: {config.get('GEMINI_MODEL')}")
    print(f"   Confidence Threshold: {config.get('CONFIDENCE_THRESHOLD')}%")
    print(f"   Max Search Results: {config.get('MAX_SEARCH_RESULTS')}")
    print(f"   Max Scraping Depth: {config.get('MAX_SCRAPING_DEPTH')}")
    print(f"   Report Tone: {config.get('DEFAULT_REPORT_TONE')}")
    print(
        f"   Include Confidence Scores: {'Yes' if config.get('INCLUDE_CONFIDENCE_SCORES') else 'No'}")
    print("")


def print_query_info(query: str, responses: Dict[str, str]) -> None:
    """Print research query information."""
    print("📋 Research Query:")
    print(f"   {query.strip()}")
    print("")

    if responses:
        print("💬 Pre-configured Clarification Responses:")
        for question, answer in responses.items():
            print(f"   Q: {question}")
            print(f"   A: {answer}")
        print("")


def format_confidence_breakdown(breakdown: Dict[str, Any]) -> str:
    """Format confidence breakdown for display."""
    if not breakdown:
        return "No breakdown available"

    formatted_lines = []
    for stage, confidence in breakdown.items():
        stage_name = stage.replace("_", " ").title()
        formatted_lines.append(f"   • {stage_name}: {confidence}")

    return "\n".join(formatted_lines)


async def run_research(query: str, clarification_responses: Dict[str, str]) -> None:
    """Run the research process with the specified query and responses."""

    # Load and validate configuration
    config = load_config()
    validate_config(config)

    # Print configuration and query info
    print("=" * 60)
    print("🔍 Odyssey Engine - Direct Research")
    print("=" * 60)
    print_config_info(config)
    print_query_info(query, clarification_responses)

    try:
        # Initialize engine
        print("🚀 Initializing research engine...")
        engine = ResearchEngine(config)

        # Start research session
        print("📝 Starting research session...")
        session_id = await engine.start_research_session(query)
        print(f"   Session ID: {session_id}")
        print("")

        # Conduct research
        print("🔍 Conducting research...")
        print("   This may take several minutes depending on the complexity...")
        print("")

        # First attempt - might need clarification
        result = await engine.conduct_research(session_id)

        # Handle clarification if needed
        if result.get("status") == "needs_clarification":
            print("🤔 Clarification needed...")
            questions = result.get("questions", [])

            # Display questions
            for i, question_data in enumerate(questions, 1):
                question = question_data.get("question", "")
                purpose = question_data.get("purpose", "")
                examples = question_data.get("examples", [])

                print(f"   Question {i}: {question}")
                if purpose:
                    print(f"   Purpose: {purpose}")
                if examples:
                    print(f"   Examples: {', '.join(examples)}")
                print("")

            # Check if we have pre-configured responses
            if clarification_responses:
                print("✅ Using pre-configured responses...")

                # Verify all questions are answered
                unanswered_questions = []
                for question_data in questions:
                    question = question_data.get("question", "")
                    if question not in clarification_responses:
                        unanswered_questions.append(question)

                if unanswered_questions:
                    print("❌ Some questions don't have pre-configured responses:")
                    for q in unanswered_questions:
                        print(f"   • {q}")
                    print(
                        "\nPlease add these questions to CLARIFICATION_RESPONSES in the script.")
                    return

                # Continue with responses
                print("🔄 Continuing research with your responses...")
                result = await engine.conduct_research(session_id, clarification_responses)
            else:
                print("❌ No pre-configured responses found.")
                print(
                    "Please add responses to CLARIFICATION_RESPONSES in the script and run again.")
                print("\nExample format:")
                print("CLARIFICATION_RESPONSES = {")
                for question_data in questions:
                    question = question_data.get("question", "")
                    print(f'    "{question}": "Your answer here",')
                print("}")
                return

        # Process final result
        if result.get("status") == "completed":
            print("✅ Research completed successfully!")
            print("=" * 60)

            # Display results
            report = result.get("report", {})
            confidence = result.get("confidence", {})

            # Show confidence summary
            if confidence:
                overall_conf = confidence.get("overall_confidence", 0)
                conf_level = confidence.get("confidence_level", "Unknown")

                print(f"📊 Research Confidence:")
                print(f"   Overall: {overall_conf:.1f}% ({conf_level})")
                print("")

                breakdown = confidence.get("confidence_breakdown", {})
                if breakdown:
                    print("   Stage Breakdown:")
                    print(format_confidence_breakdown(breakdown))
                    print("")

            # Show report info
            if report:
                word_count = report.get("word_count", 0)
                file_path = report.get("file_path", "")

                print(f"📄 Report Generated:")
                print(f"   File: {file_path}")
                print(f"   Word Count: {word_count:,} words")
                print(
                    f"   Sections: {report.get('metadata', {}).get('sections_count', 0)}")
                print("")

                print("📖 Your comprehensive research report has been saved!")
                print(f"   You can find it at: {file_path}")

        elif result.get("status") == "error":
            print(f"❌ Research failed: {result.get('error', 'Unknown error')}")
            print("   Check the logs/odyssey.log file for more details.")
        else:
            print(
                f"❌ Research failed with status: {result.get('status', 'Unknown')}")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error during research: {str(e)}")
        print("   Check the logs/odyssey.log file for more details.")


async def main():
    """Main entry point for the direct research script."""

    # Validate that query is provided
    if not RESEARCH_QUERY.strip():
        print("❌ Error: RESEARCH_QUERY is empty!")
        print("Please edit the RESEARCH_QUERY variable in this script.")
        return

    # Load environment variables
    load_dotenv()

    # Run the research
    await run_research(RESEARCH_QUERY.strip(), CLARIFICATION_RESPONSES)

if __name__ == "__main__":
    asyncio.run(main())
