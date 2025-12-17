"""
Parallel Data Gathering Agent.

Orchestrates concurrent data gathering from multiple sources using ParallelAgent.
"""

import os
from google.adk.agents import ParallelAgent, SequentialAgent

from .internal_knowledge import internal_knowledge_agent
from .google_search import google_search_agent
from .web_scraper_agent import web_scraper_agent
from .consolidator import consolidator_agent


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
