# Odyssey Engine - Deep Research Engine

AI-powered asynchronous research pipeline that transforms a plain-language question into a structured, cited, confidence-scored markdown report. It performs intent clarification, multi‑source data gathering (internal knowledge, Google grounded search, web scraping), synthesis, conflict detection, and structured report generation.

## Overview

Pipeline stages:
1. Intent Analysis → clarifying dialogue / missing info detection
2. Data Gathering → internal knowledge, grounded Google search, (placeholder) documents, controlled-depth web scraping
3. Analysis & Synthesis → themes, conflicts, contextual summaries (comparison / timeline / pros & cons)
4. Report Generation → structured markdown (Executive Summary, Key Findings, Detailed Analysis, Contradictory Viewpoints, Bibliography)
5. Confidence Scoring → per-stage + overall weighted confidence with recommendations

All intermediate artifacts, confidence metrics, and final report metadata are persisted as JSON session files for auditability and reproducibility.

## Key Features

- **Adaptive Clarification**: Multi-turn intent interrogation with fallback handling
- **Prioritized Multi-Source Gathering**: Internal knowledge → grounded Google search → (extensible) documents → depth‑limited scraping
- **Conflict & Theme Detection**: Identifies contradictory viewpoints and synthesizes themes with fallback logic
- **Confidence Framework**: Stage + overall scoring (data quality, reliability, coverage, synthesis, structure)
- **Structured Markdown Reports**: Reproducible, sectioned, and file-named with timestamp + query snippet
- **Session Persistence**: Versioned JSON per session + optional backups
- **CLI & Direct Scripts**: Rich interactive CLI plus `simple_research.py` & `new_research.py` automation scripts
- **Resilience**: Robust JSON parsing retries + fallbacks when LLM output malformed
- **Extensibility**: Clear extension points for new data sources, analysis modules, and report formats

## Installation

### 1. Clone & Environment
```bash
git clone <repository-url> odyssey-engine
cd odyssey-engine
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt  # or: pip install -e .
cp .env.example .env
```

### 2. Configure API Key
Edit `.env`:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Verify Setup
```bash
python -m pytest -q  # optional quick sanity (most tests mock external calls)
python main.py --query "Test the pipeline works"
```

> Using `pip install -e .` enables editable mode referencing `pyproject.toml`.

## Quick Start

```bash
# Interactive guided session
python main.py

# Direct non-interactive (one-shot) query
python main.py --query "Compare EV market share in Europe vs North America 2023"

# Continue a pending session (needs clarification)
python main.py --session <session_id>

# Use simplified script (minimal features)
python simple_research.py

# Use full direct script with predefined clarification responses
python new_research.py
```

Generate a new report in `reports/` and a session JSON in `sessions/`.

## Project Structure (Core)

```
src/
	core/
		engine.py           # Orchestrates pipeline
		intent_analyzer.py  # Clarification & intent modeling
		data_gatherer.py    # Multi-source acquisition & consolidation
		report_generator.py # Sectioned markdown report assembly
	utils/
		gemini_client.py    # Gemini 2.5 API + grounded search wrapper
		web_scraper.py      # Depth-controlled async scraping & extraction
		confidence.py       # Stage + aggregate scoring logic
		storage.py          # Async JSON session + backup management
	cli/
		interface.py        # Rich interactive terminal UI
simple_research.py      # Minimal direct usage script
new_research.py         # Advanced scripted research with overrides
example.py              # Programmatic usage pattern
tests/                  # Unit + integration markers
reports/                # Generated markdown reports
sessions/               # Persisted session JSON
logs/                   # Runtime logs
```

## Configuration

Environment variables (see `.env.example` for full list):

