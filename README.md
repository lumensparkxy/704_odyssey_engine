# Odyssey Engine - Deep Research Engine

A Python-based command-line tool that provides in-depth answers to user queries by gathering information from various sources, analyzing it, and generating comprehensive reports.

## Overview

The Odyssey Engine is designed for curious minds who want to go deeper than obvious answers. It uses advanced AI (Gemini Pro 2.5) to conduct thorough research by:

- Understanding user intent through conversational interviews
- Gathering information from multiple sources (Google Search, web scraping, documents)
- Analyzing and compiling comprehensive reports
- Providing traceability and session storage

## Features

- **Multi-turn Conversational Interface**: Clarifies user intent through follow-up questions
- **Multiple Data Sources**: Google Search, web scraping, document analysis
- **Confidence Scoring**: LLM-based confidence assessment
- **Comprehensive Reports**: Markdown reports with executive summary, key findings, and citations
- **Session Storage**: JSON-based storage of all research sessions and intermediate steps
- **Web Scraping**: Intelligent link following up to 3 levels deep

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd odyssey-engine

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Gemini API key
```

## Quick Start

```bash
# Start a research session
python main.py

# Or with a direct query
python main.py --query "Compare the market share of EVs in Europe vs. North America for 2023"
```

## Project Structure

```
odyssey-engine/
├── src/
│   ├── core/
│   │   ├── engine.py          # Main research engine
│   │   ├── intent_analyzer.py # User intent analysis
│   │   ├── data_gatherer.py   # Information gathering
│   │   └── report_generator.py # Report generation
│   ├── utils/
│   │   ├── gemini_client.py   # Gemini API client
│   │   ├── web_scraper.py     # Web scraping utilities
│   │   ├── confidence.py      # Confidence scoring
│   │   └── storage.py         # Session storage
│   └── cli/
│       └── interface.py       # Command-line interface
├── sessions/                  # Stored research sessions
├── reports/                   # Generated reports
├── tests/                     # Unit tests
├── config/                    # Configuration files
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
└── .env.example              # Environment variables template
```

## Configuration

Set the following environment variables in `.env`:

```
GEMINI_API_KEY=your_gemini_api_key_here
CONFIDENCE_THRESHOLD=75
MAX_SCRAPING_DEPTH=3
SESSION_STORAGE_PATH=./sessions
REPORTS_OUTPUT_PATH=./reports
```

## Usage Examples

### Basic Research Query
```bash
python main.py --query "What are the latest developments in quantum computing?"
```

### Interactive Mode
```bash
python main.py --interactive
```

### Load Previous Session
```bash
python main.py --session session_id_12345
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Quality
```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
pylint src/
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions, please open an issue on the GitHub repository.
