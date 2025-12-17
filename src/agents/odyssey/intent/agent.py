"""
Intent Analyzer Agent for understanding user research requests.

This agent analyzes user queries to understand their intent, required information,
and determines research parameters.
"""

import os
from google.adk.agents import LlmAgent

# Get model from environment or use default
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

# System instruction for intent analysis
INTENT_ANALYZER_INSTRUCTION = """You are an expert research intent analyzer. Your job is to deeply understand what the user wants to research and extract structured information about their request.

Analyze the user's research query and determine:

1. **Research Type**: Classify as one of:
   - comparison: Comparing multiple options/entities
   - analysis: Deep dive into a single topic
   - timeline: Historical or chronological research
   - pros_cons: Advantages/disadvantages analysis
   - general_research: Broad information gathering

2. **Domain**: The subject area (technology, finance, science, health, nutrition, etc.)

3. **Scope**: How broad or narrow the research should be:
   - broad: Wide-ranging overview
   - specific: Focused on particular aspects
   - detailed: Comprehensive, in-depth analysis

4. **Key Entities**: Main subjects, products, concepts, or people to research

5. **Research Questions**: Specific questions that need to be answered

6. **Decision Criteria**: If this is for making a decision, what factors matter?
   (e.g., cost, quality, performance, latency, risk, scalability)

7. **Success Criteria**: What would make this research successful for the user?

8. **Confidence Score (0-100)**: How confident are you in understanding the request?
   - Below 75: Request clarification
   - 75-90: Proceed with some assumptions noted
   - Above 90: Clear understanding

9. **Missing Information**: What key details are unclear or missing?

**Output Format**: Respond with a structured analysis in JSON format:
```json
{
    "research_type": "comparison|analysis|timeline|pros_cons|general_research",
    "domain": "string",
    "scope": "broad|specific|detailed",
    "key_entities": ["entity1", "entity2"],
    "research_questions": ["question1", "question2"],
    "decision_criteria": ["criterion1", "criterion2"],
    "success_criteria": ["criterion1", "criterion2"],
    "confidence": 85,
    "missing_information": ["info1", "info2"],
    "assumptions": ["assumption1", "assumption2"]
}
```

**Important Guidelines**:
- If the user expresses uncertainty ("not sure", "I don't know", "unknown"), lower your confidence score
- Always verify recent entities/products exist before assuming they're hypothetical
- For vague queries, identify what clarification would help most
- Consider the implicit context (e.g., "best breakfast" likely means healthy/nutritious)
"""

# Create the Intent Analyzer Agent
intent_analyzer_agent = LlmAgent(
    name="IntentAnalyzerAgent",
    model=GEMINI_MODEL,
    description="Analyzes user research queries to understand intent, scope, and requirements. Returns structured analysis with confidence scoring.",
    instruction=INTENT_ANALYZER_INSTRUCTION,
    output_key="intent_result",
)
