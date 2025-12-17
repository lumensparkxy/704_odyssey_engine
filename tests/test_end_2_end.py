"""End-to-end (mocked) longest-path test for Odyssey Engine.

This test intentionally drives the pipeline through the *longest path* and exercises
multiple internal loops within each stage:

1) Intent stage loop: initial run requires clarification, then a second run proceeds.
2) Data gathering loops:
   - internal knowledge iterates over multiple research questions
   - search iterates over multiple generated search queries (including a timeout)
   - web scraping iterates over multiple URLs and follows links to depth
3) Analysis loops:
   - themes identification retries after an invalid JSON response
   - conflicts identification retries after an invalid JSON response
4) Report generation loops:
   - generates per-question sections for multiple research questions
   - generates per-theme sections for multiple themes

All external network/LLM calls are mocked; this is deterministic and cheap to run.
"""

from __future__ import annotations
from utils.web_scraper import ScrapedPage
from core.engine import ResearchEngine

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _mk_config(tmp_path: Path) -> Dict[str, Any]:
    return {
        "GEMINI_API_KEY": "test_key",
        "GEMINI_MODEL": "gemini-2.5-pro",
        "CONFIDENCE_THRESHOLD": 75,
        "MAX_SCRAPING_DEPTH": 2,
        "MAX_SEARCH_RESULTS": 2,
        "MAX_SEARCH_QUERIES": 3,
        "MAX_LINKS_PER_PAGE": 2,
        "REQUEST_TIMEOUT": 5,
        "SESSION_STORAGE_PATH": str(tmp_path / "sessions"),
        "REPORTS_OUTPUT_PATH": str(tmp_path / "reports"),
    }


