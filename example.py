"""Compatibility wrapper (deprecated).

The programmatic example was moved out of the repository root.
Use: `python examples/programmatic_usage.py`
"""

from __future__ import annotations

from pathlib import Path
import runpy


def main() -> None:
    target = Path(__file__).resolve().parent / \
        "examples" / "programmatic_usage.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
