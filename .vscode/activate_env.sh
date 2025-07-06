#!/bin/zsh
# Auto-activate virtual environment script for Odyssey Engine
# This script is sourced automatically when opening terminals in VS Code

# Check if we're already in the virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment already active: $(basename $VIRTUAL_ENV)"
else
    # Check if .venv directory exists
    if [[ -d ".venv" ]]; then
        echo "🐍 Activating Odyssey Engine virtual environment..."
        source .venv/bin/activate
        echo "✅ Virtual environment activated: $(basename $VIRTUAL_ENV)"
        echo "📦 Python version: $(python --version)"
        echo "📍 Project root: $(pwd)"
        echo ""
        echo "🚀 Available commands:"
        echo "  - odyssey: Run the Odyssey Engine CLI"
        echo "  - python main.py: Run the main application"
        echo "  - pytest: Run tests"
        echo "  - pip list: Show installed packages"
        echo ""
    else
        echo "❌ Virtual environment not found. Run 'python -m venv .venv' to create it."
    fi
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
