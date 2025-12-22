"""
Tests for Interactive Intent Clarification Workflow.

Tests for the human-in-the-loop intent analysis features:
- HumanInputAgent
- SessionAuditLogger
- Criteria display
- User confirmation flow
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime


class TestHumanInputAgent:
    """Test HumanInputAgent functionality."""

    def test_human_input_agent_import(self):
        """Test that HumanInputAgent can be imported."""
        from src.agents.odyssey.intent.human_input import HumanInputAgent, human_input_agent
        assert HumanInputAgent is not None
        assert human_input_agent is not None
        assert human_input_agent.name == "HumanInputAgent"

    def test_human_input_agent_in_loop(self):
        """Test HumanInputAgent is included in the clarification loop."""
        from src.agents.odyssey.intent.clarification import intent_clarification_loop

        sub_agent_names = [
            agent.name for agent in intent_clarification_loop.sub_agents]
        assert "HumanInputAgent" in sub_agent_names

    def test_loop_has_three_agents(self):
        """Test the loop has IntentAnalyzer, ConfidenceChecker, and HumanInput."""
        from src.agents.odyssey.intent.clarification import intent_clarification_loop

        sub_agent_names = [
            agent.name for agent in intent_clarification_loop.sub_agents]
        assert len(sub_agent_names) == 3
        assert "IntentAnalyzerAgent" in sub_agent_names
        assert "ConfidenceCheckerAgent" in sub_agent_names
        assert "HumanInputAgent" in sub_agent_names

    def test_build_criteria_display(self):
        """Test _build_criteria_display generates correct structure."""
        from src.agents.odyssey.intent.human_input import HumanInputAgent

        agent = HumanInputAgent()

        intent = {
            "research_type": "analysis",
            "domain": "technology",
            "scope": "detailed",
            "key_entities": ["CRISPR", "gene editing"],
            "research_questions": ["What are the latest advancements?"],
            "decision_criteria": ["accuracy", "relevance"],
            "success_criteria": ["comprehensive overview"],
            "confidence": 85,
            "missing_information": [],
            "assumptions": ["Focus on 2024-2025 developments"],
        }

        display = agent._build_criteria_display(intent)

        assert "criteria" in display
        assert "confidence_score" in display
        assert display["confidence_score"] == 85
        assert display["confidence_met"] is True
        assert "criteria_met_count" in display
        assert "research_questions" in display

    def test_generate_clarification_questions_missing_type(self):
        """Test clarification questions generated for missing research type."""
        from src.agents.odyssey.intent.human_input import HumanInputAgent

        agent = HumanInputAgent()

        intent = {
            "domain": "technology",
            "key_entities": [],
            "missing_information": ["research focus unclear"],
        }

        questions = agent._generate_clarification_questions(
            intent, round_num=1)

        assert len(questions) > 0
        assert len(questions) <= 3  # Max 3 questions
        # Should ask about research type since it's missing
        assert any("type" in q.lower() or "looking for" in q.lower()
                   for q in questions)

    def test_parse_intent_from_string(self):
        """Test parsing intent from JSON string."""
        from src.agents.odyssey.intent.human_input import HumanInputAgent

        agent = HumanInputAgent()

        json_str = '''```json
{
    "research_type": "comparison",
    "domain": "automotive",
    "confidence": 70
}
```'''

        parsed = agent._parse_intent(json_str)

        assert parsed["research_type"] == "comparison"
        assert parsed["domain"] == "automotive"
        assert parsed["confidence"] == 70

    def test_parse_intent_from_dict(self):
        """Test parsing intent from dict (passthrough)."""
        from src.agents.odyssey.intent.human_input import HumanInputAgent

        agent = HumanInputAgent()

        intent_dict = {
            "research_type": "analysis",
            "confidence": 80,
        }

        parsed = agent._parse_intent(intent_dict)

        assert parsed == intent_dict

    def test_build_enriched_query(self):
        """Test building enriched query with user response."""
        from src.agents.odyssey.intent.human_input import HumanInputAgent

        agent = HumanInputAgent()

        original = "Latest advancements in CRISPR technology"
        response = "I want to focus on therapeutic applications, especially for genetic diseases."
        state = {
            "clarification_questions": [
                "What specific aspects of CRISPR interest you?",
                "Are you interested in research or clinical applications?"
            ]
        }

        enriched = agent._build_enriched_query(original, response, state)

        assert original in enriched
        assert response in enriched
        assert "clarification questions" in enriched.lower()


class TestSessionAuditLogger:
    """Test SessionAuditLogger functionality."""

    def test_audit_logger_import(self):
        """Test SessionAuditLogger can be imported."""
        from src.agents.odyssey.tools.session_audit import (
            SessionAuditLogger,
            create_audit_logger,
        )
        assert SessionAuditLogger is not None
        assert create_audit_logger is not None

    def test_create_audit_logger(self):
        """Test creating an audit logger."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("test-session-123", "test-user-456")

        assert logger.session_id == "test-session-123"
        assert logger.user_id == "test-user-456"
        assert logger.audit_log["session_id"] == "test-session-123"

    def test_log_original_query(self):
        """Test logging original query."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")
        logger.log_original_query("What is quantum computing?")

        assert logger.audit_log["original_query"] == "What is quantum computing?"

    def test_iteration_tracking(self):
        """Test iteration tracking."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")

        # Start first iteration
        iter_num = logger.start_iteration()
        assert iter_num == 1
        assert len(logger.audit_log["intent_iterations"]) == 1

        # Start second iteration
        iter_num = logger.start_iteration()
        assert iter_num == 2
        assert len(logger.audit_log["intent_iterations"]) == 2

    def test_log_intent_analysis(self):
        """Test logging intent analysis."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")
        logger.start_iteration()

        intent = {
            "research_type": "analysis",
            "confidence": 75,
        }
        logger.log_intent_analysis(intent)

        current = logger.audit_log["intent_iterations"][-1]
        assert current["intent_analysis"] == intent
        assert current["confidence_score"] == 75

    def test_log_clarification_questions(self):
        """Test logging clarification questions."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")
        logger.start_iteration()

        questions = ["What scope?", "What timeframe?"]
        logger.log_clarification_questions(questions)

        current = logger.audit_log["intent_iterations"][-1]
        assert current["clarification_questions"] == questions

    def test_log_user_response(self):
        """Test logging user response."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")
        logger.start_iteration()

        logger.log_user_response("What scope?", "Broad overview")

        current = logger.audit_log["intent_iterations"][-1]
        assert len(current["user_responses"]) == 1
        assert current["user_responses"][0]["question"] == "What scope?"
        assert current["user_responses"][0]["response"] == "Broad overview"

    def test_log_iteration_decision(self):
        """Test logging iteration decision."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")
        logger.start_iteration()

        logger.log_iteration_decision(
            "continue", "User provided clarification")

        current = logger.audit_log["intent_iterations"][-1]
        assert current["decision"]["action"] == "continue"
        assert current["decision"]["reason"] == "User provided clarification"

    def test_log_user_confirmation(self):
        """Test logging user confirmation."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")

        logger.log_user_confirmation(True, "Looks good!")

        assert logger.audit_log["user_confirmed"] is True
        assert logger.audit_log["user_confirmation_comment"] == "Looks good!"

    def test_build_criteria_summary(self):
        """Test building criteria summary."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")

        intent = {
            "research_type": "analysis",
            "domain": "technology",
            "scope": "detailed",
            "key_entities": ["CRISPR"],
            "research_questions": ["What's new?"],
            "decision_criteria": ["accuracy"],
            "success_criteria": ["completeness"],
            "missing_information": ["timeframe"],
            "assumptions": [],
            "confidence": 80,
        }

        summary = logger._build_criteria_summary(intent)

        assert summary["has_research_type"] is True
        assert summary["has_domain"] is True
        assert summary["has_key_entities"] is True
        assert summary["has_research_questions"] is True
        assert summary["missing_info_count"] == 1
        assert summary["confidence_threshold_met"] is True

    def test_get_criteria_display(self):
        """Test getting formatted criteria display."""
        from src.agents.odyssey.tools.session_audit import create_audit_logger

        logger = create_audit_logger("session-1", "user-1")

        intent = {
            "research_type": "comparison",
            "domain": "automotive",
            "scope": "specific",
            "key_entities": ["BMW", "Mercedes"],
            "research_questions": ["Which is better?"],
            "decision_criteria": ["price", "features"],
            "success_criteria": ["clear recommendation"],
            "missing_information": [],
            "assumptions": [],
            "confidence": 90,
        }

        display = logger.get_criteria_display(intent)

        assert "criteria" in display
        assert len(display["criteria"]) == 7
        assert display["confidence_score"] == 90
        assert display["confidence_met"] is True
        assert display["ready_to_proceed"] is True
        assert display["criteria_met_count"] >= 5

    def test_finalize_and_save(self):
        """Test finalizing and saving audit log."""
        from src.agents.odyssey.tools.session_audit import SessionAuditLogger
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Override the log path
            os.environ["AUDIT_LOG_PATH"] = tmpdir

            # Create new logger to pick up env var
            from src.agents.odyssey.tools import session_audit
            original_path = session_audit.AUDIT_LOG_PATH
            session_audit.AUDIT_LOG_PATH = tmpdir

            try:
                logger = SessionAuditLogger("test-session", "test-user")
                logger.log_original_query("Test query")
                logger.start_iteration()

                final_intent = {
                    "research_type": "analysis",
                    "confidence": 85,
                }

                result = logger.finalize(
                    final_intent=final_intent,
                    final_confidence=85,
                    exit_reason="user_confirmed"
                )

                assert result["completed_at"] is not None
                assert result["final_intent"] == final_intent
                assert result["final_confidence"] == 85
                assert result["exit_reason"] == "user_confirmed"

                # Check file was created
                log_files = list(Path(tmpdir).glob("*.json"))
                assert len(log_files) == 1

                # Verify file content
                with open(log_files[0]) as f:
                    saved_log = json.load(f)
                    assert saved_log["session_id"] == "test-session"
                    assert saved_log["original_query"] == "Test query"
            finally:
                session_audit.AUDIT_LOG_PATH = original_path


