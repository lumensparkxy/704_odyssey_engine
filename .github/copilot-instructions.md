<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Odyssey Engine - Deep Research AI (v2.0 - ADK)

## Project Overview
This is a Python-based research engine powered by Google ADK (Agent Development Kit) that conducts comprehensive research using a multi-agent pipeline. The system uses specialized agents for each stage: Intent Analysis → Data Gathering → Analysis → Report Generation.

## Architecture (ADK v2.0)

### Pipeline Structure
```
OdysseyResearchPipeline (SequentialAgent)
├── IntentClarificationLoop (LoopAgent)
│   ├── IntentAnalysisAgent (LlmAgent)
│   └── ConfidenceCheckerAgent (LlmAgent)
├── DataGatheringPipeline (SequentialAgent)
│   ├── ParallelDataGatherer (ParallelAgent)
│   │   ├── InternalKnowledgeAgent (LlmAgent)
│   │   ├── GoogleSearchAgent (LlmAgent) + google_search tool
│   │   └── WebScraperAgent (LlmAgent) + url_context tool
│   └── ConsolidatorAgent (LlmAgent)
├── AnalysisAgent (LlmAgent)
└── ReportGenerationPipeline (SequentialAgent)
    ├── ReportWriterAgent (LlmAgent)
    └── ReportSaverAgent (LlmAgent) + save_report_to_file tool
```

### Core Components
- **src/agents/odyssey/agent.py**: Root pipeline (OdysseyResearchPipeline)
- **src/agents/odyssey/intent/**: Intent analysis and confidence checking agents
- **src/agents/odyssey/data_gathering/**: Parallel data gathering (search, scraping, knowledge)
- **src/agents/odyssey/analysis/**: Analysis agent
- **src/agents/odyssey/report/**: Report generation pipeline
- **src/agents/odyssey/tools/**: Custom ADK tools (confidence, file_writer)

### CLI Interface
- **src/cli/adk_interface.py**: Rich terminal interface using ADK Runner
- **src/cli/entrypoint.py**: Click-based command entry point

## Coding Standards

### ADK Agent Pattern
All agents use Google ADK's agent types:
```python
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent

my_agent = LlmAgent(
    name="AgentName",
    model=GEMINI_MODEL,
    description="What this agent does",
    output_key="state_key_for_output",
    tools=[tool1, tool2],
    instruction="Detailed prompt...",
)
```

### State Management
Agents communicate via session state:
```python
# Writing to state (via output_key)
output_key="intent_result"

# Reading from state (via instruction template)
instruction="""Access data via: {intent_result}"""
```

### Built-in Tools
Use ADK's built-in tools when available:
- `google_search` - Web search grounding
- `url_context` - URL content extraction (replaces custom scraper)

### Custom Tools
For custom functionality:
```python
from google.adk.tools import FunctionTool

def my_tool(param: str) -> Dict[str, Any]:
    """Tool docstring becomes the description."""
    return {"result": "value"}

my_tool_adk = FunctionTool(func=my_tool)
```

## Testing Guidelines
- Use pytest for all tests
- Tests are in `tests/test_adk_phase*.py`
- Test agent structure, configuration, and pipeline order
- Mock external API calls (Gemini)

## Key Dependencies
- `google-adk`: Agent Development Kit
- `google-generativeai`: Gemini API
- `rich`: Terminal UI
- `click`: CLI framework

## Running the Application
```bash
# Interactive mode
python -m src.cli.entrypoint

# With query
python -m src.cli.entrypoint -q "your research query"

# Direct main.py
python main.py
```

## Environment Variables
- `GEMINI_API_KEY`: Required - Gemini API key
- `GEMINI_MODEL`: Optional - Model name (default: gemini-2.5-pro)
- `REPORTS_OUTPUT_PATH`: Optional - Report output directory (default: ./reports)
