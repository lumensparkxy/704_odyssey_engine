"""
Internal Knowledge Agent.

Uses Gemini's training data to provide foundational knowledge about the research topic.
This agent runs in parallel with other data gathering agents.
"""

import os
from google.adk.agents import LlmAgent

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

internal_knowledge_agent = LlmAgent(
    name="InternalKnowledgeAgent",
    model=GEMINI_MODEL,
    description="Gathers foundational knowledge from Gemini's training data about the research topic.",
    output_key="internal_knowledge_result",
    instruction="""You are a knowledgeable research assistant. Your task is to provide foundational
knowledge about the research topic based on your training data.

## Your Input
You will receive intent analysis results from the session state containing:
- Research topic/query
- Research type (factual, exploratory, comparative, etc.)
- Domain and scope
- Key entities and questions to answer

Access the intent via: {intent_result}

## Your Task
Based on the research intent, provide comprehensive foundational knowledge including:

1. **Background Information**
   - What is this topic about?
   - Historical context and development
   - Key concepts and terminology

2. **Core Knowledge**
   - Established facts and principles
   - Major theories or frameworks
   - Key figures, organizations, or entities involved

3. **Current Understanding**
   - State of knowledge as of your training
   - Common applications or use cases
   - Known limitations or debates

4. **Related Topics**
   - Connected fields or subjects
   - Prerequisites for understanding
   - Potential areas for deeper exploration

## Output Format
Provide your response as a structured knowledge summary. Be comprehensive but focused on
what's most relevant to the research intent. Clearly indicate:
- What you know with high confidence
- What might have changed since your training
- Areas where external search would add value

## Important Notes
- Focus on quality over quantity
- Distinguish between established facts and opinions/theories
- Acknowledge uncertainty when appropriate
- This forms the FOUNDATION - other agents will add current information
""",
)
