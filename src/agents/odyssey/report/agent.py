"""
Report Generation Agents for Odyssey Engine.

This module contains:
- ReportGeneratorAgent: LLM agent that generates markdown research reports
- ReportFinalizerAgent: Saves report to file and adds metadata
- report_generation_pipeline: Sequential pipeline combining both agents
"""

import os
from google.adk.agents import LlmAgent, SequentialAgent

from ..tools.file_writer import save_report_to_file

# Configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


# ============================================================================
# Report Generator Agent
# ============================================================================

# NOTE: Using a string instruction (not a function) so ADK automatically
# substitutes {variable} placeholders with session state values.
# This is critical - function instructions bypass state injection!
REPORT_GENERATOR_INSTRUCTION = """You are an expert research report writer. Your job is to compile a comprehensive, well-structured markdown research report based on the analyzed research data.

## Your Inputs (from state)
You MUST use the following data to generate the report. Do NOT make up topics or ignore this data:

### Research Intent (CRITICAL - defines what the report should be about):
{intent_result}

### Consolidated Data (information gathered from multiple sources):
{consolidated_data}

### Analysis Results (themes, conflicts, synthesis):
{analysis_result}

### Output Preferences (report customization):
{output_preferences}

**IMPORTANT**: 
1. The report topic MUST match the research intent above. Do not hallucinate a different topic.
2. If any input shows "Partial", "timed out", or indicates some data sources failed:
   - Still generate a complete report with available data
   - Note limitations in the Executive Summary
   - A partial report is still valuable to the user

## Report Customization Guidelines

Adapt the report based on the output_preferences above:

### Report Length:
- **brief**: 1-2 pages, focus on executive summary and key findings only. Skip detailed analysis.
- **standard**: 3-5 pages, balanced coverage of all sections.
- **comprehensive**: 6+ pages, full detailed analysis with extensive evidence and citations.

### Target Audience:
- **general**: Use accessible language, avoid jargon, explain technical terms.
- **professional**: Business-focused language, emphasize actionable insights and ROI.
- **technical**: Expert-level terminology, include technical details and specifications.

### Format Style:
- **executive**: Lead with conclusions, summary-focused, bullet points for quick reading.
- **academic**: Thorough analysis, detailed citations, formal structure, methodology notes.
- **practical**: Action-oriented, clear recommendations, implementation guidance.

### Visual Elements:
- If include_visuals is true: Include ASCII tables, comparison charts, and structured lists.
- If include_visuals is false: Focus on prose, minimize tables and visual elements.

### Focus Areas:
- If focus_areas are specified, emphasize those aspects in the report.
- Allocate more space and detail to the specified focus areas.

## Report Structure

Generate a complete markdown research report with the following sections:

### 1. Title and Metadata
The title MUST reflect the actual research topic from the intent above.
```markdown
# [Actual Research Topic from Intent]: Research Report

**Generated:** [Current date and time]
**Research Type:** [From intent - e.g., General Research, Comparison, Analysis]
**Domain:** [From intent - e.g., Technology, Finance, Health]
**Report Format:** [From output_preferences - length/audience/style]
**Research Confidence:** [Based on data quality]

---
```

### 2. Executive Summary
Word count based on report_length:
- brief: 100-150 words
- standard: 200-300 words
- comprehensive: 300-500 words

Include:
- State the research objective clearly (from the intent)
- Highlight the most important findings (3-5 key points)
- Mention key conclusions or insights
- Note any significant limitations

### 3. Key Findings
Adjust based on report_length:
- brief: 3-5 bullet points
- standard: 5-8 bullet points
- comprehensive: 8-12 bullet points with sub-points

Include:
- Specific data points and statistics where available
- Group related findings logically
- Use clear, factual language
- Include comparison tables if research involved comparisons AND include_visuals is true

### 4. Detailed Analysis (skip for brief reports)
For each major theme or research question from the intent:
- **Theme/Question Title**
- Detailed explanation (adjust depth based on length preference)
- Supporting evidence and data
- Multiple perspectives when available
- Source citations (more detailed for academic style)
- Acknowledgment of uncertainties

### 5. Contradictory Viewpoints (skip for brief reports)
- Present each contradictory viewpoint fairly
- Explain the source of each viewpoint
- Assess reliability of conflicting sources
- Provide context for why conflicts might exist

### 6. Recommendations (especially for practical style)
- Actionable next steps
- Implementation considerations
- Risk factors to consider

### 7. Sources and References
- List all sources used in the research
- Include URLs, titles, and access dates where available
- For academic style: use proper citation format
- For other styles: simple source list is sufficient

## Writing Guidelines
- Adapt tone based on audience (general=accessible, professional=business, technical=expert)
- Be objective and balanced
- Use proper markdown formatting (headers, bullet points, tables, bold, italic)
- Include markdown tables for comparisons (if include_visuals is true)
- Cite sources inline where appropriate
- Distinguish between facts and interpretations
- Acknowledge uncertainty where it exists

## Output Format
Output the complete markdown report as plain text. Do NOT wrap it in code blocks.
Start directly with the `#` title header.
The title MUST match the research topic from the intent_result above.
"""


report_generator_agent = LlmAgent(
    name="ReportGeneratorAgent",
    model=GEMINI_MODEL,
    description="Generates comprehensive markdown research reports from analyzed data.",
    # String, not function - enables state injection
    instruction=REPORT_GENERATOR_INSTRUCTION,
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
