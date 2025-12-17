"""Stage-by-stage gating tests for Odyssey Engine.

Goal: ensure the pipeline does NOT accept arbitrary values and blindly proceed.
Each stage must produce a minimally valid, structured output before the engine
advances to the next stage.

These are pure unit tests: all external calls are mocked.
"""

from __future__ import annotations
from core.engine import ResearchEngine

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _mk_config(tmp_path: Path) -> dict:
    return {
        "GEMINI_API_KEY": "test_key",
        "GEMINI_MODEL": "gemini-2.5-pro",
        "CONFIDENCE_THRESHOLD": 75,
        "MAX_SCRAPING_DEPTH": 1,
        "SESSION_STORAGE_PATH": str(tmp_path / "sessions"),
        "REPORTS_OUTPUT_PATH": str(tmp_path / "reports"),
    }


def _mk_confidence(overall: float = 80.0) -> dict:
    return {
        "overall_confidence": overall,
        "confidence_level": "High",
        "factors": {},
        "recommendations": [],
    }


def _mk_valid_intent_result() -> dict:
    return {
        "needs_clarification": False,
        "intent": {
            "research_type": "general_research",
            "domain": "technology",
            "scope": "broad",
            "confidence": 90,
        },
        "context": {
            "comparison_needed": False,
            "timeline_needed": False,
            "pros_cons_needed": False,
            "detailed_report": False,
        },
        "confidence": 90,
        "research_questions": ["What is RAG?"],
        "key_entities": ["RAG"],
        "domain": "technology",
        "scope": "broad",
    }


def _mk_valid_data_result() -> dict:
    return {
        "sources": {
            "internal_knowledge": {"responses": []},
        },
        "consolidated_information": {"consolidated_text": "hello"},
        "source_reliability": {"internal_knowledge": 0.75},
        "conflicts": [],
        "coverage_assessment": {"overall_coverage": 75, "question_coverage": {}},
    }


def _mk_valid_analysis_result() -> dict:
    return {
        "themes": [
            {
                "title": "Theme 1",
                "description": "desc",
                "supporting_evidence": ["a"],
            }
        ],
        "conflicts": [],
        "summaries": {"executive": "summary"},
        "data_quality_assessment": {"sources_count": 1},
    }


