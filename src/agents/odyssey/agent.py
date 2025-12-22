"""
Odyssey Engine - ADK Root Agent Definition.

This is the main agent orchestrating the research pipeline using Google ADK.
Phase 1: Intent Analysis + Analysis (SequentialAgent)
Phase 2: Parallel Data Gathering (ParallelAgent)
Phase 3: Report Generation (SequentialAgent)
"""

import os
from google.adk.agents import SequentialAgent

from .intent import intent_clarification_loop
from .data_gathering import data_gathering_pipeline
from .analysis import analysis_agent
from .report import report_generation_pipeline

# Configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


# Phase 3: Full pipeline with Intent + Data Gathering + Analysis + Report Generation
root_agent = SequentialAgent(
    name="OdysseyResearchPipeline",
    description="""Deep research engine that conducts comprehensive research through multiple stages:
    1. Intent Analysis - Understand what the user wants to research (with clarification loop)
    2. Data Gathering - Parallel collection from internal knowledge, Google Search, and web scraping
    3. Analysis - Identify themes, conflicts, and synthesize findings
    4. Report Generation - Generate and save comprehensive markdown research reports
    """,
    sub_agents=[
        intent_clarification_loop,  # Phase 1: Intent with clarification loop
        data_gathering_pipeline,    # Phase 2: Parallel data gathering + consolidation
        analysis_agent,             # Phase 1: Analysis and synthesis
        report_generation_pipeline,  # Phase 3: Report generation and file saving
    ],
)
