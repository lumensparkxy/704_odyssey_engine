"""
Clarification Loop for Intent Analysis.

Implements a LoopAgent with PolicyEngine for human-in-the-loop clarification
when the intent confidence is below threshold.
"""

import os
import json
from typing import AsyncGenerator

from google.adk.agents import LlmAgent, LoopAgent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext

from .agent import intent_analyzer_agent, GEMINI_MODEL

# Configuration
CONFIDENCE_THRESHOLD = int(os.getenv("CONFIDENCE_THRESHOLD", "75"))
MAX_CLARIFICATION_ROUNDS = int(os.getenv("MAX_FOLLOW_UP_QUESTIONS", "5"))


class ConfidenceCheckerAgent(BaseAgent):
    """
    Custom agent that checks intent analysis confidence and decides whether to escalate.

    Escalates (exits loop) when:
    - Confidence >= threshold
    - Max iterations reached
    - User indicates they want to proceed anyway
    """

    name: str = "ConfidenceCheckerAgent"
    description: str = "Checks if intent analysis confidence meets threshold"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Check confidence and decide whether to continue or escalate."""

        # Get intent result from state
        intent_result = ctx.session.state.get("intent_result", {})
        clarification_round = ctx.session.state.get("clarification_round", 0)

        # Parse confidence from intent result
        confidence = 0
        if isinstance(intent_result, str):
            try:
                parsed = json.loads(intent_result)
                confidence = parsed.get("confidence", 0)
            except json.JSONDecodeError:
                confidence = 0
        elif isinstance(intent_result, dict):
            confidence = intent_result.get("confidence", 0)

        # Determine if we should escalate (exit the loop)
        should_escalate = False
        reason = ""

        if confidence >= CONFIDENCE_THRESHOLD:
            should_escalate = True
            reason = f"Confidence {confidence}% meets threshold {CONFIDENCE_THRESHOLD}%"
        elif clarification_round >= MAX_CLARIFICATION_ROUNDS:
            should_escalate = True
            reason = f"Max clarification rounds ({MAX_CLARIFICATION_ROUNDS}) reached"

        # Update state
        new_round = clarification_round + 1

        # Yield event with escalate decision
        yield Event(
            author=self.name,
            actions=EventActions(
                escalate=should_escalate,
                state_delta={
                    "clarification_round": new_round,
                    "needs_clarification": not should_escalate,
                    "confidence_check_reason": reason,
                    "current_confidence": confidence,
                }
            )
        )


# Clarification Question Generator Agent
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


# Create the clarification loop
# This loop runs: IntentAnalyzer -> ConfidenceChecker
# Exits when confidence is sufficient or max rounds reached
intent_clarification_loop = LoopAgent(
    name="IntentClarificationLoop",
    description="Iteratively analyzes intent and requests clarification until confidence threshold is met",
    max_iterations=MAX_CLARIFICATION_ROUNDS,
    sub_agents=[
        intent_analyzer_agent,
        confidence_checker,
    ],
)
