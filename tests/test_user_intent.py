"""
Test suite for User Intent Flow.

This module tests the complete intent analysis and clarification flow:
1. No clarification required - proceeds directly to next stage
2. Clarification needed - loops until confidence threshold is reached
3. Max clarification rounds reached - force proceeds with warning

These tests verify the core pipeline behavior that the Odyssey Engine
follows when processing user research queries.
"""

from __future__ import annotations
from core.engine import ResearchEngine

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================

def _mk_config(tmp_path: Path, **overrides) -> dict:
    """Create test configuration with optional overrides."""
    config = {
        "GEMINI_API_KEY": "test_key",
        "GEMINI_MODEL": "gemini-2.5-pro",
        "CONFIDENCE_THRESHOLD": 75,
        "MAX_FOLLOW_UP_QUESTIONS": 5,
        "MAX_SCRAPING_DEPTH": 1,
        "SESSION_STORAGE_PATH": str(tmp_path / "sessions"),
        "REPORTS_OUTPUT_PATH": str(tmp_path / "reports"),
    }
    config.update(overrides)
    return config


def _mk_confidence(overall: float = 80.0) -> dict:
    """Create a confidence score structure."""
    return {
        "overall_confidence": overall,
        "confidence_level": "High" if overall >= 75 else "Medium" if overall >= 50 else "Low",
        "factors": {},
        "recommendations": [],
    }


def _mk_intent_result(
    confidence: int = 90,
    needs_clarification: bool = False,
    questions: list = None,
    missing_info: list = None,
) -> dict:
    """Create a valid intent analysis result."""
    result = {
        "needs_clarification": needs_clarification,
        "intent": {
            "research_type": "comparison",
            "domain": "technology",
            "scope": "detailed",
            "confidence": confidence,
        },
        "context": {
            "comparison_needed": True,
            "timeline_needed": False,
            "pros_cons_needed": True,
            "detailed_report": True,
        },
        "confidence": confidence,
        "research_questions": ["What are the differences between RAG and fine-tuning?"],
        "key_entities": ["RAG", "fine-tuning", "LLM", "GPT-4"],
        "domain": "technology",
        "scope": "detailed",
        "decision_criteria": ["cost", "latency", "accuracy"],
        "success_criteria": ["clear recommendation", "pros/cons"],
    }

    if needs_clarification and questions:
        result["questions"] = questions
    if missing_info:
        result["missing_information"] = missing_info

    return result


def _mk_data_result() -> dict:
    """Create a valid data gathering result."""
    return {
        "sources": {
            "internal_knowledge": {"responses": ["RAG uses retrieval..."]},
            "web_search": {"results": ["Recent article about fine-tuning..."]},
        },
        "consolidated_information": {
            "rag_overview": "RAG combines retrieval with generation...",
            "finetuning_overview": "Fine-tuning adapts model weights...",
        },
        "source_reliability": {"internal_knowledge": 0.85, "web_search": 0.75},
        "conflicts": [],
        "coverage_assessment": {"overall_coverage": 80, "question_coverage": {}},
    }


def _mk_analysis_result() -> dict:
    """Create a valid analysis result."""
    return {
        "themes": [
            {
                "title": "Cost Comparison",
                "description": "RAG vs fine-tuning cost analysis",
                "supporting_evidence": ["RAG requires infrastructure", "Fine-tuning has training costs"],
            },
            {
                "title": "Performance Characteristics",
                "description": "Latency and accuracy tradeoffs",
                "supporting_evidence": ["RAG adds retrieval latency", "Fine-tuning has fixed inference"],
            },
        ],
        "conflicts": [],
        "summaries": {"executive": "Both approaches have tradeoffs..."},
        "data_quality_assessment": {"sources_count": 2, "freshness_score": 0.8},
    }


