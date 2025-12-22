"""
Clarification Loop for Intent Analysis.

Implements a LoopAgent with human-in-the-loop clarification
when the intent confidence is below threshold.

Flow:
1. IntentAnalyzerAgent - Analyzes query and outputs structured intent
2. ConfidenceCheckerAgent - Checks confidence and determines if clarification needed
3. HumanInputAgent - Requests user input (clarification or confirmation)
4. Loop continues until user confirms or max iterations reached
"""

import os
import json
from typing import AsyncGenerator, Dict, Any

from google.adk.agents import LlmAgent, LoopAgent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext

from .agent import intent_analyzer_agent, GEMINI_MODEL
from .human_input import human_input_agent

# Configuration
CONFIDENCE_THRESHOLD = int(os.getenv("CONFIDENCE_THRESHOLD", "75"))
MAX_CLARIFICATION_ROUNDS = int(os.getenv("MAX_FOLLOW_UP_QUESTIONS", "5"))


def parse_intent_result(intent_result: Any) -> Dict[str, Any]:
    """
    Parse intent result from string or dict format.

    Args:
        intent_result: Raw intent result (string with JSON or dict)

    Returns:
        Parsed dictionary with intent data
    """
    if isinstance(intent_result, dict):
        return intent_result

    if isinstance(intent_result, str):
        try:
            # Strip markdown code blocks if present
            clean_result = intent_result.strip()
            if clean_result.startswith("```json"):
                clean_result = clean_result[7:]
            elif clean_result.startswith("```"):
                clean_result = clean_result[3:]
            if clean_result.endswith("```"):
                clean_result = clean_result[:-3]
            clean_result = clean_result.strip()

            return json.loads(clean_result)
        except json.JSONDecodeError:
            return {}

    return {}


class ConfidenceCheckerAgent(BaseAgent):
    """
    Custom agent that checks intent analysis confidence and sets state flags.

    This agent:
    1. Parses the intent result
    2. Extracts confidence score
    3. Determines if clarification is needed
    4. Sets state flags for HumanInputAgent to use

    Does NOT escalate directly - that's handled by HumanInputAgent based on user confirmation.
    """

    name: str = "ConfidenceCheckerAgent"
    description: str = "Checks if intent analysis confidence meets threshold and prepares state for human input"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Check confidence and set state flags."""

        state = ctx.session.state

        # Check if user already confirmed - if so, escalate
        if state.get("user_confirmed_proceed", False):
            yield Event(
                author=self.name,
                actions=EventActions(
                    escalate=True,
                    state_delta={
                        "confidence_check_status": "user_confirmed_escalate",
                    }
                )
            )
            return

        # Get intent result from state
        intent_result = state.get("intent_result", {})
        clarification_round = state.get("clarification_round", 0)

        # Parse intent result
        parsed_intent = parse_intent_result(intent_result)
        confidence = parsed_intent.get("confidence", 0)

        # Determine if clarification is needed
        needs_clarification = confidence < CONFIDENCE_THRESHOLD
        max_rounds_reached = clarification_round >= MAX_CLARIFICATION_ROUNDS

        # Build criteria check result
        criteria_status = {
            "has_research_type": bool(parsed_intent.get("research_type")),
            "has_domain": bool(parsed_intent.get("domain")),
            "has_scope": bool(parsed_intent.get("scope")),
            "has_key_entities": bool(parsed_intent.get("key_entities")) and len(parsed_intent.get("key_entities", [])) > 0,
            "has_research_questions": bool(parsed_intent.get("research_questions")) and len(parsed_intent.get("research_questions", [])) > 0,
            "has_decision_criteria": bool(parsed_intent.get("decision_criteria")),
            "missing_info_count": len(parsed_intent.get("missing_information", [])),
        }

        # Determine reason
        if not needs_clarification:
            reason = f"Confidence {confidence}% meets threshold {CONFIDENCE_THRESHOLD}%"
        elif max_rounds_reached:
            reason = f"Max clarification rounds ({MAX_CLARIFICATION_ROUNDS}) reached"
        else:
            reason = f"Confidence {confidence}% below threshold {CONFIDENCE_THRESHOLD}% - clarification needed"

        # Update round counter
        new_round = clarification_round + 1

        # If max rounds reached without user confirmation, escalate with warning
        if max_rounds_reached and not state.get("user_confirmed_proceed", False):
            yield Event(
                author=self.name,
                actions=EventActions(
                    escalate=True,  # Force exit after max rounds
                    state_delta={
                        "clarification_round": new_round,
                        "needs_clarification": False,  # No more clarification possible
                        "max_rounds_reached": True,
                        "confidence_check_reason": reason,
                        "current_confidence": confidence,
                        "parsed_intent": parsed_intent,
                        "criteria_status": criteria_status,
                        "confidence_check_status": "max_rounds_escalate",
                    }
                )
            )
            return

        # Otherwise, set state for HumanInputAgent (don't escalate - let human decide)
        yield Event(
            author=self.name,
            actions=EventActions(
                escalate=False,  # Don't escalate - wait for human input
                state_delta={
                    "clarification_round": new_round,
                    "needs_clarification": needs_clarification,
                    "confidence_check_reason": reason,
                    "current_confidence": confidence,
                    "parsed_intent": parsed_intent,
                    "criteria_status": criteria_status,
                    "confidence_check_status": "awaiting_human_input",
                }
            )
        )


# Clarification Question Generator Agent (LLM-based alternative)
clarification_agent = LlmAgent(
    name="ClarificationAgent",
    model=GEMINI_MODEL,
    description="Generates clarifying questions when intent analysis confidence is low",
    instruction="""You are helping to clarify a research request. Based on the current intent analysis, generate helpful clarifying questions.

Review the intent analysis in {intent_result} and the missing information identified.

Generate 1-3 clear, specific questions that will help clarify:
- Ambiguous scope or requirements
- Missing context needed for research
- Unclear decision criteria
- Timeframe or geographic constraints

Format your questions conversationally, making them easy to answer. Include examples where helpful.

If {needs_clarification} is false, simply acknowledge the request is clear and summarize the understood intent.
""",
    output_key="clarification_questions",
)


# Create the confidence checker instance
confidence_checker = ConfidenceCheckerAgent()


# Create the clarification loop with human-in-the-loop
# Flow: IntentAnalyzer -> ConfidenceChecker -> HumanInputAgent
# Loop continues until:
# - User confirms to proceed (user_confirmed_proceed = True)
# - Max iterations reached
intent_clarification_loop = LoopAgent(
    name="IntentClarificationLoop",
    description="Iteratively analyzes intent with human-in-the-loop clarification until user confirms",
    max_iterations=MAX_CLARIFICATION_ROUNDS,
    sub_agents=[
        intent_analyzer_agent,   # 1. Analyze/re-analyze query
        confidence_checker,       # 2. Check confidence & set flags
        # 3. Request human input (clarification or confirmation)
        human_input_agent,
    ],
)
