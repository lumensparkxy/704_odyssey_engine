#!/usr/bin/env python3
"""
Odyssey Engine - Deep Research Engine
Main entry point for the command-line interface.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cli.interface import OdysseyCLI
from dotenv import load_dotenv

def main():
    """Main entry point for the Odyssey Engine."""
    # Load environment variables
    load_dotenv()
    
    # Initialize and run CLI
    cli = OdysseyCLI()
    asyncio.run(cli.run())

if __name__ == "__main__":
    main()
