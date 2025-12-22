"""
Live progress display components for Odyssey Engine CLI.

This module provides animated progress tracking with Rich's Live display,
showing elapsed time, current activity, and rotating playful messages.
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from rich.table import Table

from .messages import (
    get_rotating_message,
    get_tool_discovery_message,
    get_phase_header,
    PHASE_MESSAGES,
)


@dataclass
class ToolActivity:
    """Represents a tool invocation for display."""
    tool_name: str
    description: str  # e.g., the search query or URL
    timestamp: float = field(default_factory=time.time)

    def format_display(self) -> str:
        """Format for display in the progress panel."""
        if self.tool_name == "google_search":
            return f'🔍 Searching: "{self.description}"'
        elif self.tool_name == "url_context":
            # Truncate long URLs
            url = self.description
            if len(url) > 60:
                url = url[:57] + "..."
            return f"📄 Fetching: {url}"
        else:
            return f"🔧 {self.tool_name}: {self.description}"


class ProgressTracker:
    """
    Tracks progress state for a research phase.

    Maintains current phase, elapsed time, tool activities,
    and message rotation index for animated display.
    """

    def __init__(self, phase: str, timeout_seconds: int = None):
        """
        Initialize tracker for a specific phase.

        Args:
            phase: The phase name (e.g., "DataGathering", "Analysis")
            timeout_seconds: Optional timeout limit for the phase
        """
        self.phase = phase
        self.start_time = time.time()
        self.message_rotation_index = 0
        self.last_rotation_time = time.time()
        self.rotation_interval = 3.0  # Rotate message every 3 seconds

        # Timeout tracking
        self.timeout_seconds = timeout_seconds
        self._elapsed_seconds = 0  # Allow external update

        # Tool activity tracking
        self.tool_activities: List[ToolActivity] = []
        self.max_activities_shown = 3  # Show last N tool activities

        # Sub-agent tracking
        self.current_sub_agent: Optional[str] = None

    @property
    def elapsed_seconds(self) -> int:
        """Get elapsed time in seconds."""
        if self._elapsed_seconds > 0:
            return int(self._elapsed_seconds)
        return int(time.time() - self.start_time)

    @elapsed_seconds.setter
    def elapsed_seconds(self, value: float):
        """Allow external update of elapsed time."""
        self._elapsed_seconds = value

    @property
    def elapsed_display(self) -> str:
        """Get formatted elapsed time string with optional timeout warning."""
        seconds = self.elapsed_seconds
        if seconds < 60:
            time_str = f"{seconds}s"
        else:
            minutes = seconds // 60
            secs = seconds % 60
            time_str = f"{minutes}m {secs}s"

        # Add timeout warning if applicable
        if self.timeout_seconds:
            remaining = self.timeout_seconds - seconds
            if remaining <= 0:
                return f"{time_str} [red](TIMEOUT)[/red]"
            elif remaining < 60:
                return f"{time_str} [yellow]({remaining}s left)[/yellow]"
            elif remaining < 120:
                return f"{time_str} [dim]({remaining // 60}m left)[/dim]"

        return time_str

    def should_rotate_message(self) -> bool:
        """Check if it's time to rotate to next message."""
        return (time.time() - self.last_rotation_time) >= self.rotation_interval

    def rotate_message(self) -> str:
        """Rotate to next message and return it."""
        if self.should_rotate_message():
            self.message_rotation_index += 1
            self.last_rotation_time = time.time()

        # Use sub-agent specific messages if available
        phase_key = self.current_sub_agent or self.phase
        return get_rotating_message(phase_key, self.message_rotation_index)

    def add_tool_activity(self, tool_name: str, description: str):
        """
        Record a tool invocation.

        Args:
            tool_name: Name of the tool (e.g., "google_search")
            description: Details (e.g., the search query)
        """
        activity = ToolActivity(tool_name=tool_name, description=description)
        self.tool_activities.append(activity)

        # Keep only recent activities
        if len(self.tool_activities) > 10:
            self.tool_activities = self.tool_activities[-10:]

    def set_sub_agent(self, agent_name: str):
        """
        Set the current sub-agent for message selection.

        Args:
            agent_name: Name like "GoogleSearchAgent", "WebScraperAgent"
        """
        # Map agent names to message keys
        agent_map = {
            "GoogleSearch": "GoogleSearch",
            "WebScraper": "WebScraper",
            "InternalKnowledge": "InternalKnowledge",
            "Consolidator": "Consolidator",
            "Analysis": "Analysis",
            "Report": "ReportGeneration",
        }

        for key, value in agent_map.items():
            if key in agent_name:
                self.current_sub_agent = value
                return

        # Reset to main phase if no match
        self.current_sub_agent = None

    def get_recent_activities(self) -> List[ToolActivity]:
        """Get the most recent tool activities for display."""
        return self.tool_activities[-self.max_activities_shown:]


