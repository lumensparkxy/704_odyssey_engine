# Odyssey Engine - Deep Research AI

AI-powered research pipeline built on **Google ADK (Agent Development Kit)** that transforms natural language queries into comprehensive, structured markdown reports.

## Overview

Odyssey Engine uses a multi-agent architecture to conduct thorough research:

1. **Intent Analysis** → Understand and clarify research objectives
2. **Data Gathering** → Parallel collection from multiple sources
3. **Analysis** → Theme identification, conflict detection, synthesis
4. **Report Generation** → Structured markdown with citations

## Architecture

```
OdysseyResearchPipeline (SequentialAgent)
├── IntentClarificationLoop (LoopAgent)
│   ├── IntentAnalysisAgent (LlmAgent)
│   └── ConfidenceCheckerAgent (LlmAgent)
├── DataGatheringPipeline (SequentialAgent)
│   ├── ParallelDataGatherer (ParallelAgent)
│   │   ├── InternalKnowledgeAgent (LlmAgent)
│   │   ├── GoogleSearchAgent (LlmAgent) + google_search
│   │   └── WebScraperAgent (LlmAgent) + url_context
│   └── ConsolidatorAgent (LlmAgent)
├── AnalysisAgent (LlmAgent)
└── ReportGenerationPipeline (SequentialAgent)
    ├── ReportWriterAgent (LlmAgent)
    └── ReportSaverAgent (LlmAgent) + save_report_to_file
```

### Key Features

- **Multi-Agent Pipeline**: Specialized agents for each research phase
- **Built-in Tools**: Uses ADK's `google_search` and `url_context` for web research
- **Parallel Data Gathering**: Concurrent collection from knowledge, search, and URLs
- **Confidence Scoring**: Validates research quality at each stage
- **Rich CLI**: Interactive terminal interface with progress tracking
- **Structured Reports**: Markdown output with executive summary, findings, and citations

## Installation

### Prerequisites
- Python 3.10+
- Google Gemini API key

### Setup

```bash
# Clone repository
git clone <repository-url> odyssey-engine
cd odyssey-engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

## Quick Start

```bash
# Interactive mode
python main.py

# With query
python -m src.cli.entrypoint -q "Compare React vs Vue for enterprise apps"
```

Reports are saved to `reports/` directory.

## Project Structure

```
odyssey-engine/
├── src/
│   ├── agents/odyssey/           # ADK Agent Definitions
│   │   ├── agent.py              # Root pipeline
│   │   ├── intent/               # Intent analysis agents
│   │   ├── data_gathering/       # Parallel data gathering
│   │   ├── analysis/             # Analysis agent
│   │   ├── report/               # Report generation
│   │   └── tools/                # Custom tools (confidence, file_writer)
│   └── cli/
│       ├── adk_interface.py      # Rich terminal interface
│       └── entrypoint.py         # CLI entry point
├── tests/                        # Test suite (93 tests)
├── reports/                      # Generated reports
├── main.py                       # Application entry point
└── pyproject.toml                # Project configuration
```

## Configuration

Environment variables (`.env`):

| Variable | Purpose | Default |
|----------|---------|---------|
| `GEMINI_API_KEY` | Gemini API authentication | (required) |
| `GEMINI_MODEL` | Model name | `gemini-3-flash-preview` |
| `REPORTS_OUTPUT_PATH` | Report output directory | `./reports` |

## Usage Examples

### Interactive Research Session
```bash
python main.py
```
Follow the prompts to enter your research query and watch the pipeline execute.

### Direct Query
```bash
python -m src.cli.entrypoint -q "What are the latest developments in quantum computing?"
```

### Programmatic Usage
```python
import asyncio
from src.cli.adk_interface import OdysseyADKCLI

async def main():
    cli = OdysseyADKCLI()
    await cli.run()

asyncio.run(main())
```

## Development

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_adk_phase1.py -v
```

### Code Quality
```bash
# Format code
black src/

# Sort imports
isort src/

# Type checking
mypy src/
```

## How It Works

1. **Intent Clarification**: The `IntentClarificationLoop` analyzes your query, extracting research type, domain, and specific questions. A confidence checker ensures the intent is clear before proceeding.

2. **Data Gathering**: Three agents work in parallel:
   - `InternalKnowledgeAgent`: Leverages model's training knowledge
   - `GoogleSearchAgent`: Performs grounded web searches
   - `WebScraperAgent`: Extracts content from relevant URLs using `url_context`

3. **Consolidation**: The `ConsolidatorAgent` merges findings from all sources, deduplicates information, and assesses source reliability.

4. **Analysis**: The `AnalysisAgent` identifies themes, detects conflicts, and synthesizes insights.

5. **Report Generation**: The `ReportWriterAgent` creates a structured markdown report, and `ReportSaverAgent` persists it to disk.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing API key | Ensure `GEMINI_API_KEY` is set in `.env` |
| Import errors | Run from project root with `python -m src.cli.entrypoint` |
| Slow responses | Normal for comprehensive research; Gemini processes take time |

## License

MIT License - see [LICENSE](LICENSE)

---
*Odyssey Engine v2.0 - Powered by Google ADK*
