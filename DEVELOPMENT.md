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
python main.py                # interactive
python main.py --query "Your research question"  # one-shot
python main.py --session <session_id>            # continue
python simple_research.py     # minimal scripted
python new_research.py        # advanced scripted
python example.py             # programmatic sample
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

## Data Flow

### Session Storage Format
```json
{
  "session_id": "uuid-string",
  "created_at": "2025-01-01T12:00:00",
  "initial_query": "User's original question",
  "status": "completed|needs_clarification|error",
  "stages": {
    "intent_analysis": {
      "status": "completed",
      "result": { /* analysis results */ },
      "confidence": { /* confidence scores */ }
    },
    "data_gathering": { /* similar structure */ },
    "analysis": { /* similar structure */ },
    "report_generation": { /* similar structure */ }
  },
  "final_report": { /* report metadata */ },
  "overall_confidence": 85.5
}
```

### Confidence Scoring
Each stage includes confidence assessment:
```python
confidence = {
    "overall_confidence": 85.5,
    "confidence_level": "High",
    "factors": {
        "data_quality": 80.0,
        "source_reliability": 90.0,
        "coverage_completeness": 85.0
    },
    "recommendations": ["Suggestion 1", "Suggestion 2"]
}
```

## Development Patterns

### 1. Async/Await Usage
All I/O operations use async patterns:
```python
async def process_data(self, data):
    result = await self.external_api_call(data)
    processed = await self.analyze_result(result)
    return processed
```

### 2. Error Handling
Comprehensive error handling with graceful degradation:
```python
try:
    result = await self.risky_operation()
except SpecificException as e:
    self.logger.error(f"Operation failed: {e}")
    result = self.fallback_method()
except Exception as e:
    self.logger.critical(f"Unexpected error: {e}")
    raise ResearchEngineError(f"Critical failure: {e}")
```

### 3. Configuration Management
Use environment variables with defaults:
```python
self.timeout = config.get("REQUEST_TIMEOUT", 30)
self.max_depth = int(os.getenv("MAX_SCRAPING_DEPTH", "3"))
```

### 4. Logging
Currently initializes basic logging to `logs/odyssey.log`. Planned enhancement: structured JSON logging and dynamic level from `LOG_LEVEL`.
Structured logging throughout:
```python
self.logger.info(f"Starting research session {session_id}")
self.logger.warning(f"Low confidence score: {confidence}")
self.logger.error(f"Failed to process: {error}")
```

## Testing

### Unit Tests
```bash
pytest -m "not integration"            # fast unit tests (mocks)
pytest -m integration -s               # real API (cost/time)
pytest --cov=src --cov-report=term-missing
```

Markers declared in `pyproject.toml`. Avoid running integration in CI without secrets.

### Integration Tests
Use `-m integration`. They call the real Gemini API; skip automatically if no key present.

### Test Structure
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_research_pipeline():
    # Setup mocks
    mock_client = AsyncMock()
    
    # Test operation
    result = await engine.conduct_research(session_id)
    
    # Assertions
    assert result["status"] == "completed"
    assert result["confidence"]["overall_confidence"] > 70
```

## Debugging

### 1. Enable Verbose Logging
Set `logging.basicConfig(level=logging.DEBUG)` early or set environment then patch code until dynamic level is implemented.

### 2. Session Inspection
```python
# Load and inspect session
session_data = await storage.load_session(session_id)
print(json.dumps(session_data, indent=2))
```

### 3. Confidence Analysis
```python
# Check confidence factors
confidence = await scorer.score_data_quality(data_result)
print(f"Quality factors: {confidence['quality_factors']}")
```

## Performance Optimization

### 1. Concurrent Operations
```python
# Process multiple sources concurrently
tasks = [self.process_source(source) for source in sources]
results = await asyncio.gather(*tasks)
```

### 2. Connection Pooling
```python
# Use aiohttp session for connection reuse
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        return await response.text()
```

### 3. Caching (Planned)
```python
# Cache expensive operations
@lru_cache(maxsize=128)
def expensive_computation(input_data):
    return complex_analysis(input_data)
```

## Common Issues & Solutions

### 1. API Rate Limits
- Implement exponential backoff
- Use connection pooling
- Respect rate limiting headers

### 2. Web Scraping Failures
- Implement robust error handling
- Use fallback strategies
- Respect robots.txt

### 3. Memory Usage
- Stream large responses
- Implement pagination
- Clear intermediate data

### 4. Configuration Issues
- Validate configuration on startup
- Provide clear error messages
- Use environment-specific configs

## Extending the Engine

### 1. Adding New Data Sources
```python
class CustomDataSource:
    async def gather_data(self, query):
        # Implement data gathering logic
        return structured_data
```

### 2. Custom Report Formats
```python
class PDFReportGenerator(ReportGenerator):
    async def generate_report(self, data):
        # Custom PDF generation logic
        return pdf_report
```

### 3. Additional Analysis Types
```python
class SentimentAnalyzer:
    async def analyze_sentiment(self, content):
        # Sentiment analysis implementation
        return sentiment_scores
```

## Deployment

### 1. Local Development
```bash
python main.py
```

### 2. Docker Deployment (Example)
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

### 3. Production Considerations
- Use proper logging configuration
- Implement health checks
- Set up monitoring and alerting
- Use secrets management for API keys
- Implement proper error tracking

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run quality checks: `black src/ && isort src/ && pytest`
5. Commit changes: `git commit -m "Add feature"`
6. Push branch: `git push origin feature-name`
7. Create pull request

## Resources

- [Gemini API (Google AI)](https://ai.google.dev/docs)
- [AsyncIO](https://docs.python.org/3/library/asyncio.html)
- [Rich](https://rich.readthedocs.io/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [aiohttp](https://docs.aiohttp.org/)

## Roadmap (High-Level)

- Document parsing (PDF/HTML normalization) integration
- Config-driven logging level & structured JSON logs
- Caching layer keyed by normalized query intent
- Multi-format export (HTML/PDF)
- Pluggable analysis modules (trend, risk, sentiment)

---
Maintainers: Update this guide when adding configuration flags, changing session schema, or introducing new pipeline stages.
