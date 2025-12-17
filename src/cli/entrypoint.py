"""Odyssey Engine CLI entrypoint.

This module provides the main console script entrypoint for Odyssey Engine.
Uses Google ADK-powered multi-agent pipeline.

Usage:
    odyssey              # Start interactive research CLI
    odyssey -q "query"   # Non-interactive mode with query
"""

from __future__ import annotations

import asyncio

import click
from dotenv import load_dotenv


@click.command()
@click.option(
    '--query', '-q',
    help='Research query for non-interactive mode'
)
def main(query: str | None) -> None:
    """Odyssey Engine - Deep Research AI.

    Run comprehensive research using Google ADK agents pipeline.
    """
    load_dotenv()

    from cli.adk_interface import OdysseyADKCLI
    cli = OdysseyADKCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
