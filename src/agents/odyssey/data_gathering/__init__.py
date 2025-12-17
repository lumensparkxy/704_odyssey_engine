"""
Data Gathering Agents Package.

Phase 2: ParallelAgent with multiple data sources.
"""

from .parallel_gatherer import data_gathering_pipeline
from .internal_knowledge import internal_knowledge_agent
from .google_search import google_search_agent
from .web_scraper_agent import web_scraper_agent
from .consolidator import consolidator_agent

__all__ = [
    "data_gathering_pipeline",
    "internal_knowledge_agent",
    "google_search_agent",
    "web_scraper_agent",
    "consolidator_agent",
]
