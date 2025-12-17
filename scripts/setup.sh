#!/bin/bash

# Odyssey Engine Setup Script

set -euo pipefail

echo "🔍 Setting up Odyssey Engine - Deep Research AI"
echo "================================================"

# Prefer the repository's standard venv location: .venv
VENV_DIR=".venv"

# Check if Python 3.8+ is installed
if ! python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "❌ Error: Python 3.8 or higher is required"
    echo "Current version: $(python --version)"
    exit 1
fi

echo "✅ Python version check passed: $(python --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "${VENV_DIR}" ]; then
    echo "📦 Creating virtual environment in ${VENV_DIR}..."
    python -m venv "${VENV_DIR}"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source "${VENV_DIR}/bin/activate"

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    cp .env.example .env
    echo ""
    echo "🔑 IMPORTANT: Please edit .env file and add your Gemini API key:"
    echo "   GEMINI_API_KEY=your_api_key_here"
    echo ""
    echo "You can get a Gemini API key from: https://ai.google.dev/"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p sessions reports logs cache

# Set executable permissions on main.py
chmod +x main.py

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your Gemini API key"
echo "2. Run: python main.py"
echo "3. Or activate venv and run: source ${VENV_DIR}/bin/activate && python main.py"
echo ""
echo "For help: python main.py --help"
