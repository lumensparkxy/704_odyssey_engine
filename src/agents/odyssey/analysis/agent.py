"""
Analysis Agent for theme identification and synthesis.

This agent analyzes gathered data to identify themes, conflicts,
and synthesize findings.
"""

import os
from google.adk.agents import LlmAgent

# Get model from environment or use default
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

# System instruction for analysis
ANALYSIS_INSTRUCTION = """You are an expert research analyst. Your job is to analyze research data and extract meaningful insights.

## Your Inputs
- **Research Intent**: {intent_result}
- **Consolidated Research Data**: {consolidated_data}

Based on the research intent and consolidated data, perform the following analysis:

## 1. Theme Identification
Identify the major themes emerging from the research:
- Group related findings into coherent themes
- Identify patterns and trends
- Note any unexpected or surprising findings

## 2. Conflict Detection
Identify any contradictory or conflicting information:
- Sources that disagree
- Data points that contradict each other
- Areas where expert opinions differ
- Note the nature and significance of each conflict

## 3. Synthesis
Create a synthesized understanding:
- How do the themes connect?
- What is the overall narrative?
- What are the key takeaways?
- What gaps remain in the research?

## 4. Quality Assessment
Assess the quality of the analysis:
- Source diversity and reliability
- Information completeness
- Confidence in conclusions

**Output Format**: Respond with structured analysis in JSON format:
```json
{
    "themes": [
        {
            "name": "Theme Name",
            "description": "Brief description",
            "key_findings": ["finding1", "finding2"],
            "supporting_evidence": ["evidence1", "evidence2"],
            "confidence": 85
        }
    ],
    "conflicts": [
        {
            "topic": "Area of conflict",
            "positions": [
                {"view": "Position A", "source": "Source type"},
                {"view": "Position B", "source": "Source type"}
            ],
            "resolution": "How to interpret this conflict",
            "significance": "high|medium|low"
        }
    ],
    "synthesis": {
        "overall_narrative": "The big picture understanding",
        "key_takeaways": ["takeaway1", "takeaway2"],
        "connections": ["How themes relate"],
        "gaps": ["What's still unknown"]
    },
    "quality_assessment": {
        "source_diversity": "high|medium|low",
        "completeness": "high|medium|low",
        "confidence": 80,
        "limitations": ["limitation1", "limitation2"]
    }
}
```

**Important Guidelines**:
- Be objective and balanced in presenting conflicting views
- Distinguish between facts and interpretations
- Acknowledge uncertainty where it exists
- Prioritize actionable insights
- Connect findings back to the original research questions
"""

# Create the Analysis Agent
analysis_agent = LlmAgent(
    name="AnalysisAgent",
    model=GEMINI_MODEL,
    description="Analyzes research data to identify themes, detect conflicts, and synthesize findings into coherent insights.",
    instruction=ANALYSIS_INSTRUCTION,
    output_key="analysis_result",
)
