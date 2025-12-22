"""
Phase 3 Integration Tests for ADK Migration.

Tests the Report Generation pipeline including:
- ReportGeneratorAgent structure and configuration
- ReportFinalizerAgent with file_writer tool
- Report generation pipeline assembly
- file_writer tool functionality
- Full pipeline with report generation
"""

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Import report agents and tools
from src.agents.odyssey.report import (
    report_generator_agent,
    report_finalizer_agent,
    report_generation_pipeline,
)
from src.agents.odyssey.tools.file_writer import (
    save_report_to_file,
    get_report_path,
)
from src.agents.odyssey import root_agent


# ============================================================================
# Report Generator Agent Tests
# ============================================================================

class TestReportGeneratorAgent:
    """Tests for ReportGeneratorAgent configuration."""

    def test_agent_exists(self):
        """ReportGeneratorAgent should be defined."""
        assert report_generator_agent is not None

    def test_agent_name(self):
        """Agent should have correct name."""
        assert report_generator_agent.name == "ReportGeneratorAgent"

    def test_agent_description(self):
        """Agent should have meaningful description."""
        assert "report" in report_generator_agent.description.lower()
        assert "markdown" in report_generator_agent.description.lower()

    def test_agent_has_model(self):
        """Agent should have a model configured."""
        assert report_generator_agent.model is not None

    def test_agent_has_instruction(self):
        """Agent should have instruction (callable or string)."""
        assert report_generator_agent.instruction is not None
        # Instruction can be a callable or string
        if callable(report_generator_agent.instruction):
            # Call with None context to get the instruction string
            instruction = report_generator_agent.instruction(None)
            assert len(instruction) > 100
        else:
            assert len(report_generator_agent.instruction) > 100

    def test_instruction_contains_report_sections(self):
        """Instruction should mention key report sections."""
        if callable(report_generator_agent.instruction):
            instruction = report_generator_agent.instruction(None).lower()
        else:
            instruction = report_generator_agent.instruction.lower()
        assert "executive summary" in instruction
        assert "key findings" in instruction
        assert "detailed" in instruction
        assert "contradictory" in instruction
        assert "sources" in instruction or "bibliography" in instruction

    def test_instruction_references_state_keys(self):
        """Instruction should reference expected state keys."""
        if callable(report_generator_agent.instruction):
            instruction = report_generator_agent.instruction(None)
        else:
            instruction = report_generator_agent.instruction
        assert "{intent_result}" in instruction
        # Accept both required {var} and optional {var:} syntax for resilience
        assert "{consolidated_data}" in instruction or "{consolidated_data:}" in instruction
        assert "{analysis_result}" in instruction or "{analysis_result:}" in instruction

    def test_agent_output_key(self):
        """Agent should have correct output key."""
        assert report_generator_agent.output_key == "report_content"


# ============================================================================
# Report Finalizer Agent Tests
# ============================================================================

class TestReportFinalizerAgent:
    """Tests for ReportFinalizerAgent configuration."""

    def test_agent_exists(self):
        """ReportFinalizerAgent should be defined."""
        assert report_finalizer_agent is not None

    def test_agent_name(self):
        """Agent should have correct name."""
        assert report_finalizer_agent.name == "ReportFinalizerAgent"

    def test_agent_description(self):
        """Agent should have meaningful description."""
        desc = report_finalizer_agent.description.lower()
        assert "save" in desc or "file" in desc

    def test_agent_has_tools(self):
        """Agent should have file writing tools."""
        assert report_finalizer_agent.tools is not None
        assert len(report_finalizer_agent.tools) > 0

    def test_agent_has_save_tool(self):
        """Agent should have save_report_to_file tool."""
        tool_names = [
            getattr(t, '__name__', getattr(t, 'name', str(t)))
            for t in report_finalizer_agent.tools
        ]
        assert any('save' in name.lower() for name in tool_names)

    def test_agent_output_key(self):
        """Agent should have correct output key."""
        assert report_finalizer_agent.output_key == "report_metadata"


