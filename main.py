#!/usr/bin/env python3
"""
Odyssey Engine - Deep Research Engine
Main entry point for the command-line interface.

Supports both legacy engine (src/core/) and ADK-based agents (src/agents/).
Set USE_ADK=true in environment or config to use ADK pipeline.
"""

from dotenv import load_dotenv
import os
import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def _use_adk() -> bool:
    """Check if ADK mode is enabled via environment or config."""
    # Check environment variable first
    env_value = os.getenv("USE_ADK", "").lower()
    if env_value in ("true", "1", "yes"):
        return True
    if env_value in ("false", "0", "no"):
        return False

    # Fall back to config file
    config_path = Path(__file__).parent / "config" / "default.conf"
    if config_path.exists():
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(config_path)
            return config.getboolean("adk", "use_adk", fallback=False)
        except Exception:
            pass

    return False


def main():
    """Main entry point for the Odyssey Engine."""
    # Load environment variables
    load_dotenv()

    if _use_adk():
        # Use ADK-based agent pipeline
        print("🚀 Starting Odyssey Engine with ADK agents...")
        print("   Run 'adk web --port 8000' from src/agents/ for web UI")
        print("   Or 'adk run src/agents' for CLI mode")

        # For now, provide instructions - full ADK CLI integration in Phase 4
        from agents import root_agent
        print(f"\n✅ ADK root_agent loaded: {root_agent.name}")
        print("   Use 'adk run' or 'adk web' commands to interact with the agent.")
    else:
        # Use legacy engine
        from cli.interface import OdysseyCLI
        cli = OdysseyCLI()
        asyncio.run(cli.run())


if __name__ == "__main__":
    main()
