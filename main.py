#!/usr/bin/env python3
"""
Odyssey Engine - Deep Research AI
Main entry point for the command-line interface.

Uses Google ADK multi-agent pipeline for comprehensive research.
"""

from dotenv import load_dotenv
import asyncio
from pathlib import Path
import sys

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    """Main entry point for the Odyssey Engine."""
    # Load environment variables
    load_dotenv()

    print("🚀 Starting Odyssey Engine with ADK agents...")

    from cli.adk_interface import OdysseyADKCLI
    cli = OdysseyADKCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
