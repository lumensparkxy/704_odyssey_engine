#!/usr/bin/env python3
"""Compatibility wrapper (deprecated).

The direct scripts were moved out of the repository root to reduce clutter.
Use: `python scripts/new_research.py`
"""

from __future__ import annotations

from pathlib import Path
import runpy


def main() -> None:
    target = Path(__file__).resolve().parent / "scripts" / "new_research.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
