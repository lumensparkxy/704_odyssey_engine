````markdown
# Direct Research Scripts Usage Guide

This repo includes scripts that let you run research directly without going through the interactive CLI.

## 1. `scripts/new_research.py` - Full-Featured Direct Research

This is the comprehensive version with detailed configuration options and robust error handling.

### Features:
- Detailed configuration override options
- Comprehensive error handling and status reporting
- Confidence score reporting
- Pre-configured clarification responses
- Detailed progress reporting

### Usage:

1. **Edit the research query:**
   ```python
   RESEARCH_QUERY = """
   Your research question here.
   You can use multiple lines for complex queries.
   """
   ```

2. **Optional: Pre-configure clarification responses:**
   ```python
   CLARIFICATION_RESPONSES = {
       "What specific aspect interests you most?": "Business applications",
       "What time period should I focus on?": "2024-2025",
       "What industries are you most interested in?": "Technology, healthcare"
   }
   ```

3. **Optional: Override configuration:**
   ```python
   CONFIG_OVERRIDES = {
       "CONFIDENCE_THRESHOLD": 80,
       "MAX_SEARCH_RESULTS": 15,
       "DEFAULT_REPORT_TONE": "formal_accessible"
   }
   ```

4. **Run the script:**
   ```bash
   python scripts/new_research.py
   ```

### Example Workflow:
1. First run: The script will show you what clarification questions the engine asks
2. Add responses to `CLARIFICATION_RESPONSES`
3. Second run: The script will use your responses and complete the research

## 2. `scripts/simple_research.py` - Minimal Setup Version

This is a streamlined version for quick research tasks.

### Features:
- Minimal configuration
- Simple error handling
- Quick setup and execution

### Usage:

1. **Edit the research query:**
   ```python
   RESEARCH_QUERY = """
   Your research question here.
   """
   ```

2. **Run the script:**
   ```bash
   python scripts/simple_research.py
   ```

3. **If clarification is needed, add responses:**
   ```python
   CLARIFICATION_RESPONSES = {
       "Question from engine": "Your answer"
   }
   ```

## Environment Setup

Both scripts require the same environment setup as the main application:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up your API key in `.env` file:**
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

   Optional (advanced) variables such as `CONFIDENCE_THRESHOLD`, `MAX_SCRAPING_DEPTH`,
   `MAX_SEARCH_RESULTS`, and `DEFAULT_REPORT_TONE` can refine behavior. Placeholders
   `CACHE_PATH` and `LOG_LEVEL` are not yet active.

   Refer to `README.md` for the canonical environment variable list.

## Output Files

Both scripts will generate:
- **Report file**: `reports/research_report_[query_snippet]_[timestamp].md`
- **Session file**: `sessions/session_[uuid].json`
- **Log file**: `logs/odyssey.log`

Choose the script that best fits your workflow and research needs.

````
