"""
Playful progress messages for Odyssey Engine CLI.

This module contains rotating messages displayed during each research phase
to make the wait time more engaging and fun.
"""

from typing import Dict, List
import random

# =============================================================================
# PHASE MESSAGES - Rotating messages shown during each pipeline phase
# =============================================================================

PHASE_MESSAGES: Dict[str, List[str]] = {
    # Intent Analysis Phase
    "IntentAnalysis": [
        "Decoding your research quest... 🔮",
        "Reading between the lines... 📖",
        "Understanding what you're really after... 🧠",
        "Parsing the mysteries of your query... 🕵️",
        "Tuning into your wavelength... 📡",
    ],

    # Confidence Check
    "ConfidenceCheck": [
        "Double-checking our understanding... ✅",
        "Making sure we're on the same page... 📋",
        "Running a sanity check... 🎯",
        "Validating our interpretation... 🔍",
    ],

    # Data Gathering Phase (main phase - longest)
    "DataGathering": [
        "Hunting down the good stuff... 🕵️",
        "Scouring the interwebs... 🌐",
        "Digging through mountains of data... ⛏️",
        "Following the digital breadcrumbs... 🍞",
        "Unleashing the research hounds... 🐕",
        "Diving into the knowledge ocean... 🤿",
        "Leaving no stone unturned... 🪨",
        "On the trail of insights... 🔦",
    ],

    # Google Search specific
    "GoogleSearch": [
        "Asking the Google oracle... 🔮",
        "Summoning search results... ✨",
        "Querying the knowledge gods... ⚡",
        "Casting a wide net... 🎣",
        "Sending out search probes... 📡",
    ],

    # Web Scraping specific
    "WebScraper": [
        "Extracting the juicy bits... 🍊",
        "Reading the fine print... 📰",
        "Gathering web treasures... 💎",
        "Slurping up content... 🍜",
        "Mining digital gold... ⛏️",
    ],

    # Internal Knowledge
    "InternalKnowledge": [
        "Consulting the ancient scrolls... 📜",
        "Tapping into the knowledge vault... 🏛️",
        "Channeling inner wisdom... 🧘",
        "Searching the memory banks... 💾",
        "Accessing deep knowledge... 🧠",
    ],

    # Consolidation
    "Consolidator": [
        "Piecing the puzzle together... 🧩",
        "Connecting the dots... 🔗",
        "Merging streams of knowledge... 🌊",
        "Synthesizing findings... ⚗️",
        "Building the big picture... 🖼️",
    ],

    # Analysis Phase
    "Analysis": [
        "Crunching the numbers... 🔢",
        "Analyzing patterns... 📊",
        "Finding the signal in the noise... 📶",
        "Extracting insights... 💡",
        "Thinking deeply... 🤔",
        "Weighing the evidence... ⚖️",
        "Drawing conclusions... 📝",
    ],

    # Report Generation Phase
    "ReportGeneration": [
        "Crafting your report... ✍️",
        "Polishing the prose... ✨",
        "Weaving the narrative... 🧵",
        "Putting pen to paper... 🖊️",
        "Assembling the masterpiece... 🎨",
        "Making it look pretty... 💅",
    ],

    # Report Saving
    "ReportSaver": [
        "Saving your findings... 💾",
        "Preserving the knowledge... 📁",
        "Filing away the goods... 🗄️",
    ],
}

# =============================================================================
# TOOL ACTIVITY MESSAGES - Reactions when tools are invoked
# =============================================================================

TOOL_DISCOVERY_MESSAGES: List[str] = [
    "Found something interesting! 👀",
    "Ooh, this looks promising... 🎯",
    "Jackpot! Let me dig into this... 💰",
    "Now we're getting somewhere... 🚀",
    "This could be useful... 📌",
    "Spotted a lead! 🔍",
]

TOOL_COMPLETION_MESSAGES: List[str] = [
    "Got it! ✓",
    "Captured! 📸",
    "Locked and loaded! 🔒",
    "In the bag! 👜",
    "Snagged it! 🎣",
]

# =============================================================================
# TIMEOUT AND ERROR MESSAGES - Displayed when things go wrong
# =============================================================================

TIMEOUT_MESSAGES: Dict[str, List[str]] = {
    "DataGathering": [
        "⏰ Taking longer than expected, wrapping up with what we have...",
        "⚠️ Time's running short, finalizing data collection...",
        "🏃 Running out of time, consolidating available data...",
    ],
    "Analysis": [
        "⏰ Analysis is taking a while, finishing up...",
        "⚠️ Time limit approaching, completing analysis...",
    ],
    "ReportGeneration": [
        "⏰ Report generation running long, wrapping up...",
        "⚠️ Finalizing report with available content...",
    ],
}

GRACEFUL_FAILURE_MESSAGES: List[str] = [
    "One source couldn't complete, but we'll make do! 💪",
    "Not all sources responded, continuing with what we have...",
    "Some data sources timed out, but the show goes on! 🎭",
    "Partial data collected - still enough to work with! ✨",
]

# =============================================================================
# PHASE HEADERS - Displayed when entering a new phase
# =============================================================================

PHASE_HEADERS: Dict[str, str] = {
    "IntentAnalysis": "🎯 Phase 1: Understanding Your Query",
    "DataGathering": "🔍 Phase 2: Gathering Intelligence",
    "Analysis": "🧠 Phase 3: Deep Analysis",
    "ReportGeneration": "📝 Phase 4: Crafting Your Report",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_phase_message(phase: str, index: int = None) -> str:
    """
    Get a message for the given phase.

    Args:
        phase: The phase name (e.g., "DataGathering", "Analysis")
        index: Optional specific index, otherwise picks randomly

    Returns:
        A playful message string
    """
    messages = PHASE_MESSAGES.get(phase, PHASE_MESSAGES.get("DataGathering"))
    if index is not None:
        return messages[index % len(messages)]
    return random.choice(messages)


def get_rotating_message(phase: str, rotation_index: int) -> str:
    """
    Get a message based on rotation index (for sequential cycling).

    Args:
        phase: The phase name
        rotation_index: Current rotation count

    Returns:
        A message that cycles through the list sequentially
    """
    messages = PHASE_MESSAGES.get(phase, PHASE_MESSAGES.get("DataGathering"))
    return messages[rotation_index % len(messages)]


def get_tool_discovery_message() -> str:
    """Get a random reaction message when a tool finds something."""
    return random.choice(TOOL_DISCOVERY_MESSAGES)


def get_tool_completion_message() -> str:
    """Get a random message when a tool completes."""
    return random.choice(TOOL_COMPLETION_MESSAGES)


def get_phase_header(phase: str) -> str:
    """Get the header text for a phase."""
    return PHASE_HEADERS.get(phase, f"📋 {phase}")