def _mk_scraped_page(url: str, *, links: list[str]) -> ScrapedPage:
    # Use a real ScrapedPage instance so `.links` is a real list (not a MagicMock),
    # ensuring follow-link loops execute deterministically.
    return ScrapedPage(
        url=url,
        title=f"Title for {url}",
        content=("This is sufficiently long content. " * 20),
        links=links,
        metadata={},
        scrape_time=0.01,
        success=True,
        error=None,
    )


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
@patch("core.data_gatherer.WebScraper")
async def test_end_2_end_longest_path_multiple_loops(MockWebScraper, MockGeminiClient, tmp_path: Path):
    config = _mk_config(tmp_path)

    # --- Mock Gemini Client ---
    mock_gemini = MockGeminiClient.return_value

    # Keep some local counters to shape multi-attempt behaviors
    counters = {
        "themes_attempts": 0,
        "conflicts_attempts": 0,
        "search_calls": 0,
    }

    async def generate_with_grounding_side_effect(prompt: str, **kwargs):
        prompt_lower = prompt.lower()

        # Stage 1: intent analysis (first pass ambiguous -> needs clarification)
        if "analyze the following research query" in prompt_lower and "user clarifications" not in prompt_lower:
            return {
                "response": json.dumps(
                    {
                        "research_type": "general_research",
                        "domain": "technology",
                        "scope": "broad",
                        "key_entities": ["RAG", "fine-tuning"],
                        "research_questions": [
                            "What is retrieval-augmented generation (RAG)?",
                            "How does fine-tuning compare to RAG?",
                        ],
                        "context_requirements": ["timeframe"],
                        "output_preferences": ["comparison", "timeline", "pros_cons"],
                        "confidence": 40,
                        "missing_information": [
                            "target audience",
                            "desired timeframe",
                            "comparison criteria",
                        ],
                    }
                ),
                "sources": [],
            }

        # Stage 1: intent analysis (second pass clarified)
        if "analyze the following research query with user-provided clarifications" in prompt_lower:
            return {
                "response": json.dumps(
                    {
                        "research_type": "comparison",
                        "domain": "technology",
                        "scope": "detailed",
                        "key_entities": ["RAG", "fine-tuning"],
                        "research_questions": [
                            "RAG vs fine-tuning: trade-offs and best practices",
                            "When should you choose one over the other?",
                        ],
                        "context_requirements": [],
                        "output_preferences": ["comparison", "timeline", "pros_cons"],
                        "confidence": 95,
                        "missing_information": [],
                    }
                ),
                "sources": [],
            }

        # Stage 2: google search grounding (multiple query loop, include one timeout)
        if kwargs.get("enable_search") is True or "research and provide detailed information about" in prompt_lower:
            counters["search_calls"] += 1
            if counters["search_calls"] == 1:
                raise asyncio.TimeoutError()
            # Return grounded sources (urls) for later scraping
            return {
                "response": f"Grounded search response {counters['search_calls']}",
                "sources": [
                    "http://example.com/rag",
                    "http://example.com/finetune",
                    "http://example.com/rag",  # dup to test de-dupe
                ],
            }

        # Default (should not normally hit)
        return {"response": "{}", "sources": []}

    mock_gemini.generate_with_grounding.side_effect = generate_with_grounding_side_effect

    async def generate_response_side_effect(prompt: str, **kwargs):
        p = prompt.lower()

        # Stage 1: clarifying questions
        if "generate clarifying questions" in p:
            return json.dumps(
                [
                    {
                        "question": "Who is the target audience? (e.g., ML engineers, PMs)",
                        "purpose": "Tune depth and jargon",
                        "examples": ["ML engineers", "General technical"],
                        "allow_unknown": True,
                    },
                    {
                        "question": "What timeframe matters most? (e.g., 2022-2025, current)",
                        "purpose": "Focus on recent practices",
                        "examples": ["Current", "Last 2 years"],
                        "allow_unknown": True,
                    },
                    {
                        "question": "What comparison criteria should we emphasize? (cost, latency, quality)",
                        "purpose": "Prioritize trade-offs",
                        "examples": ["Cost", "Latency", "Quality"],
                        "allow_unknown": True,
                    },
                ]
            )

        # Stage 2: internal knowledge loop (multiple research questions)
        if "based on your training data" in p:
            return "Internal knowledge response. According to studies, ..."

        # Stage 2: search query generation loop
        if "generate effective google search queries" in p:
            return json.dumps(
                [
                    "RAG vs fine-tuning trade-offs",
                    "retrieval augmented generation best practices 2024",
                    "fine-tuning LLM latency cost quality",
                ]
            )

        # Stage 2: conflicts between sources (data-gatherer-level conflicts)
        if "identify any conflicts or contradictions" in p and "multiple sources" in p:
            return json.dumps(
                [
                    {
                        "conflict_type": "Cost estimates",
                        "sources_involved": ["internal_knowledge", "google_search"],
                        "description": "Different cost benchmarks across sources.",
                        "severity": "Low",
                    }
                ]
            )

        # Stage 2: consolidation
        if "consolidate the following information" in p:
            return "Consolidated info about RAG and fine-tuning."

        # Stage 2: coverage assessment loop (per-question)
        if "assess how well this consolidated information answers" in p:
            return json.dumps({"coverage_score": 90, "gaps": []})

        # Stage 3: themes identification retry loop
        if "identify the key themes" in p:
            counters["themes_attempts"] += 1
            if counters["themes_attempts"] == 1:
                return "not valid json"
            return json.dumps(
                [
                    {
                        "title": "Latency vs Quality",
                        "description": "Trade-offs between response time and output quality.",
                        "supporting_evidence": ["Source A", "Source B"],
                    },
                    {
                        "title": "Operational Complexity",
                        "description": "RAG adds infra complexity; fine-tuning adds training pipeline complexity.",
                        "supporting_evidence": ["Source C"],
                    },
                ]
            )

        # Stage 3: conflicts identification retry loop
        if "identify any conflicting information" in p:
            counters["conflicts_attempts"] += 1
            if counters["conflicts_attempts"] == 1:
                return "{}"  # invalid (expects array)
            return json.dumps(
                [
                    {
                        "conflict_type": "Performance claims",
                        "description": "Some sources claim fine-tuning always beats RAG; others disagree.",
                        "sources_involved": ["Source A", "Source D"],
                        "severity": "Medium",
                    }
                ]
            )

        # Stage 3: summaries
        if "create a concise executive summary" in p:
            return "Executive Summary: RAG vs fine-tuning depends on constraints."

        if "create a detailed comparison analysis" in p:
            return json.dumps(
                {
                    "comparison_table": [
                        {"metric": "Latency", "RAG": "Medium", "Fine-tuning": "Low"},
                        {"metric": "Freshness", "RAG": "High", "Fine-tuning": "Low"},
                    ],
                    "key_differences": ["Freshness", "Infra complexity"],
                }
            )

        if "extract and organize chronological events" in p:
            return json.dumps(
                [
                    {"date": "2020", "description": "RAG popularized in production systems"},
                    {"date": "2023", "description": "Fine-tuning workflows mature"},
                ]
            )

        if "extract pros and cons" in p:
            return json.dumps(
                {
                    "pros": ["Freshness", "Source grounding"],
                    "cons": ["Complex infra", "Latency overhead"],
                }
            )

        # Stage 4: report generation loops
        if "generate an executive summary" in p:
            return "(Report) Executive summary text."

        if "generate a key findings section" in p:
            return "- Finding 1\n- Finding 2\n- Finding 3"

        if "generate a detailed section answering this research question" in p:
            return "Detailed answer with citations."

        if "generate a detailed section about this theme" in p:
            return "Theme deep dive."

        if "generate a section on contradictory viewpoints" in p:
            return "Conflicting viewpoints section."

        # Default
        return "{}"

    mock_gemini.generate_response.side_effect = generate_response_side_effect

    # Used by scraped content quality scoring
    mock_gemini.analyze_content = AsyncMock(
        return_value={"result": '"quality_score": 85'})

    # --- Mock Web Scraper (depth-following loop) ---
    mock_scraper = MockWebScraper.return_value

    def scrape_page_side_effect(url: str):
        if url == "http://example.com/rag":
            # depth 2
            return _mk_scraped_page(url, links=["http://example.com/rag/link1", "http://example.com/rag/link2"])
        if url == "http://example.com/finetune":
            # depth 2
            return _mk_scraped_page(url, links=["http://example.com/finetune/link1"])
        if url.endswith("/link1"):
            return _mk_scraped_page(url, links=[])
        if url.endswith("/link2"):
            return _mk_scraped_page(url, links=[])
        return _mk_scraped_page(url, links=[])

    mock_scraper.scrape_page = AsyncMock(side_effect=scrape_page_side_effect)

    # --- Execute ---
    engine = ResearchEngine(config)

    session_id = await engine.start_research_session("RAG vs fine-tuning")

    # First run: needs clarification
    result1 = await engine.conduct_research(session_id)
    assert result1["status"] == "needs_clarification"
    assert len(result1["questions"]) >= 2

    # Second run: proceed through all stages
    user_responses = {q["question"]: "ok" for q in result1["questions"]}
    result2 = await engine.conduct_research(session_id, user_responses=user_responses)

    assert result2["status"] == "completed"

    session_data = result2["session_data"]
    stages = session_data["stages"]

    # Stage completeness
    assert stages["intent_analysis"]["status"] == "completed"
    assert stages["data_gathering"]["status"] == "completed"
    assert stages["analysis"]["status"] == "completed"
    assert stages["report_generation"]["status"] == "completed"

    # Longest-path features in analysis
    analysis_result = stages["analysis"]["result"]
    assert len(analysis_result["themes"]) >= 2  # created after retry loop
    assert len(analysis_result["conflicts"]) >= 1  # created after retry loop

    summaries = analysis_result["summaries"]
    assert "executive" in summaries
    assert "comparison" in summaries
    assert "timeline" in summaries
    assert "pros_cons" in summaries

    # Data gathering loops hit
    data_result = stages["data_gathering"]["result"]
    assert "internal_knowledge" in data_result["sources"]
    assert "google_search" in data_result["sources"]
    assert "web_scraping" in data_result["sources"]

    # Report exists
    report_path = stages["report_generation"]["result"]["report_path"]
    assert Path(report_path).exists()

    # --- Verify we exercised multi-iteration loops ---
    # 1) Search queries loop (3 search attempts, one timed out but still counts)
    assert counters["search_calls"] == config["MAX_SEARCH_QUERIES"]

    # 2) Analysis retry loops
    assert counters["themes_attempts"] >= 2
    assert counters["conflicts_attempts"] >= 2

    # 3) Scraping depth loop: scrape_page called for at least initial URLs + followed links
    assert mock_scraper.scrape_page.call_count >= 4

    # 4) Report generation loops should have been asked to write sections multiple times
    # We infer this by counting prompts.
    prompts = [call.args[0].lower()
               for call in mock_gemini.generate_response.call_args_list]
    assert sum(
        "generate a detailed section answering this research question" in p for p in prompts) >= 2
    assert sum(
        "generate a detailed section about this theme" in p for p in prompts) >= 2