def _mk_valid_report(tmp_path: Path) -> dict:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "report.md"
    report_path.write_text("# Report\n\nHello", encoding="utf-8")

    return {
        "content": "# Report\n\nHello",
        "file_path": str(report_path),
        "metadata": {"file_path": str(report_path)},
        "sections": {"executive_summary": "x"},
        "word_count": 2,
        "generation_time": "2025-01-01T00:00:00",
    }


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_stage_1_invalid_intent_does_not_proceed_to_stage_2(MockGeminiClient, tmp_path: Path):
    engine = ResearchEngine(_mk_config(tmp_path))

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value="not-a-dict")
    engine.data_gatherer.gather_data = AsyncMock()

    # Avoid confidence scorer calling any LLM methods
    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence())

    session_id = await engine.start_research_session("test query")
    result = await engine.conduct_research(session_id)

    assert result["status"] == "error"
    engine.data_gatherer.gather_data.assert_not_called()


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_stage_2_invalid_data_does_not_proceed_to_stage_3(MockGeminiClient, tmp_path: Path):
    engine = ResearchEngine(_mk_config(tmp_path))

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value=_mk_valid_intent_result())
    engine.data_gatherer.gather_data = AsyncMock(
        return_value={"sources": "oops"})  # invalid
    engine._analyze_and_compile = AsyncMock()

    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence())
    engine.confidence_scorer.score_data_quality = AsyncMock(
        return_value=_mk_confidence())

    session_id = await engine.start_research_session("test query")
    result = await engine.conduct_research(session_id)

    assert result["status"] == "error"
    engine._analyze_and_compile.assert_not_called()


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_stage_3_invalid_analysis_does_not_proceed_to_stage_4(MockGeminiClient, tmp_path: Path):
    engine = ResearchEngine(_mk_config(tmp_path))

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value=_mk_valid_intent_result())
    engine.data_gatherer.gather_data = AsyncMock(
        return_value=_mk_valid_data_result())
    engine._analyze_and_compile = AsyncMock(
        return_value={"themes": "bad"})  # invalid
    engine.report_generator.generate_report = AsyncMock()

    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence())
    engine.confidence_scorer.score_data_quality = AsyncMock(
        return_value=_mk_confidence())
    engine.confidence_scorer.score_analysis = AsyncMock(
        return_value=_mk_confidence())

    session_id = await engine.start_research_session("test query")
    result = await engine.conduct_research(session_id)

    assert result["status"] == "error"
    engine.report_generator.generate_report.assert_not_called()


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_stage_4_invalid_report_path_errors(MockGeminiClient, tmp_path: Path):
    engine = ResearchEngine(_mk_config(tmp_path))

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value=_mk_valid_intent_result())
    engine.data_gatherer.gather_data = AsyncMock(
        return_value=_mk_valid_data_result())
    engine._analyze_and_compile = AsyncMock(
        return_value=_mk_valid_analysis_result())
    engine.report_generator.generate_report = AsyncMock(
        return_value={"file_path": str(tmp_path / "reports" / "missing.md")})

    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence())
    engine.confidence_scorer.score_data_quality = AsyncMock(
        return_value=_mk_confidence())
    engine.confidence_scorer.score_analysis = AsyncMock(
        return_value=_mk_confidence())

    session_id = await engine.start_research_session("test query")
    result = await engine.conduct_research(session_id)

    assert result["status"] == "error"


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_successful_run_records_completed_stages_with_numeric_confidence(MockGeminiClient, tmp_path: Path):
    engine = ResearchEngine(_mk_config(tmp_path))

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value=_mk_valid_intent_result())
    engine.data_gatherer.gather_data = AsyncMock(
        return_value=_mk_valid_data_result())
    engine._analyze_and_compile = AsyncMock(
        return_value=_mk_valid_analysis_result())
    engine.report_generator.generate_report = AsyncMock(
        return_value=_mk_valid_report(tmp_path))

    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence(81.0))
    engine.confidence_scorer.score_data_quality = AsyncMock(
        return_value=_mk_confidence(71.0))
    engine.confidence_scorer.score_analysis = AsyncMock(
        return_value=_mk_confidence(61.0))
    engine.confidence_scorer.score_report_quality = AsyncMock(
        return_value=_mk_confidence(91.0))
    engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
        return_value=_mk_confidence(77.0))

    session_id = await engine.start_research_session("test query")
    result = await engine.conduct_research(session_id)

    assert result["status"] == "completed"
    session_data = result["session_data"]

    # Stage numbering (1..4) and completeness checks
    stages_in_order = [
        (1, "intent_analysis"),
        (2, "data_gathering"),
        (3, "analysis"),
        (4, "report_generation"),
    ]

    for stage_number, stage_name in stages_in_order:
        assert session_data["stages"][stage_name][
            "status"] == "completed", f"Stage {stage_number} ({stage_name}) not completed"
        conf = session_data["stages"][stage_name]["confidence"]
        assert isinstance(conf, dict)
        assert 0 <= conf.get(
            "overall_confidence", -1) <= 100, f"Stage {stage_number} ({stage_name}) confidence not 0..100"

    # Sanity check: report path saved
    report_path = session_data["stages"]["report_generation"]["result"]["report_path"]
    assert Path(report_path).exists()


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_stage_1_low_confidence_triggers_clarification(MockGeminiClient, tmp_path: Path):
    """Confidence below threshold should trigger clarification flow, not error."""
    engine = ResearchEngine(_mk_config(tmp_path))

    # Return intent with confidence 74% (below 75% threshold)
    low_confidence_intent = _mk_valid_intent_result()
    low_confidence_intent["confidence"] = 74  # Below threshold of 75
    low_confidence_intent["missing_information"] = [
        "specific use case", "budget constraints"]

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value=low_confidence_intent)
    engine.data_gatherer.gather_data = AsyncMock()

    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence(74.0))

    session_id = await engine.start_research_session("test query")
    result = await engine.conduct_research(session_id)

    # Should return needs_clarification, NOT error
    assert result["status"] == "needs_clarification"
    assert "questions" in result
    assert len(result["questions"]) > 0
    assert result["confidence"] == 74
    assert result["confidence_threshold"] == 75
    # Data gathering should NOT have been called
    engine.data_gatherer.gather_data.assert_not_called()


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_stage_1_exactly_at_threshold_proceeds(MockGeminiClient, tmp_path: Path):
    """Confidence exactly at threshold should proceed."""
    engine = ResearchEngine(_mk_config(tmp_path))

    # Return intent with confidence exactly at threshold (75%)
    threshold_intent = _mk_valid_intent_result()
    threshold_intent["confidence"] = 75  # Exactly at threshold

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value=threshold_intent)
    engine.data_gatherer.gather_data = AsyncMock(
        return_value=_mk_valid_data_result())
    engine._analyze_and_compile = AsyncMock(
        return_value=_mk_valid_analysis_result())
    engine.report_generator.generate_report = AsyncMock(
        return_value=_mk_valid_report(tmp_path))

    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence(75.0))
    engine.confidence_scorer.score_data_quality = AsyncMock(
        return_value=_mk_confidence(75.0))
    engine.confidence_scorer.score_analysis = AsyncMock(
        return_value=_mk_confidence(75.0))
    engine.confidence_scorer.score_report_quality = AsyncMock(
        return_value=_mk_confidence(75.0))
    engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
        return_value=_mk_confidence(75.0))

    session_id = await engine.start_research_session("test query")
    result = await engine.conduct_research(session_id)

    # Should succeed since confidence >= threshold
    assert result["status"] == "completed"
    engine.data_gatherer.gather_data.assert_called_once()


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_max_clarification_rounds_forces_proceed(MockGeminiClient, tmp_path: Path):
    """After max clarification rounds, pipeline should proceed even with low confidence."""
    config = _mk_config(tmp_path)
    config["MAX_FOLLOW_UP_QUESTIONS"] = 2  # Set low for testing
    engine = ResearchEngine(config)

    # Return intent with confidence below threshold
    low_confidence_intent = _mk_valid_intent_result()
    low_confidence_intent["confidence"] = 60  # Below 75% threshold
    low_confidence_intent["missing_information"] = ["context"]

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value=low_confidence_intent)
    engine.data_gatherer.gather_data = AsyncMock(
        return_value=_mk_valid_data_result())
    engine._analyze_and_compile = AsyncMock(
        return_value=_mk_valid_analysis_result())
    engine.report_generator.generate_report = AsyncMock(
        return_value=_mk_valid_report(tmp_path))

    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence(60.0))
    engine.confidence_scorer.score_data_quality = AsyncMock(
        return_value=_mk_confidence(70.0))
    engine.confidence_scorer.score_analysis = AsyncMock(
        return_value=_mk_confidence(70.0))
    engine.confidence_scorer.score_report_quality = AsyncMock(
        return_value=_mk_confidence(70.0))
    engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
        return_value=_mk_confidence(67.0))

    session_id = await engine.start_research_session("test query")

    # First call - should need clarification (round 1)
    result1 = await engine.conduct_research(session_id)
    assert result1["status"] == "needs_clarification"
    assert result1["clarification_round"] == 1

    # Second call with responses - should still need clarification (round 2)
    result2 = await engine.conduct_research(session_id, {"q1": "answer1"})
    assert result2["status"] == "needs_clarification"
    assert result2["clarification_round"] == 2

    # Third call - max rounds reached (2), should force proceed
    result3 = await engine.conduct_research(session_id, {"q2": "answer2"})
    assert result3["status"] == "completed"  # Forced to proceed
    engine.data_gatherer.gather_data.assert_called_once()


@pytest.mark.asyncio
@patch("core.engine.GeminiClient")
async def test_clarification_returns_round_info(MockGeminiClient, tmp_path: Path):
    """Clarification response should include round tracking info."""
    engine = ResearchEngine(_mk_config(tmp_path))

    low_confidence_intent = _mk_valid_intent_result()
    low_confidence_intent["confidence"] = 50
    low_confidence_intent["missing_information"] = ["details"]

    engine.intent_analyzer.analyze_intent = AsyncMock(
        return_value=low_confidence_intent)

    engine.confidence_scorer.score_intent_analysis = AsyncMock(
        return_value=_mk_confidence(50.0))

    session_id = await engine.start_research_session("test query")
    result = await engine.conduct_research(session_id)

    assert result["status"] == "needs_clarification"
    assert "clarification_round" in result
    assert "max_clarification_rounds" in result
    assert result["clarification_round"] == 1
    assert result["max_clarification_rounds"] == 5  # Default from config
