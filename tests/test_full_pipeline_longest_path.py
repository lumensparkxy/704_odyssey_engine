
from utils.web_scraper import ScrapedPage
from core.engine import ResearchEngine
import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestFullPipelineLongestPath:
    """
    Test case covering the longest path through the Odyssey Engine pipeline.

    Path:
    1. Ambiguous Query -> Intent Analysis -> Needs Clarification
    2. User Response -> Intent Analysis -> Clarified (with all context flags)
    3. Data Gathering -> Internal + Search + Scraping
    4. Analysis -> Themes + Conflicts + All Summaries (Comparison, Timeline, Pros/Cons)
    5. Report Generation
    """

    def setup_method(self):
        self.config = {
            "GEMINI_API_KEY": "test_key",
            "GEMINI_MODEL": "gemini-2.5-pro",
            "CONFIDENCE_THRESHOLD": 75,
            "MAX_SCRAPING_DEPTH": 2,
            "SESSION_STORAGE_PATH": "./test_sessions",
            "REPORTS_OUTPUT_PATH": "./test_reports",
            "MAX_SEARCH_QUERIES": 1,
            "MAX_SEARCH_RESULTS": 1
        }

        # Ensure directories exist
        Path("./test_sessions").mkdir(exist_ok=True)
        Path("./test_reports").mkdir(exist_ok=True)

    def teardown_method(self):
        import shutil
        if Path("./test_sessions").exists():
            shutil.rmtree("./test_sessions")
        if Path("./test_reports").exists():
            shutil.rmtree("./test_reports")

    @patch("core.engine.GeminiClient")
    @patch("core.data_gatherer.WebScraper")
    @pytest.mark.asyncio
    async def test_longest_path_execution(self, MockWebScraper, MockGeminiClient):
        # --- Setup Mocks ---

        # 1. Mock Gemini Client
        mock_gemini = MockGeminiClient.return_value

        # Define the side effect for generate_response to handle different stages
        async def generate_response_side_effect(prompt, **kwargs):
            prompt_lower = prompt.lower()

            # Intent Analysis - Clarifying Questions Generation
            if "generate clarifying questions" in prompt_lower:
                return json.dumps([
                    {
                        "question": "What specific aspect of AI are you interested in?",
                        "purpose": "To narrow scope",
                        "allow_unknown": True
                    },
                    {
                        "question": "What time frame should I focus on?",
                        "purpose": "To set temporal bounds",
                        "allow_unknown": True
                    }
                ])

            # Intent Analysis (Fallback if not caught by grounding)
            if "analyze the following user query" in prompt_lower:
                # ... (This might not be reached if grounding handles it, but keep it)
                pass

            # Data Gathering - Internal Knowledge
            if "based on your training data" in prompt_lower:
                return "Internal knowledge about AI."

            # Data Gathering - Search Queries
            if "generate effective google search queries" in prompt_lower:
                return json.dumps(["AI healthcare future", "AI finance future"])

            # Data Gathering - Consolidate
            if "consolidate the following information" in prompt_lower:
                return "Consolidated info about AI."

            # Data Gathering - Coverage
            if "assess how well this consolidated information" in prompt_lower:
                return json.dumps({"coverage_score": 90, "gaps": []})

            # Analysis - Themes
            if "identify the key themes" in prompt_lower:
                return json.dumps([
                    {
                        "title": "Automation",
                        "description": "AI automating tasks",
                        "supporting_evidence": ["Source A", "Source B"]
                    }
                ])

            # Analysis - Conflicts
            if "identify any conflicting information" in prompt_lower:
                return json.dumps([
                    {
                        "conflict_type": "Timeline",
                        "description": "Disagreement on AGI date",
                        "sources_involved": ["Source A", "Source B"],
                        "severity": "Medium"
                    }
                ])

            # Analysis - Summaries
            if "create a concise executive summary" in prompt_lower:
                return "Executive Summary: AI is growing."

            if "create a detailed comparison analysis" in prompt_lower:
                return json.dumps({
                    "comparison_table": [{"metric": "Growth", "Healthcare": "High", "Finance": "Medium"}],
                    "key_differences": ["Regulation", "Adoption rate"]
                })

            if "extract and organize chronological events" in prompt_lower:
                return json.dumps([
                    {"date": "2025", "description": "AI Act passed"}
                ])

            if "extract pros and cons" in prompt_lower:
                return json.dumps({
                    "pros": ["Efficiency", "Accuracy"],
                    "cons": ["Job loss", "Bias"]
                })

            # Report Generation (if it calls Gemini)
            if "generate" in prompt_lower and "report" in prompt_lower:
                return "# Final Report\n\nContent..."

            # Default fallback
            return "{}"

        mock_gemini.generate_response.side_effect = generate_response_side_effect

        # Define side effect for generate_with_grounding
        async def generate_with_grounding_side_effect(prompt, **kwargs):
            prompt_lower = prompt.lower()

            # Intent Analysis - First Pass (Ambiguous)
            if "analyze the following research query" in prompt_lower and "user clarifications" not in prompt_lower:
                return {
                    "response": json.dumps({
                        "research_type": "general_research",
                        "domain": "technology",
                        "scope": "broad",
                        "key_entities": ["AI"],
                        "research_questions": ["Future of AI?"],
                        "context_requirements": ["scope"],
                        "output_preferences": ["report"],
                        "confidence": 50,
                        "missing_information": ["specific aspect", "time frame"]
                    }),
                    "sources": []
                }

            # Intent Analysis - Second Pass (Clarified)
            if "analyze the following research query" in prompt_lower and "user clarifications" in prompt_lower:
                return {
                    "response": json.dumps({
                        "research_type": "comparison",
                        "domain": "technology",
                        "scope": "specific",
                        "key_entities": ["AI", "Healthcare", "Finance"],
                        "research_questions": ["AI in healthcare vs finance"],
                        "context_requirements": [],
                        "output_preferences": ["comparison", "timeline", "pros_cons"],
                        "confidence": 95,
                        "missing_information": []
                    }),
                    "sources": []
                }

            # Google Search
            return {
                "response": "Search result about AI.",
                "sources": ["http://example.com/ai"]
            }

        mock_gemini.generate_with_grounding.side_effect = generate_with_grounding_side_effect

        # Mock analyze_content for Web Scraper reliability
        mock_gemini.analyze_content = AsyncMock(
            return_value={"result": '"quality_score": 85'})

        # 2. Mock Web Scraper
        mock_scraper = MockWebScraper.return_value
        mock_page = MagicMock(spec=ScrapedPage)
        mock_page.to_dict.return_value = {
            "url": "http://example.com/ai",
            "title": "AI Future",
            "content": "Long content about AI...",
            "links": []
        }
        mock_page.links = []
        mock_scraper.scrape_page.return_value = mock_page

        # --- Execution ---

        engine = ResearchEngine(self.config)

        # Step 0: Start Session
        print("\n--- Step 0: Start Session ---")
        session_id = await engine.start_research_session("Future of AI")

        # Step 1: Initial Query (Ambiguous)
        print("\n--- Step 1: Initial Query ---")
        result1 = await engine.conduct_research(session_id, user_responses=None)

        # Assertions for Step 1
        assert result1["status"] == "needs_clarification"
        assert "questions" in result1
        assert len(result1["questions"]) > 0

        # Step 2: Provide Clarification (Longest Path)
        print("\n--- Step 2: Clarification ---")
        # Extract question text from the question objects
        q1 = result1["questions"][0]["question"]
        q2 = result1["questions"][1]["question"]

        user_responses = {
            q1: "I want to compare AI in healthcare vs finance.",
            q2: "Next 10 years."
        }

        result2 = await engine.conduct_research(session_id, user_responses=user_responses)

        # Assertions for Step 2 (Final Result)
        assert result2["status"] == "completed"
        assert "report" in result2
        assert "session_data" in result2

        session_data = result2["session_data"]
        stages = session_data["stages"]

        # Verify all stages completed
        assert stages["intent_analysis"]["status"] == "completed"
        assert stages["data_gathering"]["status"] == "completed"
        assert stages["analysis"]["status"] == "completed"
        assert stages["report_generation"]["status"] == "completed"

        # Verify Analysis Depth (Longest Path features)
        analysis_result = stages["analysis"]["result"]
        assert "themes" in analysis_result
        assert "conflicts" in analysis_result
        assert len(analysis_result["conflicts"]) > 0  # We mocked conflicts

        summaries = analysis_result["summaries"]
        assert "executive" in summaries
        assert "comparison" in summaries  # Triggered by context
        assert "timeline" in summaries    # Triggered by context
        assert "pros_cons" in summaries   # Triggered by context

        # Verify Data Gathering Sources
        data_result = stages["data_gathering"]["result"]
        sources = data_result["sources"]
        assert "internal_knowledge" in sources
        assert "google_search" in sources
        assert "web_scraping" in sources

        print("\nTest completed successfully! Longest path verified.")


if __name__ == "__main__":
    pytest.main([__file__])
