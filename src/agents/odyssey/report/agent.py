"""
Report Generation Agents for Odyssey Engine.

This module contains:
- ReportGeneratorAgent: LLM agent that generates markdown research reports
- ReportFinalizerAgent: Saves report to file and adds metadata
- report_generation_pipeline: Sequential pipeline combining both agents
"""

import os
from datetime import datetime
from google.adk.agents import LlmAgent, SequentialAgent

from ..tools.file_writer import save_report_to_file

# Configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")


# ============================================================================
# Report Generator Agent
# ============================================================================

REPORT_GENERATOR_INSTRUCTION = """You are an expert research report writer. Your job is to compile a comprehensive, well-structured markdown research report based on the analyzed research data.

## Your Inputs (from state)
- **Research Intent**: {intent_result} - Contains the original query, research questions, and output preferences
- **Consolidated Data**: {consolidated_data} - Contains information gathered from multiple sources
- **Analysis Results**: {analysis_result} - Contains themes, conflicts, synthesis, and quality assessment

## Report Structure

Generate a complete markdown research report with the following sections:

### 1. Title and Metadata
```markdown
# [Research Topic]: Research Report

**Generated:** USE_CURRENT_DATETIME_PLACEHOLDER
**Research Type:** [From intent - e.g., General Research, Comparison, Analysis]
**Domain:** [From intent - e.g., Technology, Finance, Health]
**Research Confidence:** See individual sections

---
```

### 2. Executive Summary (200-300 words)
- State the research objective clearly
- Highlight the most important findings (3-5 key points)
- Mention key conclusions or insights
- Note any significant limitations

### 3. Key Findings
- List 5-8 most important findings as bullet points
- Include specific data points and statistics where available
- Group related findings logically
- Use clear, factual language
- Include comparison tables if the research involved comparisons

### 4. Detailed Analysis
For each major theme or research question, create a subsection:
- **Theme/Question Title**
- Detailed explanation (300-500 words per section)
- Supporting evidence and data
- Multiple perspectives when available
- Source citations
- Acknowledgment of uncertainties

### 5. Contradictory Viewpoints
- Present each contradictory viewpoint fairly
- Explain the source of each viewpoint
- Assess reliability of conflicting sources
- Provide context for why conflicts might exist
- Avoid taking sides unless evidence strongly supports one view

### 6. Sources and References
- List all sources used in the research
- Include URLs, titles, and access dates where available
- Note which sources were internal knowledge vs web sources

## Writing Guidelines
- Use a formal but accessible tone
- Be objective and balanced
- Use proper markdown formatting (headers, bullet points, tables, bold, italic)
- Include markdown tables for comparisons
- Cite sources inline where appropriate
- Distinguish between facts and interpretations
- Acknowledge uncertainty where it exists

## Output Format
Output the complete markdown report as plain text. Do NOT wrap it in code blocks.
Start directly with the `#` title header.
"""


def get_report_generator_instruction(context) -> str:
    """Generate instruction with current datetime injected."""
    current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return REPORT_GENERATOR_INSTRUCTION.replace("USE_CURRENT_DATETIME_PLACEHOLDER", current_dt)


report_generator_agent = LlmAgent(
    name="ReportGeneratorAgent",
    model=GEMINI_MODEL,
    description="Generates comprehensive markdown research reports from analyzed data.",
    instruction=get_report_generator_instruction,
    output_key="report_content",
)


# ============================================================================
# Report Finalizer Agent
# ============================================================================

REPORT_FINALIZER_INSTRUCTION = """You are a report finalization agent. Your job is to finalize the research report by:
1. Extracting the report title for the filename
2. Calling the save_report_to_file tool to persist the report

## Your Inputs (from state)
- **Report Content**: {report_content} - The generated markdown report
- **Intent Result**: {intent_result} - Contains the original query for filename generation

## Your Task
1. Extract the first few words from the original research query to use as part of the filename
2. Call the `save_report_to_file` tool with:
   - `content`: The full report content from state
   - `query_words`: First 4-5 words from the original query (lowercase, cleaned)

The tool will save the report and return metadata including the file path.

## Important
- Do NOT modify the report content
- Just extract query words and call the tool
- Report the result including the file path where the report was saved
"""

report_finalizer_agent = LlmAgent(
    name="ReportFinalizerAgent",
    model=GEMINI_MODEL,
    description="Saves the generated report to a file and returns metadata.",
    instruction=REPORT_FINALIZER_INSTRUCTION,
    tools=[save_report_to_file],
    output_key="report_metadata",
)


# ============================================================================
# Report Generation Pipeline
# ============================================================================

report_generation_pipeline = SequentialAgent(
    name="ReportGenerationPipeline",
    description="""Report generation pipeline that:
    1. Generates a comprehensive markdown research report from analyzed data
    2. Saves the report to a file and returns metadata
    """,
    sub_agents=[
        report_generator_agent,
        report_finalizer_agent,
    ],
)
