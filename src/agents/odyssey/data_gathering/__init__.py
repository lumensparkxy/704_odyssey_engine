"""
Data Gathering Agents Package.

Phase 2: ParallelAgent with multiple data sources.

Includes timeout protection to prevent hangs:
- DATA_GATHERING_TOTAL_TIMEOUT: 5 minutes (default)
- GOOGLE_SEARCH_TIMEOUT: 2 minutes (default)
- WEB_SCRAPER_TIMEOUT: 2.5 minutes (default)
- INTERNAL_KNOWLEDGE_TIMEOUT: 2 minutes (default)

Set via environment variables to customize.
"""

from .parallel_gatherer import data_gathering_pipeline, DATA_GATHERING_TOTAL_TIMEOUT
from .internal_knowledge import internal_knowledge_agent
from .google_search import google_search_agent
from .web_scraper_agent import web_scraper_agent
from .consolidator import consolidator_agent

__all__ = [
    "data_gathering_pipeline",
    "DATA_GATHERING_TOTAL_TIMEOUT",
    "internal_knowledge_agent",
    "google_search_agent",
    "web_scraper_agent",
    "consolidator_agent",
]
