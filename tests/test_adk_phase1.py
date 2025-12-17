"""
ADK Phase 1 Integration Tests.

Tests for Intent Analysis + Analysis pipeline using Google ADK.
Phase 1: SequentialAgent with IntentAnalyzerAgent + LoopAgent + AnalysisAgent
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestPhase1AgentStructure:
    """Test that Phase 1 agent structure is correctly defined."""

    def test_root_agent_import(self):
        """Test that root_agent can be imported."""
        from src.agents.odyssey.agent import root_agent
        assert root_agent is not None
        assert root_agent.name == "OdysseyResearchPipeline"

    def test_root_agent_has_sub_agents(self):
        """Test that root_agent has the expected sub-agents."""
        from src.agents.odyssey.agent import root_agent

        sub_agent_names = [agent.name for agent in root_agent.sub_agents]
        assert "IntentClarificationLoop" in sub_agent_names
        assert "AnalysisAgent" in sub_agent_names

    def test_intent_analyzer_agent_config(self):
        """Test IntentAnalyzerAgent configuration."""
        from src.agents.odyssey.intent.agent import intent_analyzer_agent

        assert intent_analyzer_agent.name == "IntentAnalyzerAgent"
        assert intent_analyzer_agent.output_key == "intent_result"
        assert "gemini" in intent_analyzer_agent.model.lower()

    def test_analysis_agent_config(self):
        """Test AnalysisAgent configuration."""
        from src.agents.odyssey.analysis.agent import analysis_agent

        assert analysis_agent.name == "AnalysisAgent"
        assert analysis_agent.output_key == "analysis_result"
        assert "gemini" in analysis_agent.model.lower()

    def test_confidence_checker_agent(self):
        """Test ConfidenceCheckerAgent configuration."""
        from src.agents.odyssey.intent.clarification import confidence_checker

        assert confidence_checker.name == "ConfidenceCheckerAgent"
        assert confidence_checker.description is not None
        # ConfidenceCheckerAgent is a custom BaseAgent that writes needs_clarification to state

    def test_loop_agent_config(self):
        """Test LoopAgent configuration for clarification."""
        from src.agents.odyssey.intent.clarification import intent_clarification_loop

        assert intent_clarification_loop.name == "IntentClarificationLoop"
        assert intent_clarification_loop.max_iterations == 5


class TestPhase1Tools:
    """Test Phase 1 tools."""

    def test_confidence_scorer_tool(self):
        """Test confidence scoring tool."""
        from src.agents.odyssey.tools.confidence import score_confidence

        # Test intent scoring
        result = score_confidence("intent", {
            "research_type": "factual",
            "domain": "technology",
            "key_entities": ["quantum computing"],
            "research_questions": ["What is quantum supremacy?"],
            "missing_information": []
        })

        assert "score" in result
        assert "level" in result
        assert "factors" in result
        assert isinstance(result["score"], int)
        assert 0 <= result["score"] <= 100

    def test_confidence_levels(self):
        """Test confidence level thresholds."""
        from src.agents.odyssey.tools.confidence import score_confidence

        # High confidence result
        high_result = score_confidence("intent", {
            "research_type": "comparison",
            "domain": "technology",
            "key_entities": ["AWS", "GCP"],
            "research_questions": ["Which is better for ML?"],
            "missing_information": []
        })
        assert high_result["score"] >= 75

        # Low confidence result (missing key fields)
        low_result = score_confidence("intent", {})
        assert low_result["score"] < 50


class TestPhase1StateKeys:
    """Test that Phase 1 uses correct state keys."""

    def test_intent_output_key(self):
        """Test intent analyzer uses correct output key."""
        from src.agents.odyssey.intent.agent import intent_analyzer_agent
        assert intent_analyzer_agent.output_key == "intent_result"

    def test_analysis_output_key(self):
        """Test analysis agent uses correct output key."""
        from src.agents.odyssey.analysis.agent import analysis_agent
        assert analysis_agent.output_key == "analysis_result"

    def test_confidence_checker_agent_defined(self):
        """Test confidence checker agent is defined with correct name."""
        from src.agents.odyssey.intent.clarification import confidence_checker
        # ConfidenceCheckerAgent is a custom BaseAgent that writes needs_clarification to state
        assert confidence_checker.name == "ConfidenceCheckerAgent"


class TestPhase1Instructions:
    """Test that agent instructions are properly defined."""

    def test_intent_analyzer_has_instruction(self):
        """Test IntentAnalyzerAgent has comprehensive instruction."""
        from src.agents.odyssey.intent.agent import intent_analyzer_agent

        instruction = intent_analyzer_agent.instruction
        assert instruction is not None
        assert len(instruction) > 100
        # Check for key instruction elements
        assert "research_type" in instruction.lower() or "type" in instruction.lower()

    def test_analysis_agent_has_instruction(self):
        """Test AnalysisAgent has comprehensive instruction."""
        from src.agents.odyssey.analysis.agent import analysis_agent

        instruction = analysis_agent.instruction
        assert instruction is not None
        assert len(instruction) > 100
        # Check for key analysis elements
        assert "theme" in instruction.lower() or "conflict" in instruction.lower()

    def test_analysis_reads_intent_result(self):
        """Test AnalysisAgent instruction references intent_result."""
        from src.agents.odyssey.analysis.agent import analysis_agent

        instruction = analysis_agent.instruction
        assert "{intent_result}" in instruction


class TestPhase1Imports:
    """Test that all Phase 1 imports work correctly."""

    def test_intent_package_imports(self):
        """Test intent package exports."""
        from src.agents.odyssey.intent import (
            intent_analyzer_agent,
            intent_clarification_loop,
        )
        assert intent_analyzer_agent is not None
        assert intent_clarification_loop is not None

    def test_analysis_package_imports(self):
        """Test analysis package exports."""
        from src.agents.odyssey.analysis import analysis_agent
        assert analysis_agent is not None

    def test_tools_package_imports(self):
        """Test tools package exports."""
        from src.agents.odyssey.tools import score_confidence
        assert score_confidence is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