class LiveProgressPanel:
    """
    Renders an animated progress panel using Rich.

    Displays:
    - Phase header with spinner
    - Elapsed time
    - Recent tool activities (search queries, URLs)
    - Rotating playful message
    """

    def __init__(self, tracker: ProgressTracker, console: Console = None):
        """
        Initialize the panel renderer.

        Args:
            tracker: The ProgressTracker instance
            console: Optional Rich console (creates new if not provided)
        """
        self.tracker = tracker
        self.console = console or Console()
        self.spinner = Spinner("dots", style="cyan")

    def render(self) -> Panel:
        """
        Render the current progress state as a Rich Panel.

        Returns:
            A Rich Panel ready for display in Live context
        """
        # Build content parts
        parts = []

        # Line 1: Status with spinner placeholder + elapsed time
        status_line = Text()
        status_line.append("● ", style="cyan bold")
        status_line.append(self.tracker.rotate_message())
        status_line.append(f"  ⏱️ {self.tracker.elapsed_display}", style="dim")
        parts.append(status_line)

        # Line 2+: Recent tool activities
        activities = self.tracker.get_recent_activities()
        if activities:
            parts.append(Text())  # Blank line
            for activity in activities:
                activity_text = Text()
                activity_text.append("  ")
                activity_text.append(
                    activity.format_display(), style="dim cyan")
                parts.append(activity_text)

        # Combine all parts
        content = Group(*parts)

        # Create panel with phase header
        header = get_phase_header(self.tracker.phase)
        panel = Panel(
            content,
            title=f"[bold]{header}[/bold]",
            title_align="left",
            border_style="blue",
            padding=(1, 2),
        )

        return panel

    def render_simple(self) -> Text:
        """
        Render a simpler single-line version for less important phases.

        Returns:
            A Rich Text object with spinner-style output
        """
        text = Text()
        text.append("● ", style="cyan bold")
        text.append(self.tracker.rotate_message())
        text.append(f"  ⏱️ {self.tracker.elapsed_display}", style="dim")
        return text


def extract_tool_info_from_event(event) -> Optional[Dict[str, Any]]:
    """
    Extract tool call information from an ADK event.

    Args:
        event: An ADK event object

    Returns:
        Dict with 'tool_name' and 'description' if found, else None
    """
    # Try to get function calls from event
    if hasattr(event, 'get_function_calls'):
        try:
            calls = event.get_function_calls()
            if calls:
                for call in calls:
                    tool_name = getattr(call, 'name', None)
                    args = getattr(call, 'args', {})

                    if tool_name == 'google_search':
                        query = args.get('query', str(args))
                        return {'tool_name': tool_name, 'description': query}

                    elif tool_name == 'url_context':
                        urls = args.get('urls', args)
                        if isinstance(urls, list) and urls:
                            return {'tool_name': tool_name, 'description': urls[0]}
                        elif isinstance(urls, str):
                            return {'tool_name': tool_name, 'description': urls}
        except Exception:
            pass  # Silent fallback

    # Fallback: check content for function call parts
    if hasattr(event, 'content') and event.content:
        content = event.content
        if hasattr(content, 'parts'):
            for part in content.parts:
                if hasattr(part, 'function_call'):
                    fc = part.function_call
                    tool_name = getattr(fc, 'name', None)
                    args = getattr(fc, 'args', {})

                    if tool_name == 'google_search':
                        query = args.get('query', str(args))
                        return {'tool_name': tool_name, 'description': query}

                    elif tool_name == 'url_context':
                        urls = args.get('urls', args)
                        if isinstance(urls, list) and urls:
                            return {'tool_name': tool_name, 'description': urls[0]}

    return None


def get_agent_from_event(event) -> Optional[str]:
    """
    Extract the agent name from an ADK event.

    Args:
        event: An ADK event object

    Returns:
        Agent name string if found, else None
    """
    if hasattr(event, 'author') and event.author:
        return event.author
    return None
