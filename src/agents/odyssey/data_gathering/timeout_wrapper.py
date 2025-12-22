"""
Timeout Wrapper for Data Gathering Agents.

Provides timeout protection and graceful fallback for ADK agents
to prevent the pipeline from hanging indefinitely.
"""

import os
import asyncio
import functools
from typing import Any, Dict, Optional
from datetime import datetime

# Timeout configuration (in seconds)
DEFAULT_AGENT_TIMEOUT = int(
    os.getenv("AGENT_TIMEOUT_SECONDS", "180"))  # 3 minutes per agent
GOOGLE_SEARCH_TIMEOUT = int(
    os.getenv("GOOGLE_SEARCH_TIMEOUT", "120"))  # 2 minutes for search
# 2.5 minutes for scraping
WEB_SCRAPER_TIMEOUT = int(os.getenv("WEB_SCRAPER_TIMEOUT", "150"))
INTERNAL_KNOWLEDGE_TIMEOUT = int(
    os.getenv("INTERNAL_KNOWLEDGE_TIMEOUT", "120"))  # 2 minutes


class AgentTimeoutError(Exception):
    """Raised when an agent exceeds its timeout limit."""

    def __init__(self, agent_name: str, timeout_seconds: int, message: str = None):
        self.agent_name = agent_name
        self.timeout_seconds = timeout_seconds
        self.message = message or f"Agent '{agent_name}' timed out after {timeout_seconds} seconds"
        super().__init__(self.message)


class AgentExecutionError(Exception):
    """Raised when an agent fails during execution."""

    def __init__(self, agent_name: str, original_error: Exception):
        self.agent_name = agent_name
        self.original_error = original_error
        self.message = f"Agent '{agent_name}' failed: {str(original_error)}"
        super().__init__(self.message)


def create_fallback_result(
    agent_name: str,
    output_key: str,
    error: Exception,
    partial_data: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a fallback result when an agent fails or times out.

    This ensures the pipeline continues even when one source fails.
    """
    error_type = "timeout" if isinstance(error, AgentTimeoutError) else "error"
    error_msg = str(error)

    fallback_content = f"""### {agent_name} - Data Gathering Failed

**Status:** ⚠️ {error_type.upper()}
**Error:** {error_msg}
**Timestamp:** {datetime.now().isoformat()}

**Impact:**
This data source was unable to complete its task. The research pipeline will continue
with data from other sources. The final analysis will note this limitation.

**Partial Data Recovered:**
{partial_data if partial_data else "No partial data available."}

**Recommendations:**
- The analysis will proceed with available data from other sources
- Consider re-running the research if this data source was critical
- Check network connectivity if this persists
"""

    return {
        output_key: fallback_content,
        f"{output_key}_status": "failed",
        f"{output_key}_error": error_msg,
        f"{output_key}_error_type": error_type,
    }


def get_agent_timeout(agent_name: str) -> int:
    """Get the appropriate timeout for an agent based on its name."""
    timeouts = {
        "GoogleSearchAgent": GOOGLE_SEARCH_TIMEOUT,
        "WebScraperAgent": WEB_SCRAPER_TIMEOUT,
        "InternalKnowledgeAgent": INTERNAL_KNOWLEDGE_TIMEOUT,
    }
    return timeouts.get(agent_name, DEFAULT_AGENT_TIMEOUT)


# Error tracking for the consolidator
class DataGatheringStatus:
    """Tracks the status of all data gathering agents."""

    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.start_time = datetime.now()

    def record_success(self, agent_name: str, output_key: str):
        """Record a successful agent execution."""
        self.results[agent_name] = {
            "status": "success",
            "output_key": output_key,
            "completed_at": datetime.now().isoformat(),
            "error": None
        }

    def record_failure(self, agent_name: str, output_key: str, error: Exception):
        """Record a failed agent execution."""
        self.results[agent_name] = {
            "status": "failed",
            "output_key": output_key,
            "completed_at": datetime.now().isoformat(),
            "error": str(error),
            "error_type": type(error).__name__
        }

    def get_summary(self) -> str:
        """Get a summary of data gathering status for the consolidator."""
        successful = [name for name, info in self.results.items()
                      if info["status"] == "success"]
        failed = [name for name, info in self.results.items()
                  if info["status"] == "failed"]

        summary = "### Data Gathering Status Summary\n\n"
        summary += f"**Total agents:** {len(self.results)}\n"
        summary += f"**Successful:** {len(successful)}\n"
        summary += f"**Failed:** {len(failed)}\n\n"

        if successful:
            summary += "**✅ Successful Sources:**\n"
            for name in successful:
                summary += f"- {name}\n"

        if failed:
            summary += "\n**⚠️ Failed Sources:**\n"
            for name in failed:
                error = self.results[name].get("error", "Unknown error")
                summary += f"- {name}: {error}\n"

        return summary

    def all_failed(self) -> bool:
        """Check if all agents failed."""
        if not self.results:
            return True
        return all(info["status"] == "failed" for info in self.results.values())

    def any_succeeded(self) -> bool:
        """Check if at least one agent succeeded."""
        return any(info["status"] == "success" for info in self.results.values())


# Global status tracker (reset per pipeline run)
_current_status: Optional[DataGatheringStatus] = None


def get_or_create_status() -> DataGatheringStatus:
    """Get or create the current data gathering status tracker."""
    global _current_status
    if _current_status is None:
        _current_status = DataGatheringStatus()
    return _current_status


def reset_status():
    """Reset the status tracker for a new pipeline run."""
    global _current_status
    _current_status = DataGatheringStatus()


def get_status_summary() -> str:
    """Get the current status summary."""
    status = get_or_create_status()
    return status.get_summary()
