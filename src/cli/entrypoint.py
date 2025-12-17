"""Odyssey Engine CLI entrypoint.

This module exists so we can expose a stable console script entrypoint
(e.g. via Poetry: `odyssey = "cli.entrypoint:main"`).

It intentionally mirrors `main.py` but lives inside the importable package.
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from cli.interface import OdysseyCLI


def main() -> None:
    """Run the interactive CLI."""
    load_dotenv()
    cli = OdysseyCLI()
    asyncio.run(cli.run())