def _mk_report(tmp_path: Path) -> dict:
    """Create a valid report result with actual file."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "research_report.md"
    report_path.write_text(
        "# Research Report\n\n## RAG vs Fine-tuning\n\nContent here...", encoding="utf-8")

    return {
        "content": "# Research Report\n\n## RAG vs Fine-tuning\n\nContent here...",
        "file_path": str(report_path),
        "metadata": {"file_path": str(report_path), "word_count": 150},
        "sections": ["Executive Summary", "Key Findings", "Recommendations"],
        "word_count": 150,
        "generation_time": "2025-12-17T00:00:00",
    }


def _mk_clarifying_questions() -> list:
    """Create sample clarifying questions."""
    return [
        {
            "question": "What is your primary use case for the chatbot?",
            "purpose": "To understand deployment context",
            "examples": ["customer support", "internal helpdesk", "sales assistant"],
            "allow_unknown": True,
        },
        {
            "question": "What are your latency requirements?",
            "purpose": "To evaluate real-time constraints",
            "examples": ["<100ms", "1-2 seconds acceptable", "no strict requirements"],
            "allow_unknown": True,
        },
        {
            "question": "What is your budget for LLM API costs?",
            "purpose": "To consider cost tradeoffs",
            "examples": ["<$100/month", "$100-500/month", "flexible"],
            "allow_unknown": True,
        },
    ]


# =============================================================================
# Test Case 1: No Clarification Required - Direct Proceed
# =============================================================================

class TestNoClarificationRequired:
    """Test cases where intent confidence is high enough to proceed directly."""

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_high_confidence_proceeds_directly(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: User query is clear, confidence >= threshold
        EXPECTED: Pipeline proceeds directly to data gathering without clarification
        """
        engine = ResearchEngine(_mk_config(tmp_path))

        # Intent with 90% confidence (above 75% threshold)
        high_confidence_intent = _mk_intent_result(
            confidence=90, needs_clarification=False)

        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=high_confidence_intent)
        engine.data_gatherer.gather_data = AsyncMock(
            return_value=_mk_data_result())
        engine._analyze_and_compile = AsyncMock(
            return_value=_mk_analysis_result())
        engine.report_generator.generate_report = AsyncMock(
            return_value=_mk_report(tmp_path))

        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(90.0))
        engine.confidence_scorer.score_data_quality = AsyncMock(
            return_value=_mk_confidence(85.0))
        engine.confidence_scorer.score_analysis = AsyncMock(
            return_value=_mk_confidence(80.0))
        engine.confidence_scorer.score_report_quality = AsyncMock(
            return_value=_mk_confidence(85.0))
        engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
            return_value=_mk_confidence(85.0))

        # Execute
        session_id = await engine.start_research_session(
            "Compare RAG vs fine-tuning for customer support chatbots"
        )
        result = await engine.conduct_research(session_id)

        # Verify
        assert result["status"] == "completed", "Should complete without clarification"
        assert engine.data_gatherer.gather_data.called, "Data gathering should be called"
        assert engine.report_generator.generate_report.called, "Report should be generated"

        # Verify session data
        session_data = result["session_data"]
        assert session_data["stages"]["intent_analysis"]["status"] == "completed"
        assert session_data["stages"]["data_gathering"]["status"] == "completed"
        assert session_data["stages"]["report_generation"]["status"] == "completed"

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_exactly_at_threshold_proceeds(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Confidence is exactly at threshold (75%)
        EXPECTED: Pipeline proceeds (>= threshold)
        """
        engine = ResearchEngine(_mk_config(tmp_path))

        # Intent with exactly 75% confidence
        threshold_intent = _mk_intent_result(
            confidence=75, needs_clarification=False)

        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=threshold_intent)
        engine.data_gatherer.gather_data = AsyncMock(
            return_value=_mk_data_result())
        engine._analyze_and_compile = AsyncMock(
            return_value=_mk_analysis_result())
        engine.report_generator.generate_report = AsyncMock(
            return_value=_mk_report(tmp_path))

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

        session_id = await engine.start_research_session("Clear research question")
        result = await engine.conduct_research(session_id)

        assert result["status"] == "completed"
        engine.data_gatherer.gather_data.assert_called_once()


# =============================================================================
# Test Case 2: Clarification Loop - Eventually Reaches Threshold
# =============================================================================

class TestClarificationLoopReachesThreshold:
    """Test cases where clarification is needed and eventually succeeds."""

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_one_round_clarification_then_proceeds(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Initial confidence is low, one round of clarification raises it above threshold
        EXPECTED: 
            - Round 1: Returns needs_clarification with questions
            - Round 2 (with answers): Proceeds to completion
        """
        engine = ResearchEngine(_mk_config(tmp_path))

        # Track call count to return different results
        call_count = [0]

        async def mock_analyze_intent(query, user_responses=None):
            call_count[0] += 1
            if user_responses is None:
                # First call: low confidence, needs clarification
                return _mk_intent_result(
                    confidence=60,
                    needs_clarification=True,
                    questions=_mk_clarifying_questions(),
                    missing_info=["use case", "latency requirements"],
                )
            else:
                # Second call with user responses: confidence improved
                return _mk_intent_result(confidence=85, needs_clarification=False)

        engine.intent_analyzer.analyze_intent = AsyncMock(
            side_effect=mock_analyze_intent)
        engine.data_gatherer.gather_data = AsyncMock(
            return_value=_mk_data_result())
        engine._analyze_and_compile = AsyncMock(
            return_value=_mk_analysis_result())
        engine.report_generator.generate_report = AsyncMock(
            return_value=_mk_report(tmp_path))

        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(85.0))
        engine.confidence_scorer.score_data_quality = AsyncMock(
            return_value=_mk_confidence(80.0))
        engine.confidence_scorer.score_analysis = AsyncMock(
            return_value=_mk_confidence(80.0))
        engine.confidence_scorer.score_report_quality = AsyncMock(
            return_value=_mk_confidence(85.0))
        engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
            return_value=_mk_confidence(82.0))

        # Round 1: Initial query
        session_id = await engine.start_research_session(
            "Compare approaches but I'm not sure about evaluation criteria"
        )
        result1 = await engine.conduct_research(session_id)

        # Verify Round 1: Should need clarification
        assert result1["status"] == "needs_clarification"
        assert "questions" in result1
        assert len(result1["questions"]) > 0
        assert result1["confidence"] == 60
        assert result1["clarification_round"] == 1

        # Round 2: User provides answers
        user_responses = {
            "What is your primary use case for the chatbot?": "customer support",
            "What are your latency requirements?": "<500ms",
            "What is your budget for LLM API costs?": "flexible",
        }
        result2 = await engine.conduct_research(session_id, user_responses)

        # Verify Round 2: Should complete
        assert result2["status"] == "completed"
        assert engine.data_gatherer.gather_data.called
        assert call_count[0] == 2, "Intent analyzer should be called twice"

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_multiple_rounds_clarification_then_proceeds(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Multiple rounds of clarification needed before threshold is reached
        EXPECTED: 
            - Rounds 1-2: Returns needs_clarification
            - Round 3: Confidence finally meets threshold, proceeds
        """
        config = _mk_config(tmp_path, MAX_FOLLOW_UP_QUESTIONS=5)
        engine = ResearchEngine(config)

        call_count = [0]

        async def mock_analyze_intent(query, user_responses=None):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: 50% confidence
                return _mk_intent_result(
                    confidence=50,
                    needs_clarification=True,
                    questions=_mk_clarifying_questions()[:2],
                    missing_info=["use case", "constraints"],
                )
            elif call_count[0] == 2:
                # Second call: improved to 65% but still below 75%
                return _mk_intent_result(
                    confidence=65,
                    needs_clarification=True,
                    questions=_mk_clarifying_questions()[1:2],
                    missing_info=["specific metrics"],
                )
            else:
                # Third call: confidence now at 80%
                return _mk_intent_result(confidence=80, needs_clarification=False)

        engine.intent_analyzer.analyze_intent = AsyncMock(
            side_effect=mock_analyze_intent)
        engine.data_gatherer.gather_data = AsyncMock(
            return_value=_mk_data_result())
        engine._analyze_and_compile = AsyncMock(
            return_value=_mk_analysis_result())
        engine.report_generator.generate_report = AsyncMock(
            return_value=_mk_report(tmp_path))

        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(80.0))
        engine.confidence_scorer.score_data_quality = AsyncMock(
            return_value=_mk_confidence(75.0))
        engine.confidence_scorer.score_analysis = AsyncMock(
            return_value=_mk_confidence(75.0))
        engine.confidence_scorer.score_report_quality = AsyncMock(
            return_value=_mk_confidence(80.0))
        engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
            return_value=_mk_confidence(77.0))

        session_id = await engine.start_research_session("Vague query needing multiple clarifications")

        # Round 1
        result1 = await engine.conduct_research(session_id)
        assert result1["status"] == "needs_clarification"
        assert result1["clarification_round"] == 1
        assert result1["confidence"] == 50

        # Round 2
        result2 = await engine.conduct_research(session_id, {"q1": "answer1"})
        assert result2["status"] == "needs_clarification"
        assert result2["clarification_round"] == 2
        assert result2["confidence"] == 65

        # Round 3 - should succeed
        result3 = await engine.conduct_research(session_id, {"q2": "answer2"})
        assert result3["status"] == "completed"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_clarification_includes_round_info(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Verify clarification response includes all tracking information
        EXPECTED: Response includes confidence, threshold, round number, and max rounds
        """
        engine = ResearchEngine(_mk_config(
            tmp_path, MAX_FOLLOW_UP_QUESTIONS=3))

        low_intent = _mk_intent_result(
            confidence=55,
            needs_clarification=True,
            questions=_mk_clarifying_questions(),
            missing_info=["details"],
        )
        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=low_intent)
        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(55.0))

        session_id = await engine.start_research_session("Query needing clarification")
        result = await engine.conduct_research(session_id)

        # Verify all tracking info is present
        assert result["status"] == "needs_clarification"
        assert "confidence" in result
        assert result["confidence"] == 55
        assert "confidence_threshold" in result
        assert result["confidence_threshold"] == 75
        assert "clarification_round" in result
        assert result["clarification_round"] == 1
        assert "max_clarification_rounds" in result
        assert result["max_clarification_rounds"] == 3


