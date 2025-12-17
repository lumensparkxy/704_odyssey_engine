"""
Phase 4 Integration Tests for ADK Migration.

Tests the CLI migration and full pipeline integration:
- ADK CLI interface
- Entrypoint
- Full pipeline structure
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


# ============================================================================
# ADK CLI Tests
# ============================================================================

class TestADKCLI:
    """Tests for the ADK-powered CLI interface."""

    def test_adk_cli_importable(self):
        """OdysseyADKCLI should be importable."""
        from src.cli.adk_interface import OdysseyADKCLI
        assert OdysseyADKCLI is not None

    def test_adk_cli_has_app_name(self):
        """ADK CLI should have APP_NAME constant."""
        from src.cli.adk_interface import OdysseyADKCLI
        assert hasattr(OdysseyADKCLI, 'APP_NAME')
        assert OdysseyADKCLI.APP_NAME == "odyssey_research_engine"

    def test_adk_cli_init_creates_session_service(self):
        """ADK CLI should initialize session service."""
        from src.cli.adk_interface import OdysseyADKCLI

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            cli = OdysseyADKCLI()
            assert cli.session_service is not None

    def test_adk_cli_config_loading(self):
        """ADK CLI should load config from environment."""
        from src.cli.adk_interface import OdysseyADKCLI

        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test_key",
            "GEMINI_MODEL": "gemini-test",
            "REPORTS_OUTPUT_PATH": "/test/reports"
        }):
            cli = OdysseyADKCLI()
            assert cli.config["GEMINI_API_KEY"] == "test_key"
            assert cli.config["GEMINI_MODEL"] == "gemini-test"
            assert cli.config["REPORTS_OUTPUT_PATH"] == "/test/reports"

    def test_adk_cli_user_id_generated(self):
        """ADK CLI should generate a user ID."""
        from src.cli.adk_interface import OdysseyADKCLI

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            cli = OdysseyADKCLI()
            assert cli.user_id is not None
            assert cli.user_id.startswith("user_")


# ============================================================================
# Entrypoint Tests
# ============================================================================

class TestEntrypoint:
    """Tests for the CLI entrypoint."""

    def test_entrypoint_importable(self):
        """Entrypoint main should be importable."""
        from src.cli.entrypoint import main
        assert main is not None

    def test_entrypoint_is_click_command(self):
        """Main should be a click command."""
        from src.cli.entrypoint import main
        import click
        assert hasattr(main, 'params')

    def test_entrypoint_has_query_option(self):
        """Entrypoint should have --query/-q option."""
        from src.cli.entrypoint import main

        param_names = [p.name for p in main.params]
        assert 'query' in param_names


# ============================================================================
# Full Pipeline Structure Tests
# ============================================================================

class TestFullPipelineStructure:
    """Tests for the complete ADK pipeline structure."""

    def test_root_agent_has_four_stages(self):
        """Root agent should have exactly 4 sub-agents."""
        from src.agents.odyssey import root_agent
        assert len(root_agent.sub_agents) == 4

    def test_root_agent_stage_order(self):
        """Pipeline stages should be in correct order."""
        from src.agents.odyssey import root_agent

        stage_names = [a.name for a in root_agent.sub_agents]

        # Check order
        assert "IntentClarificationLoop" in stage_names[0]
        assert "DataGathering" in stage_names[1]
        assert "Analysis" in stage_names[2]
        assert "Report" in stage_names[3]

    def test_all_agents_have_names(self):
        """All agents in pipeline should have names."""
        from src.agents.odyssey import root_agent

        for agent in root_agent.sub_agents:
            assert agent.name is not None
            assert len(agent.name) > 0

    def test_all_agents_have_descriptions(self):
        """All agents in pipeline should have descriptions."""
        from src.agents.odyssey import root_agent

        for agent in root_agent.sub_agents:
            assert agent.description is not None


# ============================================================================
# CLI Package Tests
# ============================================================================

class TestCLIPackage:
    """Tests for CLI package exports."""

    def test_adk_cli_accessible_from_package(self):
        """OdysseyADKCLI should be accessible from cli package."""
        from src.cli import OdysseyADKCLI
        assert OdysseyADKCLI is not None


# ============================================================================
# Tools Export Tests
# ============================================================================

class TestToolsExports:
    """Tests for tools module exports."""

    def test_all_tools_exported(self):
        """All tools should be properly exported."""
        from src.agents.odyssey.tools import (
            score_confidence,
            save_report_to_file,
            get_report_path,
        )

        assert callable(score_confidence)
        assert callable(save_report_to_file)
        assert callable(get_report_path)


# ============================================================================
# Integration Tests
# ============================================================================

class TestADKIntegration:
    """Integration tests for ADK components."""

    def test_runner_can_be_created(self):
        """ADK Runner should be creatable with our agent."""
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from src.agents.odyssey import root_agent

        session_service = InMemorySessionService()

        runner = Runner(
            app_name="test_app",
            agent=root_agent,
            session_service=session_service,
        )

        assert runner is not None
        assert runner.agent == root_agent

    @pytest.mark.asyncio
    async def test_session_can_be_created(self):
        """ADK session should be creatable."""
        from google.adk.sessions import InMemorySessionService

        session_service = InMemorySessionService()

        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user",
            state={"test": "value"},
        )

        assert session is not None
        assert session.state["test"] == "value"


# ============================================================================
# README Tests
# ============================================================================

class TestDocumentation:
    """Tests for documentation updates."""

    def test_readme_mentions_adk(self):
        """README should mention ADK."""
        readme_path = Path(__file__).parent.parent / "README.md"
        content = readme_path.read_text()

        assert "ADK" in content
        assert "Google ADK" in content or "Agent Development Kit" in content

    def test_readme_has_architecture_diagram(self):
        """README should have architecture diagram."""
        readme_path = Path(__file__).parent.parent / "README.md"
        content = readme_path.read_text()

        assert "OdysseyResearchPipeline" in content
        assert "SequentialAgent" in content