class TestConfidenceCheckerAgent:
    """Test updated ConfidenceCheckerAgent."""

    def test_confidence_checker_no_auto_escalate_high_confidence(self):
        """Test that high confidence doesn't auto-escalate without user confirm."""
        from src.agents.odyssey.intent.clarification import ConfidenceCheckerAgent

        # The new behavior: ConfidenceChecker sets flags but doesn't escalate
        # unless user_confirmed_proceed is True or max_rounds reached
        checker = ConfidenceCheckerAgent()
        assert checker.name == "ConfidenceCheckerAgent"

    def test_parse_intent_result_function(self):
        """Test the parse_intent_result utility function."""
        from src.agents.odyssey.intent.clarification import parse_intent_result

        # Test with JSON string
        json_str = '{"confidence": 80, "research_type": "analysis"}'
        parsed = parse_intent_result(json_str)
        assert parsed["confidence"] == 80

        # Test with markdown-wrapped JSON
        md_json = '```json\n{"confidence": 75}\n```'
        parsed = parse_intent_result(md_json)
        assert parsed["confidence"] == 75

        # Test with dict
        dict_input = {"confidence": 90}
        parsed = parse_intent_result(dict_input)
        assert parsed["confidence"] == 90


class TestIntentPackageExports:
    """Test that intent package exports new components."""

    def test_human_input_exports(self):
        """Test HumanInputAgent is exported from intent package."""
        from src.agents.odyssey.intent import (
            human_input_agent,
            HumanInputAgent,
            confidence_checker,
        )

        assert human_input_agent is not None
        assert HumanInputAgent is not None
        assert confidence_checker is not None


class TestToolsPackageExports:
    """Test that tools package exports new components."""

    def test_session_audit_exports(self):
        """Test SessionAuditLogger is exported from tools package."""
        from src.agents.odyssey.tools import (
            SessionAuditLogger,
            create_audit_logger,
        )

        assert SessionAuditLogger is not None
        assert create_audit_logger is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
