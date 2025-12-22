"""
Parallel Data Gathering Agent.

Orchestrates concurrent data gathering from multiple sources using ParallelAgent.

NOTE: Timeout handling is implemented at the CLI runner level (adk_interface.py)
to wrap the entire data gathering phase. Individual agent timeouts are configured
via environment variables:
- GOOGLE_SEARCH_TIMEOUT (default: 120s)
- WEB_SCRAPER_TIMEOUT (default: 150s) 
- INTERNAL_KNOWLEDGE_TIMEOUT (default: 120s)
- DATA_GATHERING_TOTAL_TIMEOUT (default: 300s / 5 minutes)

If any agent times out, the consolidator will work with partial data.
"""

import os
from google.adk.agents import ParallelAgent, SequentialAgent

from .internal_knowledge import internal_knowledge_agent
from .google_search import google_search_agent
from .web_scraper_agent import web_scraper_agent
from .consolidator import consolidator_agent

# Total timeout for all data gathering (used by CLI runner)
DATA_GATHERING_TOTAL_TIMEOUT = int(
    os.getenv("DATA_GATHERING_TOTAL_TIMEOUT", "300"))  # 5 minutes


# ParallelAgent for concurrent data gathering
# Each sub-agent writes to its own output_key in session state
parallel_data_gatherer = ParallelAgent(
    name="ParallelDataGatherer",
    description="""Gathers data concurrently from multiple sources:
    - Internal Knowledge (Gemini's training data)
    - Google Search (current web information)
    - Web Scraping (detailed content from URLs)
    
    Results are stored in session state for consolidation.
    """,
    sub_agents=[
        internal_knowledge_agent,  # output_key: internal_knowledge_result
        google_search_agent,       # output_key: google_search_result
        web_scraper_agent,         # output_key: web_scraping_result
    ],
)

# Full data gathering pipeline:
# 1. Parallel gathering from all sources
# 2. Consolidation into unified format
data_gathering_pipeline = SequentialAgent(
    name="DataGatheringPipeline",
    description="""Complete data gathering pipeline that:
    1. Gathers data in parallel from internal knowledge, Google Search, and web scraping
    2. Consolidates all sources into a unified data structure
    
    Input: intent_result from session state
    Output: consolidated_data in session state
    """,
    sub_agents=[
        parallel_data_gatherer,  # Run all gatherers concurrently
        consolidator_agent,      # Consolidate results
    ],
)
