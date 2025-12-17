"""
Phase 4 Integration Tests for ADK Migration.

Tests the CLI migration, session utilities, and full pipeline integration:
- ADK CLI interface
- Entrypoint with --adk/--legacy flags
- Session migration utilities
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
    """Tests for the CLI entrypoint with --adk/--legacy flags."""

    def test_entrypoint_importable(self):
        """Entrypoint main should be importable."""
        from src.cli.entrypoint import main
        assert main is not None

    def test_entrypoint_is_click_command(self):
        """Main should be a click command."""
        from src.cli.entrypoint import main
        import click
        assert hasattr(main, 'params')

    def test_entrypoint_has_adk_option(self):
        """Entrypoint should have --adk/--legacy option."""
        from src.cli.entrypoint import main
        
        param_names = [p.name for p in main.params]
        assert 'adk' in param_names

    def test_entrypoint_adk_default_true(self):
        """ADK mode should be default (True)."""
        from src.cli.entrypoint import main
        
        adk_param = next(p for p in main.params if p.name == 'adk')
        assert adk_param.default is True


# ============================================================================
# Session Migration Tests
# ============================================================================

class TestSessionMigration:
    """Tests for session migration utilities."""

    def test_list_legacy_sessions_empty(self):
        """list_legacy_sessions should handle empty directory."""
        from src.utils.session_migration import list_legacy_sessions
        
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions = list_legacy_sessions(tmpdir)
            assert sessions == []

    def test_list_legacy_sessions_finds_sessions(self):
        """list_legacy_sessions should find session files."""
        from src.utils.session_migration import list_legacy_sessions
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock session file
            session_data = {
                "session_id": "test-session-123",
                "initial_query": "Test query",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00"
            }
            session_file = Path(tmpdir) / "session_test-session-123.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
            
            sessions = list_legacy_sessions(tmpdir)
            assert len(sessions) == 1
            assert sessions[0]["session_id"] == "test-session-123"
            assert sessions[0]["status"] == "completed"

    def test_extract_session_state(self):
        """extract_session_state should convert legacy format to ADK state."""
        from src.utils.session_migration import extract_session_state
        
        with tempfile.TemporaryDirectory() as tmpdir:
            session_data = {
                "session_id": "test-123",
                "initial_query": "Test query",
                "stages": {
                    "intent_analysis": {
                        "result": {
                            "intent": {
                                "research_type": "comparison",
                                "domain": "technology"
                            }
                        }
                    },
                    "data_gathering": {
                        "result": {
                            "consolidated_information": {"key": "value"},
                            "sources": {"google_search": {}}
                        }
                    }
                }
            }
            session_file = Path(tmpdir) / "session.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
            
            state = extract_session_state(str(session_file))
            
            assert state["original_query"] == "Test query"
            assert state["intent_result"]["research_type"] == "comparison"
            assert "consolidated_data" in state

    def test_get_session_report_path(self):
        """get_session_report_path should extract report path."""
        from src.utils.session_migration import get_session_report_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            session_data = {
                "stages": {
                    "report_generation": {
                        "result": {
                            "file_path": "/reports/test_report.md"
                        }
                    }
                }
            }
            session_file = Path(tmpdir) / "session.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
            
            path = get_session_report_path(str(session_file))
            assert path == "/reports/test_report.md"

    def test_archive_legacy_sessions(self):
        """archive_legacy_sessions should move files to archive."""
        from src.utils.session_migration import archive_legacy_sessions
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create session file
            session_file = Path(tmpdir) / "session_test.json"
            session_file.write_text("{}")
            
            archive_dir = Path(tmpdir) / "archive"
            
            result = archive_legacy_sessions(tmpdir, str(archive_dir))
            
            assert result["archived"] == 1
            assert archive_dir.exists()
            assert not session_file.exists()
            assert (archive_dir / "session_test.json").exists()


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

    def test_cli_package_lazy_imports(self):
        """CLI package should use lazy imports."""
        import src.cli
        
        # Check __all__ is defined
        assert hasattr(src.cli, '__all__')
        assert "OdysseyCLI" in src.cli.__all__
        assert "OdysseyADKCLI" in src.cli.__all__

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
            scrape_urls,
            scrape_single_url,
            save_report_to_file,
            get_report_path,
        )
        
        assert callable(score_confidence)
        assert callable(scrape_urls)
        assert callable(scrape_single_url)
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