| Variable | Purpose | Default |
|----------|---------|---------|
| GEMINI_API_KEY | Gemini API authentication | (required) |
| GEMINI_MODEL | Model name | gemini-2.5-pro |
| CONFIDENCE_THRESHOLD | % required to skip clarification / accept overall | 75 |
| MAX_FOLLOW_UP_QUESTIONS | Clarification question cap | 5 |
| MAX_SCRAPING_DEPTH | Recursive link-follow depth | 3 |
| MAX_SEARCH_RESULTS | Limit initial search URLs considered | 10 |
| SESSION_STORAGE_PATH | Session JSON directory | ./sessions |
| REPORTS_OUTPUT_PATH | Report output directory | ./reports |
| REQUEST_TIMEOUT | Seconds per remote operation | 30 |
| MAX_CONCURRENT_REQUESTS | Parallel HTTP fetches (scraper) | 5 |
| USER_AGENT | Scraper UA string | OdysseyEngine/1.0 |
| DEFAULT_REPORT_TONE | Report tone (e.g. formal_accessible) | formal_accessible |
| INCLUDE_CONFIDENCE_SCORES | Embed per-stage score note | true |
| INCLUDE_SOURCE_RELIABILITY | Show reliability metrics | true |
| LOG_LEVEL | (Not yet wired; future logging config) | INFO |
| CACHE_PATH | (Reserved for future caching) | ./cache |

Unused / planned keys (`LOG_LEVEL`, `CACHE_PATH`) are currently placeholders and safe to omit.

## CLI Usage Patterns

| Action | Command |
|--------|---------|
| Interactive start | `python main.py` |
| One-shot query | `python main.py --query "How does CRISPR base editing differ from prime editing"` |
| Continue a session | `python main.py --session <session_id>` |
| Non-interactive scripted (minimal) | `python simple_research.py` |
| Non-interactive scripted (advanced) | `python new_research.py` |

Session IDs are printed/logged after initialization; JSON lives in `sessions/`.

## Development & Quality

Install dev extras:
```bash
pip install -e .[dev]
```

Run tests (unit only):
```bash
pytest -m "not integration" -q
```

Run integration (real API calls – costs/time):
```bash
pytest -m integration -s
```

Formatting & static analysis:
```bash
black src/ && isort src/
mypy src/
pylint src/
```

Recommended pre-commit hook script can be added later (see Roadmap).

### Programmatic Usage (Example)
```python
from core.engine import ResearchEngine
import asyncio

async def main():
	engine = ResearchEngine({"GEMINI_API_KEY": "..."})
	session_id = await engine.start_research_session("Compare LLM fine-tuning vs RAG trade-offs")
	result = await engine.conduct_research(session_id)
	print(result["report"]["file_path"])  # path to markdown

asyncio.run(main())
```

## Data & Session Model

Each session JSON stores per-stage status + confidence and final report metadata enabling reproducibility & diffing.

## Confidence Scoring
Weighted combination of stage scores (intent 15%, data 35%, analysis 30%, report 20%). Recommendations surface weakest stage when below threshold.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Immediate exit: missing API key | `.env` not loaded | Confirm file + export in shell or use `python -m dotenv.main set` |
| Stuck at data gathering | Network / grounding latency | Increase `REQUEST_TIMEOUT` or reduce `MAX_SEARCH_RESULTS` |
| Empty / malformed JSON themes | LLM formatting variance | Enable `json_debug_logging` (set in config dict) or rely on fallback themes |
| Low overall confidence | Sparse sources / shallow content | Increase scraping depth or refine query specificity |
| Few or no sources in bibliography | Grounding disabled/failing | Check logs for grounding fallback warnings |

## Security & Ethics

- Never commit real API keys; use `.env` in `.gitignore`.
- Web scraping respects depth + domain filtering; still ensure compliance with target site ToS.
- Logs intentionally exclude API keys.

## Roadmap (Planned Enhancements)

- Document ingestion (PDF / Markdown parsing)
- Caching layer (`CACHE_PATH`) for repeated queries
- Configurable logging levels & structured JSON logs
- Additional report export formats (HTML / PDF)
- Pluggable analyzers (sentiment, risk, trend modeling)
- CLI subcommands for session cleanup & export

## Contributing

1. Fork & branch (`feature/xyz`)
2. Add/adjust tests (avoid real API in unit scope)
3. Ensure formatting & type checks pass
4. Update docs / README sections you affect
5. Open PR with clear summary & rationale

## License

MIT License – see `LICENSE`.

## Support & Issues

Open a GitHub issue with:
- Reproduction steps
- Session ID (if relevant)
- Stack trace excerpt (omit sensitive info)
- Environment (Python version, OS, model override)

---
*Odyssey Engine – Deep Research AI*
