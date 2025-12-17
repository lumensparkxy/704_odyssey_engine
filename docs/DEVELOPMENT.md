````markdown
# Odyssey Engine - Development Guide

## Quick Start

### 1. Setup
```bash
git clone <repository-url> odyssey-engine
cd odyssey-engine
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt  # or: pip install -e .[dev]
cp .env.example .env
```

Optional: editable install enables script entry point (`odyssey`).

### 2. Configuration
Minimal required value:
```
GEMINI_API_KEY=your_gemini_api_key_here
```
Common optional tuning:
```
CONFIDENCE_THRESHOLD=75
MAX_SCRAPING_DEPTH=3
MAX_SEARCH_RESULTS=10
MAX_FOLLOW_UP_QUESTIONS=5
REQUEST_TIMEOUT=30
```
Placeholders not yet wired: `CACHE_PATH`, `LOG_LEVEL`.

### 3. Run
```bash
python main.py                       # interactive
python main.py --query "Your research question"  # one-shot
python main.py --session <session_id>            # continue
python scripts/simple_research.py     # minimal scripted
python scripts/new_research.py        # advanced scripted
python examples/programmatic_usage.py # programmatic sample
```

## Architecture Overview

```
Odyssey Engine Pipeline:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  User Query     │ -> │ Intent Analysis  │ -> │ Data Gathering  │ -> │ Report Generate │
│                 │    │                  │    │                 │    │                 │
│ - Initial Q     │    │ - Clarification  │    │ - Multi-source  │    │ - Markdown      │
│ - Context       │    │ - Confidence     │    │ - Web scraping  │    │ - Structured    │
│ - Follow-ups    │    │ - Research plan  │    │ - Analysis      │    │ - Bibliography  │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
                                    |                        |                        |
                               ┌────v────┐            ┌─────v─────┐          ┌──────v──────┐
                               │Session  │            │Confidence │          │   Storage   │
                               │Storage  │            │Scoring    │          │& Retrieval  │
                               └─────────┘            └───────────┘          └─────────────┘
```

## Core Components

### 1. Research Engine (`src/core/engine.py`)
Main orchestrator that coordinates the entire research pipeline.

**Key Methods:**
- `start_research_session()`: Initialize new session
- `conduct_research()`: Execute full research pipeline
- `load_session()`: Resume existing session

### 2. Intent Analyzer (`src/core/intent_analyzer.py`)
Understands user intent and generates clarifying questions.

**Process:**
1. Analyze query complexity and clarity
2. Identify missing information
3. Generate targeted follow-up questions
4. Calculate confidence in understanding

### 3. Data Gatherer (`src/core/data_gatherer.py`)
Collects information from multiple sources with priority ordering.

**Source Priority:**
1. Internal Knowledge (Gemini training data)
2. Google Search (via Gemini grounding)
3. Provided Documents
4. Web Scraping (up to 3 levels deep)

### 4. Report Generator (`src/core/report_generator.py`)
Creates comprehensive markdown reports with structured sections.

**Report Structure:**
- Executive Summary
- Key Findings
- Detailed Analysis (by question/theme)
- Contradictory Viewpoints
- Bibliography/Sources

### 5. Confidence Scorer (`src/utils/confidence.py`)
Scores each stage + aggregate weighted result with recommendations.

### 6. Gemini Client (`src/utils/gemini_client.py`)
Wraps generate + grounded search. Handles fallback when grounding fails.

## Testing

### Unit Tests
```bash
pytest -m "not integration"            # fast unit tests (mocks)
pytest -m integration -s               # real API (cost/time)
pytest --cov=src --cov-report=term-missing
```

Markers declared in `pyproject.toml`. Avoid running integration in CI without secrets.

---
Maintainers: Update this guide when adding configuration flags, changing session schema, or introducing new pipeline stages.

````
