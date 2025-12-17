"""Odyssey Engine CLI entrypoint.

This module provides the main console script entrypoint for Odyssey Engine.
Supports both legacy mode and ADK-powered mode.

Usage:
    odyssey              # Default: Uses ADK mode
    odyssey --legacy     # Use legacy (non-ADK) mode
    odyssey --adk        # Explicitly use ADK mode
"""

from __future__ import annotations

import asyncio
import sys

import click
from dotenv import load_dotenv


@click.command()
@click.option(
    '--adk/--legacy',
    default=True,
    help='Use ADK-powered pipeline (default) or legacy mode'
)
@click.option(
    '--query', '-q',
    help='Research query for non-interactive mode'
)
def main(adk: bool, query: str | None) -> None:
    """Odyssey Engine - Deep Research AI.

    Run comprehensive research using Google ADK agents pipeline.
    """
    load_dotenv()

    if adk:
        # ADK mode (default)
        from cli.adk_interface import OdysseyADKCLI
        cli = OdysseyADKCLI()
        asyncio.run(cli.run())
    else:
        # Legacy mode
        from cli.interface import OdysseyCLI
        cli = OdysseyCLI()
        asyncio.run(cli.run())


if __name__ == "__main__":
    main()
