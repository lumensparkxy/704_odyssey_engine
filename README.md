# Odyssey Engine - Deep Research Engine

AI-powered asynchronous research pipeline that transforms a plain-language question into a structured, cited, confidence-scored markdown report. Built on **Google ADK (Agent Development Kit)** for multi-agent orchestration.

## Overview

Pipeline stages (ADK Agents):
1. **Intent Analysis** (`IntentClarificationLoop`) → clarifying dialogue / missing info detection
2. **Data Gathering** (`DataGatheringPipeline`) → parallel collection: internal knowledge, grounded Google search, web scraping
3. **Analysis & Synthesis** (`AnalysisAgent`) → themes, conflicts, contextual summaries
4. **Report Generation** (`ReportGenerationPipeline`) → structured markdown reports with file persistence

All intermediate artifacts, confidence metrics, and final report metadata are persisted for auditability and reproducibility.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OdysseyResearchPipeline (SequentialAgent)        │
├─────────────────────────────────────────────────────────────────────┤
│  1. IntentClarificationLoop (LoopAgent)                             │
│     └─ IntentAnalyzerAgent → ConfidenceChecker → ShouldContinue     │
│                                                                     │
│  2. DataGatheringPipeline (SequentialAgent)                         │
│     ├─ ParallelGatherers (ParallelAgent)                            │
│     │   ├─ InternalKnowledgeAgent                                   │
│     │   ├─ GoogleSearchAgent                                        │
│     │   └─ WebScraperAgent                                          │
│     └─ ConsolidatorAgent                                            │
│                                                                     │
│  3. AnalysisAgent (LlmAgent)                                        │
│     └─ Theme identification, conflict detection, synthesis          │
│                                                                     │
│  4. ReportGenerationPipeline (SequentialAgent)                      │
│     ├─ ReportGeneratorAgent                                         │
│     └─ ReportFinalizerAgent + file_writer tool                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Features

- **Adaptive Clarification**: Multi-turn intent interrogation with fallback handling
- **Prioritized Multi-Source Gathering**: Internal knowledge → grounded Google search → (extensible) documents → depth‑limited scraping
- **Conflict & Theme Detection**: Identifies contradictory viewpoints and synthesizes themes with fallback logic
- **Confidence Framework**: Stage + overall scoring (data quality, reliability, coverage, synthesis, structure)
- **Structured Markdown Reports**: Reproducible, sectioned, and file-named with timestamp + query snippet
- **Session Persistence**: Versioned JSON per session + optional backups
- **CLI & Direct Scripts**: Rich interactive CLI plus `scripts/simple_research.py` & `scripts/new_research.py` automation scripts
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
# Interactive ADK-powered session (default)
python main.py

# Use legacy (non-ADK) mode
python main.py --legacy

# Direct query (legacy mode)
python main.py --legacy --query "Compare EV market share in Europe vs North America 2023"

# Use ADK web interface for development
cd src && adk web --port 8000

# Use simplified script (minimal features)
python scripts/simple_research.py
```

Generate a new report in `reports/` and a session JSON in `sessions/`.

## Project Structure (Core)

```
src/
	agents/                     # ADK Agent Definitions
		odyssey/
			agent.py            # Root SequentialAgent (pipeline orchestrator)
			intent/             # Intent analysis agents
			data_gathering/     # Parallel data gathering agents
			analysis/           # Analysis agent
			report/             # Report generation agents
			tools/              # ADK tools (scraper, confidence, file_writer)
	core/                       # Legacy engine (--legacy mode)
		engine.py               # Orchestrates pipeline
		intent_analyzer.py      # Clarification & intent modeling
		data_gatherer.py        # Multi-source acquisition
		report_generator.py     # Report assembly
	utils/
		gemini_client.py        # Gemini 2.5 API + grounded search wrapper
		web_scraper.py          # Async scraping & extraction
		confidence.py           # Confidence scoring logic
		storage.py              # Session management
		session_migration.py    # Legacy session utilities
	cli/
		adk_interface.py        # ADK-powered CLI (default)
		interface.py            # Legacy Rich CLI (--legacy)
		entrypoint.py           # CLI entrypoint
scripts/                        # Automation scripts
tests/                          # Unit + integration tests
reports/                        # Generated markdown reports
sessions/                       # Persisted session JSON
```

## Configuration

Environment variables (see `.env.example` for full list):

| Variable | Purpose | Default |
|----------|---------|---------|
| GEMINI_API_KEY | Gemini API authentication | (required) |
| GEMINI_MODEL | Model name | gemini-2.5-pro |
| CONFIDENCE_THRESHOLD | % required to skip clarification / accept overall | 75 |
| FORCE_CLARIFICATION_ON_UNCERTAINTY | If `true`, prompts that signal uncertainty (e.g. “I’m not sure… ask me what you need”) are more likely to trigger clarifying questions | true |
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
| Interactive ADK mode (default) | `python main.py` |
| Legacy interactive mode | `python main.py --legacy` |
| ADK web interface | `cd src && adk web --port 8000` |
| Non-interactive scripted | `python scripts/simple_research.py` |

### Entering multi-line prompts

When you use the interactive CLI (`python main.py`) and choose **Start New Research**, you can pick a query entry mode:

- `single`: one line prompt
- `multiline`: paste multiple lines, then end with a line containing only `END` (or send EOF with Ctrl-D)
- `file`: load a prompt from a `.txt` / `.md` file

This is useful for longer “brief”-style prompts (constraints, rubric, sections, etc.) that don’t fit nicely on a single line.

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
