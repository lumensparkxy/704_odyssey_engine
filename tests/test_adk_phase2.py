"""
ADK Phase 2 Integration Tests.

Tests for Parallel Data Gathering pipeline using Google ADK.
Phase 2: ParallelAgent with InternalKnowledgeAgent + GoogleSearchAgent + WebScraperAgent
         + ConsolidatorAgent
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestPhase2AgentStructure:
    """Test that Phase 2 agent structure is correctly defined."""

    def test_root_agent_includes_data_gathering(self):
        """Test that root_agent now includes data gathering pipeline."""
        from src.agents.odyssey.agent import root_agent

        sub_agent_names = [agent.name for agent in root_agent.sub_agents]
        assert "DataGatheringPipeline" in sub_agent_names

    def test_data_gathering_pipeline_structure(self):
        """Test DataGatheringPipeline has correct sub-agents."""
        from src.agents.odyssey.data_gathering import data_gathering_pipeline

        assert data_gathering_pipeline.name == "DataGatheringPipeline"
        sub_agent_names = [
            agent.name for agent in data_gathering_pipeline.sub_agents]
        assert "ParallelDataGatherer" in sub_agent_names
        assert "ConsolidatorAgent" in sub_agent_names

    def test_parallel_gatherer_structure(self):
        """Test ParallelDataGatherer has correct sub-agents."""
        from src.agents.odyssey.data_gathering.parallel_gatherer import parallel_data_gatherer

        assert parallel_data_gatherer.name == "ParallelDataGatherer"
        sub_agent_names = [
            agent.name for agent in parallel_data_gatherer.sub_agents]
        assert "InternalKnowledgeAgent" in sub_agent_names
        assert "GoogleSearchAgent" in sub_agent_names
        assert "WebScraperAgent" in sub_agent_names


class TestPhase2DataGatheringAgents:
    """Test individual data gathering agents."""

    def test_internal_knowledge_agent_config(self):
        """Test InternalKnowledgeAgent configuration."""
        from src.agents.odyssey.data_gathering.internal_knowledge import internal_knowledge_agent

        assert internal_knowledge_agent.name == "InternalKnowledgeAgent"
        assert internal_knowledge_agent.output_key == "internal_knowledge_result"
        assert "gemini" in internal_knowledge_agent.model.lower()

    def test_google_search_agent_config(self):
        """Test GoogleSearchAgent configuration."""
        from src.agents.odyssey.data_gathering.google_search import google_search_agent

        assert google_search_agent.name == "GoogleSearchAgent"
        assert google_search_agent.output_key == "google_search_result"
        assert google_search_agent.tools is not None
        assert len(google_search_agent.tools) > 0

    def test_web_scraper_agent_config(self):
        """Test WebScraperAgent configuration with url_context tool."""
        from src.agents.odyssey.data_gathering.web_scraper_agent import web_scraper_agent

        assert web_scraper_agent.name == "WebScraperAgent"
        assert web_scraper_agent.output_key == "web_scraping_result"
        assert web_scraper_agent.tools is not None
        # Now uses url_context built-in tool
        assert len(web_scraper_agent.tools) == 1
        assert "UrlContextTool" in type(web_scraper_agent.tools[0]).__name__

    def test_consolidator_agent_config(self):
        """Test ConsolidatorAgent configuration."""
        from src.agents.odyssey.data_gathering.consolidator import consolidator_agent

        assert consolidator_agent.name == "ConsolidatorAgent"
        assert consolidator_agent.output_key == "consolidated_data"
        assert "gemini" in consolidator_agent.model.lower()


class TestPhase2StateKeys:
    """Test that Phase 2 uses correct state keys."""

    def test_internal_knowledge_output_key(self):
        """Test InternalKnowledgeAgent output key."""
        from src.agents.odyssey.data_gathering.internal_knowledge import internal_knowledge_agent
        assert internal_knowledge_agent.output_key == "internal_knowledge_result"

    def test_google_search_output_key(self):
        """Test GoogleSearchAgent output key."""
        from src.agents.odyssey.data_gathering.google_search import google_search_agent
        assert google_search_agent.output_key == "google_search_result"

    def test_web_scraper_output_key(self):
        """Test WebScraperAgent output key."""
        from src.agents.odyssey.data_gathering.web_scraper_agent import web_scraper_agent
        assert web_scraper_agent.output_key == "web_scraping_result"

    def test_consolidator_output_key(self):
        """Test ConsolidatorAgent output key."""
        from src.agents.odyssey.data_gathering.consolidator import consolidator_agent
        assert consolidator_agent.output_key == "consolidated_data"


class TestPhase2Instructions:
    """Test that Phase 2 agent instructions are properly defined."""

    def test_internal_knowledge_reads_intent(self):
        """Test InternalKnowledgeAgent reads intent_result."""
        from src.agents.odyssey.data_gathering.internal_knowledge import internal_knowledge_agent

        instruction = internal_knowledge_agent.instruction
        assert "{intent_result}" in instruction

    def test_google_search_reads_intent(self):
        """Test GoogleSearchAgent reads intent_result."""
        from src.agents.odyssey.data_gathering.google_search import google_search_agent

        instruction = google_search_agent.instruction
        assert "{intent_result}" in instruction

    def test_web_scraper_reads_intent(self):
        """Test WebScraperAgent reads intent_result."""
        from src.agents.odyssey.data_gathering.web_scraper_agent import web_scraper_agent

        instruction = web_scraper_agent.instruction
        assert "{intent_result}" in instruction

    def test_consolidator_reads_all_sources(self):
        """Test ConsolidatorAgent reads from all data sources (with optional syntax)."""
        from src.agents.odyssey.data_gathering.consolidator import consolidator_agent

        instruction = consolidator_agent.instruction
        assert "{intent_result}" in instruction
        # These use optional syntax {var:} to handle missing state gracefully
        assert "{internal_knowledge_result:}" in instruction
        assert "{google_search_result:}" in instruction
        assert "{web_scraping_result:}" in instruction

    def test_analysis_reads_consolidated_data(self):
        """Test AnalysisAgent now reads consolidated_data."""
        from src.agents.odyssey.analysis.agent import analysis_agent

        instruction = analysis_agent.instruction
        # Accept both required {consolidated_data} and optional {consolidated_data:} syntax
        assert "{consolidated_data}" in instruction or "{consolidated_data:}" in instruction


class TestPhase2Imports:
    """Test that all Phase 2 imports work correctly."""

    def test_data_gathering_package_imports(self):
        """Test data_gathering package exports."""
        from src.agents.odyssey.data_gathering import (
            data_gathering_pipeline,
            internal_knowledge_agent,
            google_search_agent,
            web_scraper_agent,
            consolidator_agent,
        )
        assert data_gathering_pipeline is not None
        assert internal_knowledge_agent is not None
        assert google_search_agent is not None
        assert web_scraper_agent is not None
        assert consolidator_agent is not None

    def test_tools_exports(self):
        """Test tools are exported from tools package."""
        from src.agents.odyssey.tools import score_confidence, save_report_to_file
        assert score_confidence is not None
        assert save_report_to_file is not None


class TestPhase2PipelineOrder:
    """Test the correct order of agents in the pipeline."""

    def test_root_pipeline_order(self):
        """Test root agent has correct pipeline order."""
        from src.agents.odyssey.agent import root_agent

        sub_agent_names = [agent.name for agent in root_agent.sub_agents]

        # Intent should come before data gathering
        intent_idx = sub_agent_names.index("IntentClarificationLoop")
        data_idx = sub_agent_names.index("DataGatheringPipeline")
        analysis_idx = sub_agent_names.index("AnalysisAgent")

        assert intent_idx < data_idx < analysis_idx

    def test_data_gathering_pipeline_order(self):
        """Test data gathering pipeline order."""
        from src.agents.odyssey.data_gathering import data_gathering_pipeline

        sub_agent_names = [
            agent.name for agent in data_gathering_pipeline.sub_agents]

        # Parallel gatherer should come before consolidator
        parallel_idx = sub_agent_names.index("ParallelDataGatherer")
        consolidator_idx = sub_agent_names.index("ConsolidatorAgent")

        assert parallel_idx < consolidator_idx


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