# =============================================================================
# Test Case 3: Max Clarification Rounds - Force Proceed with Warning
# =============================================================================

class TestMaxClarificationRoundsForcesProceed:
    """Test cases where max clarification rounds is reached and pipeline force proceeds."""

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_max_rounds_reached_forces_proceed(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Confidence never reaches threshold, max rounds exhausted
        EXPECTED: After max rounds, pipeline force proceeds with warning
        """
        config = _mk_config(
            tmp_path, MAX_FOLLOW_UP_QUESTIONS=2)  # Low limit for testing
        engine = ResearchEngine(config)

        # Always return low confidence - never improves
        low_confidence_intent = _mk_intent_result(
            confidence=60,
            needs_clarification=True,
            questions=_mk_clarifying_questions()[:1],
            missing_info=["persistent_issue"],
        )
        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=low_confidence_intent)
        engine.data_gatherer.gather_data = AsyncMock(
            return_value=_mk_data_result())
        engine._analyze_and_compile = AsyncMock(
            return_value=_mk_analysis_result())
        engine.report_generator.generate_report = AsyncMock(
            return_value=_mk_report(tmp_path))

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

        session_id = await engine.start_research_session("Query that can't be fully clarified")

        # Round 1 - needs clarification
        result1 = await engine.conduct_research(session_id)
        assert result1["status"] == "needs_clarification"
        assert result1["clarification_round"] == 1
        assert result1["max_clarification_rounds"] == 2

        # Round 2 - still needs clarification
        result2 = await engine.conduct_research(session_id, {"q1": "vague answer"})
        assert result2["status"] == "needs_clarification"
        assert result2["clarification_round"] == 2

        # Round 3 - max reached, should force proceed
        result3 = await engine.conduct_research(session_id, {"q2": "still vague"})
        assert result3["status"] == "completed", "Should force proceed after max rounds"

        # Verify data gathering was called (pipeline proceeded)
        engine.data_gatherer.gather_data.assert_called_once()

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_force_proceed_marks_session(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Force proceed should mark the session/intent as forced
        EXPECTED: Intent result contains forced_proceed and max_clarifications_reached flags
        """
        config = _mk_config(
            tmp_path, MAX_FOLLOW_UP_QUESTIONS=1)  # Only 1 round
        engine = ResearchEngine(config)

        low_intent = _mk_intent_result(
            confidence=50,
            needs_clarification=True,
            questions=_mk_clarifying_questions()[:1],
            missing_info=["info"],
        )
        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=low_intent)
        engine.data_gatherer.gather_data = AsyncMock(
            return_value=_mk_data_result())
        engine._analyze_and_compile = AsyncMock(
            return_value=_mk_analysis_result())
        engine.report_generator.generate_report = AsyncMock(
            return_value=_mk_report(tmp_path))

        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(50.0))
        engine.confidence_scorer.score_data_quality = AsyncMock(
            return_value=_mk_confidence(65.0))
        engine.confidence_scorer.score_analysis = AsyncMock(
            return_value=_mk_confidence(65.0))
        engine.confidence_scorer.score_report_quality = AsyncMock(
            return_value=_mk_confidence(65.0))
        engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
            return_value=_mk_confidence(61.0))

        session_id = await engine.start_research_session("Query")

        # Round 1 - needs clarification
        result1 = await engine.conduct_research(session_id)
        assert result1["status"] == "needs_clarification"

        # Round 2 - should force proceed (max was 1)
        result2 = await engine.conduct_research(session_id, {"q": "a"})
        assert result2["status"] == "completed"

        # Check session data for force proceed markers
        session_data = result2["session_data"]
        intent_result = session_data["stages"]["intent_analysis"]["result"]
        assert intent_result.get("forced_proceed") == True
        assert intent_result.get("max_clarifications_reached") == True

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_confidence_below_threshold_but_max_rounds_proceeds(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Final confidence is still below threshold but max rounds reached
        EXPECTED: Pipeline proceeds anyway with the suboptimal understanding
        """
        config = _mk_config(tmp_path, CONFIDENCE_THRESHOLD=80,
                            MAX_FOLLOW_UP_QUESTIONS=2)
        engine = ResearchEngine(config)

        # Returns 70% confidence - below 80% threshold but won't improve
        intent_70 = _mk_intent_result(
            confidence=70,
            needs_clarification=True,
            questions=_mk_clarifying_questions()[:1],
            missing_info=["clarity"],
        )
        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=intent_70)
        engine.data_gatherer.gather_data = AsyncMock(
            return_value=_mk_data_result())
        engine._analyze_and_compile = AsyncMock(
            return_value=_mk_analysis_result())
        engine.report_generator.generate_report = AsyncMock(
            return_value=_mk_report(tmp_path))

        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(70.0))
        engine.confidence_scorer.score_data_quality = AsyncMock(
            return_value=_mk_confidence(70.0))
        engine.confidence_scorer.score_analysis = AsyncMock(
            return_value=_mk_confidence(70.0))
        engine.confidence_scorer.score_report_quality = AsyncMock(
            return_value=_mk_confidence(70.0))
        engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
            return_value=_mk_confidence(70.0))

        session_id = await engine.start_research_session("Query")

        # Go through all rounds
        result1 = await engine.conduct_research(session_id)
        assert result1["status"] == "needs_clarification"
        assert result1["confidence"] == 70
        assert result1["confidence_threshold"] == 80

        result2 = await engine.conduct_research(session_id, {"q1": "a1"})
        assert result2["status"] == "needs_clarification"

        result3 = await engine.conduct_research(session_id, {"q2": "a2"})
        # Should complete even though confidence (70) < threshold (80)
        assert result3["status"] == "completed"

        # Verify the low confidence is recorded
        overall_conf = result3["confidence"]
        assert overall_conf["overall_confidence"] == 70.0


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================

class TestEdgeCases:
    """Edge cases and boundary condition tests."""

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_confidence_just_below_threshold_asks_clarification(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Confidence is 74% (just below 75% threshold)
        EXPECTED: Triggers clarification flow
        """
        engine = ResearchEngine(_mk_config(tmp_path))

        intent_74 = _mk_intent_result(
            confidence=74,
            needs_clarification=False,  # Analyzer says no, but engine should override
            missing_info=["minor detail"],
        )
        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=intent_74)
        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(74.0))

        session_id = await engine.start_research_session("Almost clear query")
        result = await engine.conduct_research(session_id)

        # Should trigger clarification even though analyzer said no
        assert result["status"] == "needs_clarification"
        assert result["confidence"] == 74

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_zero_max_rounds_proceeds_immediately(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: MAX_FOLLOW_UP_QUESTIONS is 0
        EXPECTED: Should proceed immediately without any clarification
        """
        config = _mk_config(tmp_path, MAX_FOLLOW_UP_QUESTIONS=0)
        engine = ResearchEngine(config)

        # When max rounds is 0, even with low confidence, engine should proceed immediately
        low_intent = _mk_intent_result(
            confidence=50, needs_clarification=False)
        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=low_intent)
        engine.data_gatherer.gather_data = AsyncMock(
            return_value=_mk_data_result())
        engine._analyze_and_compile = AsyncMock(
            return_value=_mk_analysis_result())
        engine.report_generator.generate_report = AsyncMock(
            return_value=_mk_report(tmp_path))

        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(50.0))
        engine.confidence_scorer.score_data_quality = AsyncMock(
            return_value=_mk_confidence(60.0))
        engine.confidence_scorer.score_analysis = AsyncMock(
            return_value=_mk_confidence(60.0))
        engine.confidence_scorer.score_report_quality = AsyncMock(
            return_value=_mk_confidence(60.0))
        engine.confidence_scorer.calculate_overall_confidence = AsyncMock(
            return_value=_mk_confidence(57.0))

        session_id = await engine.start_research_session("Query")
        result = await engine.conduct_research(session_id)

        # With 0 max rounds, should proceed immediately
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    @patch("core.engine.GeminiClient")
    async def test_clarification_round_tracked_in_session(self, MockGeminiClient, tmp_path: Path):
        """
        SCENARIO: Session data should track the clarification round count
        EXPECTED: clarification_round is persisted in session_data
        """
        engine = ResearchEngine(_mk_config(
            tmp_path, MAX_FOLLOW_UP_QUESTIONS=3))

        low_intent = _mk_intent_result(
            confidence=50,
            needs_clarification=True,
            questions=_mk_clarifying_questions()[:1],
        )
        engine.intent_analyzer.analyze_intent = AsyncMock(
            return_value=low_intent)
        engine.confidence_scorer.score_intent_analysis = AsyncMock(
            return_value=_mk_confidence(50.0))

        session_id = await engine.start_research_session("Query")

        # Round 1
        result1 = await engine.conduct_research(session_id)
        session1 = result1["session_data"]
        # Not incremented until responses
        assert session1.get("clarification_round", 0) == 0

        # Round 2 - with responses
        result2 = await engine.conduct_research(session_id, {"q": "a"})
        session2 = result2["session_data"]
        assert session2.get("clarification_round") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
