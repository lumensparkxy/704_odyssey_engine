<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Odyssey Engine - Deep Research AI

## Project Overview
This is a Python-based command-line research engine that uses Google's Gemini Pro 2.5 API to conduct comprehensive research. The system follows a structured pipeline: Intent Analysis → Data Gathering → Analysis & Compilation → Report Generation.

## Architecture Guidelines

### Core Components
- **ResearchEngine**: Main orchestrator in `src/core/engine.py`
- **IntentAnalyzer**: User intent understanding in `src/core/intent_analyzer.py`
- **DataGatherer**: Multi-source information collection in `src/core/data_gatherer.py`
- **ReportGenerator**: Markdown report generation in `src/core/report_generator.py`

### Utilities
- **GeminiClient**: API wrapper in `src/utils/gemini_client.py`
- **WebScraper**: Intelligent web scraping in `src/utils/web_scraper.py`
- **ConfidenceScorer**: LLM-based confidence assessment in `src/utils/confidence.py`
- **SessionStorage**: JSON-based session persistence in `src/utils/storage.py`

### CLI Interface
- **OdysseyCLI**: Rich terminal interface in `src/cli/interface.py`

## Coding Standards

### Async/Await Pattern
All core operations use async/await for better performance:
```python
async def conduct_research(self, session_id: str) -> Dict[str, Any]:
    # Always use async for I/O operations
```

### Error Handling
Implement comprehensive error handling with graceful degradation:
```python
try:
    result = await self.some_operation()
except SpecificException as e:
    self.logger.error(f"Operation failed: {str(e)}")
    return fallback_result
```

### Configuration Management
Use environment variables with sensible defaults:
```python
self.timeout = config.get("REQUEST_TIMEOUT", 30)
```

### Confidence Scoring
Every major operation should include confidence assessment:
```python
confidence = await self.confidence_scorer.score_operation(result)
```

## Data Flow Patterns

### Session Storage
All intermediate results are stored in JSON format with nested structure:
```json
{
  "session_id": "uuid",
  "stages": {
    "intent_analysis": {"status": "completed", "result": {}, "confidence": {}},
    "data_gathering": {"status": "completed", "result": {}, "confidence": {}},
    // ... other stages
  }
}
```

### Multi-Source Data Gathering
Follow the priority order: Internal Knowledge → Google Search → Documents → Web Scraping

### Report Generation
Generate structured markdown reports with consistent sections:
- Executive Summary
- Key Findings
- Detailed Analysis
- Contradictory Viewpoints
- Bibliography

## Testing Guidelines
- Use pytest for all tests
- Mock external API calls (Gemini, web requests)
- Test both success and failure scenarios
- Include integration tests for full research pipeline

## Documentation
- Use comprehensive docstrings for all classes and methods
- Include type hints for all function parameters and return values
- Document configuration options and their effects
- Provide usage examples in docstrings

## Dependencies
Key dependencies and their purposes:
- `google-generativeai`: Gemini API integration
- `aiohttp`: Async HTTP requests
- `beautifulsoup4`: HTML parsing
- `rich`: Terminal UI components
- `click`: CLI framework
- `pydantic`: Data validation

## Development Workflow
1. Test individual components before integration
2. Use the confidence scoring system to validate results
3. Ensure all async operations are properly awaited
4. Store intermediate results for debugging and analysis
5. Generate comprehensive logs for troubleshooting

## Security Considerations
- Never log API keys or sensitive data
- Validate all user inputs before processing
- Implement rate limiting for external requests
- Use safe file path operations to prevent directory traversal

## Performance Guidelines
- Use connection pooling for HTTP requests
- Implement caching where appropriate
- Limit concurrent operations to prevent resource exhaustion
- Store only essential data in session files
