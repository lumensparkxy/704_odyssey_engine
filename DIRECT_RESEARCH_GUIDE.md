# Direct Research Scripts Usage Guide

This directory contains two scripts that allow you to conduct research directly without going through the interactive CLI menu:

## 1. `new_research.py` - Full-Featured Direct Research

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
   python new_research.py
   ```

### Example Workflow:
1. First run: The script will show you what clarification questions the engine asks
2. Add responses to `CLARIFICATION_RESPONSES` 
3. Second run: The script will use your responses and complete the research

## 2. `simple_research.py` - Minimal Setup Version

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
   python simple_research.py
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

## Example Research Queries

Here are some example research queries you can use:

### Technology Research:
```python
RESEARCH_QUERY = """
What are the latest developments in quantum computing in 2024-2025? 
Focus on practical applications, major breakthroughs, and commercial viability.
"""
```

### Business Research:
```python
RESEARCH_QUERY = """
What are the key factors that influence employee productivity in remote work environments?
Include best practices, tools, and management strategies.
"""
```

### Health Research:
```python
RESEARCH_QUERY = """
What are the latest evidence-based treatments for anxiety disorders?
Focus on therapeutic approaches, medication options, and efficacy rates.
"""
```

### Market Research:
```python
RESEARCH_QUERY = """
What are the current trends in the electric vehicle market?
Include market size, key players, consumer adoption rates, and future projections.
"""
```

## Common Clarification Questions

Based on the engine's behavior, here are common clarification questions and example responses:

```python
CLARIFICATION_RESPONSES = {
    "What specific aspect of [topic] interests you most?": "Practical applications and real-world impact",
    "What time period should I focus on?": "2024-2025",
    "What industries or sectors are you most interested in?": "Technology, healthcare, finance",
    "What is your primary purpose for this research?": "Academic research and analysis",
    "What level of technical detail do you need?": "Intermediate - accessible but comprehensive",
    "What geographic regions should I focus on?": "Global perspective with emphasis on North America and Europe",
    "What type of sources are most valuable to you?": "Academic papers, industry reports, and recent news"
}
```

## Tips for Better Results

1. **Be specific in your queries**: More specific questions lead to better focused research
2. **Use multi-line queries**: Break complex questions into clear, detailed explanations
3. **Pre-configure responses**: If you run research on similar topics, reuse clarification responses
4. **Check confidence scores**: Use the confidence information to assess result reliability
5. **Review session files**: Check the `sessions/` directory for detailed research progress
6. **Read the full reports**: The generated markdown reports contain comprehensive information

## Output Files

Both scripts will generate:
- **Report file**: `reports/research_report_[query_snippet]_[timestamp].md`
- **Session file**: `sessions/session_[uuid].json`
- **Log file**: `logs/odyssey.log`

## Troubleshooting

1. **API Key Issues**: Ensure your `GEMINI_API_KEY` is set in the `.env` file
2. **Import Errors**: Run `pip install -r requirements.txt` to install dependencies
3. **Timeout Issues**: Increase `REQUEST_TIMEOUT` in configuration
4. **Rate Limiting**: The engine has built-in rate limiting, but you can adjust `MAX_CONCURRENT_REQUESTS`

## Integration with Main CLI

These scripts are fully compatible with the main CLI application:
- Session files can be continued using the main CLI
- Reports can be viewed through the CLI interface
- Configuration changes affect both approaches

Choose the script that best fits your workflow and research needs!