# ============================================================================
# Report Generation Pipeline Tests
# ============================================================================

class TestReportGenerationPipeline:
    """Tests for the report generation pipeline structure."""

    def test_pipeline_exists(self):
        """Pipeline should be defined."""
        assert report_generation_pipeline is not None

    def test_pipeline_name(self):
        """Pipeline should have correct name."""
        assert report_generation_pipeline.name == "ReportGenerationPipeline"

    def test_pipeline_is_sequential(self):
        """Pipeline should be a SequentialAgent."""
        from google.adk.agents import SequentialAgent
        assert isinstance(report_generation_pipeline, SequentialAgent)

    def test_pipeline_has_sub_agents(self):
        """Pipeline should have sub-agents."""
        assert hasattr(report_generation_pipeline, 'sub_agents')
        assert len(report_generation_pipeline.sub_agents) == 2

    def test_pipeline_order(self):
        """Sub-agents should be in correct order."""
        sub_agents = report_generation_pipeline.sub_agents
        assert sub_agents[0].name == "ReportGeneratorAgent"
        assert sub_agents[1].name == "ReportFinalizerAgent"


# ============================================================================
# File Writer Tool Tests
# ============================================================================

class TestFileWriterTool:
    """Tests for the file_writer tool functions."""

    def test_save_report_function_exists(self):
        """save_report_to_file should be callable."""
        assert callable(save_report_to_file)

    def test_get_report_path_function_exists(self):
        """get_report_path should be callable."""
        assert callable(get_report_path)

    def test_save_report_creates_file(self):
        """save_report_to_file should create a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"REPORTS_OUTPUT_PATH": tmpdir}):
                result = save_report_to_file(
                    content="# Test Report\n\nThis is test content.",
                    query_words="test query words"
                )

                assert result["success"] is True
                assert result["file_path"] is not None
                assert Path(result["file_path"]).exists()

    def test_save_report_returns_metadata(self):
        """save_report_to_file should return proper metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"REPORTS_OUTPUT_PATH": tmpdir}):
                content = "# Test Report\n\n## Section 1\n\nContent here."
                result = save_report_to_file(
                    content=content,
                    query_words="what are the best practices"
                )

                assert result["success"] is True
                metadata = result["metadata"]
                assert metadata["word_count"] > 0
                assert metadata["character_count"] == len(content)
                assert metadata["size_bytes"] > 0
                assert "created_at" in metadata

    def test_save_report_filename_format(self):
        """Filename should follow expected format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"REPORTS_OUTPUT_PATH": tmpdir}):
                result = save_report_to_file(
                    content="# Report",
                    query_words="how does machine learning work"
                )

                filename = result["filename"]
                assert filename.startswith("research_report_")
                assert filename.endswith(".md")
                assert "how_does_machine_learning" in filename

    def test_save_report_cleans_query_words(self):
        """Query words should be cleaned for filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"REPORTS_OUTPUT_PATH": tmpdir}):
                result = save_report_to_file(
                    content="# Report",
                    query_words="What's the best way? (2024)"
                )

                filename = result["filename"]
                # Should not contain special characters
                assert "?" not in filename
                assert "'" not in filename
                assert "(" not in filename

    def test_save_report_limits_query_words(self):
        """Filename should only use first few query words."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"REPORTS_OUTPUT_PATH": tmpdir}):
                result = save_report_to_file(
                    content="# Report",
                    query_words="one two three four five six seven eight nine ten"
                )

                filename = result["filename"]
                # Should have at most 5 word parts
                parts = filename.replace("research_report_", "").split("_")
                # Exclude timestamp parts (last 2)
                word_parts = parts[:-2]
                assert len(word_parts) <= 5

    def test_get_report_path_returns_valid_path(self):
        """get_report_path should return valid path string."""
        path = get_report_path("test query")
        assert isinstance(path, str)
        assert "research_report" in path
        assert path.endswith(".md")

    def test_save_report_creates_directory(self):
        """Should create reports directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "new_reports_dir")
            with patch.dict(os.environ, {"REPORTS_OUTPUT_PATH": new_dir}):
                result = save_report_to_file(
                    content="# Test",
                    query_words="test"
                )

                assert result["success"] is True
                assert Path(new_dir).exists()

    def test_save_report_content_integrity(self):
        """Saved content should match input content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"REPORTS_OUTPUT_PATH": tmpdir}):
                original_content = "# My Report\n\n## Findings\n\n- Item 1\n- Item 2"
                result = save_report_to_file(
                    content=original_content,
                    query_words="test"
                )

                with open(result["file_path"], 'r') as f:
                    saved_content = f.read()

                assert saved_content == original_content


# ============================================================================
# Full Pipeline Integration Tests
# ============================================================================

class TestFullPipelineWithReport:
    """Tests for the full research pipeline including report generation."""

    def test_root_agent_includes_report_pipeline(self):
        """Root agent should include report generation pipeline."""
        sub_agent_names = [a.name for a in root_agent.sub_agents]
        assert "ReportGenerationPipeline" in sub_agent_names

    def test_root_agent_has_four_stages(self):
        """Root agent should have 4 sub-agents (including report)."""
        assert len(root_agent.sub_agents) == 4

    def test_root_agent_pipeline_order(self):
        """Pipeline stages should be in correct order."""
        sub_agents = root_agent.sub_agents
        names = [a.name for a in sub_agents]

        # Report generation should be last
        assert names[-1] == "ReportGenerationPipeline"

        # Analysis should be before report
        analysis_idx = next(i for i, n in enumerate(names) if "Analysis" in n)
        report_idx = names.index("ReportGenerationPipeline")
        assert analysis_idx < report_idx

    def test_root_agent_description_mentions_report(self):
        """Root agent description should mention report generation."""
        desc = root_agent.description.lower()
        assert "report" in desc


# ============================================================================
# Confidence Scoring for Reports Tests
# ============================================================================

class TestReportConfidenceScoring:
    """Tests for confidence scoring of report results."""

    def test_score_report_function_exists(self):
        """Confidence scorer should handle report stage."""
        from src.agents.odyssey.tools.confidence import score_confidence

        result = score_confidence("report", {
            "content": "# Test Report\n\n## Sources\n\n- Source 1",
            "sections": {"executive_summary": "test"},
            "metadata": {"file_path": "/test/path.md"},
            "file_path": "/test/path.md"
        })

        assert "score" in result
        assert "level" in result
        assert "factors" in result

    def test_report_confidence_factors(self):
        """Report confidence should include expected factors."""
        from src.agents.odyssey.tools.confidence import score_confidence

        result = score_confidence("report", {
            "content": "# Report " * 200,  # Long content
            "sections": {"test": "section"},
            "metadata": {"file_path": "/path"},
            "file_path": "/path"
        })

        factors = result["factors"]
        assert "has_content" in factors
        assert "has_sections" in factors
        assert "file_saved" in factors


# ============================================================================
# Module Exports Tests
# ============================================================================

class TestModuleExports:
    """Tests for proper module exports."""

    def test_report_module_exports(self):
        """Report module should export expected items."""
        from src.agents.odyssey.report import (
            report_generator_agent,
            report_finalizer_agent,
            report_generation_pipeline,
        )
        assert report_generator_agent is not None
        assert report_finalizer_agent is not None
        assert report_generation_pipeline is not None

    def test_tools_module_exports_file_writer(self):
        """Tools module should export file writer functions."""
        from src.agents.odyssey.tools import (
            save_report_to_file,
            get_report_path,
        )
        assert save_report_to_file is not None
        assert get_report_path is not None

    def test_root_agent_importable(self):
        """Root agent should be importable from main package."""
        from src.agents.odyssey import root_agent
        assert root_agent is not None
        assert root_agent.name == "OdysseyResearchPipeline"
