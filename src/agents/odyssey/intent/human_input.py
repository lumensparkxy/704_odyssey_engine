"""
Human Input Agent for Intent Clarification.

Provides human-in-the-loop interaction during intent analysis.
This agent pauses the pipeline to:
1. Display current understanding and criteria checklist
2. Ask clarification questions
3. Get user confirmation before proceeding
"""

import os
import json
from typing import AsyncGenerator, Dict, Any, List

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext

# Get model from environment or use default
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


class HumanInputAgent(BaseAgent):
    """
    Custom agent that requests human input during intent clarification.

    This agent ALWAYS escalates (exits the loop) immediately to give CLI control.
    The clarification "loop" is managed by CLI re-invoking the pipeline,
    NOT by internal LoopAgent iteration. This ensures:
    - Only 1 LLM call per user interaction
    - CLI can enforce max 5 clarification rounds
    - User sees results immediately after each analysis
    """

    name: str = "HumanInputAgent"
    description: str = "Requests and processes human input for intent clarification"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        Handle human input flow.

        States managed:
        - awaiting_user_input: True when waiting for user
        - user_clarification_response: User's response text
        - user_confirmed_proceed: User explicitly confirmed to proceed
        - clarification_questions: Questions to show user
        - intent_criteria_display: Formatted criteria for display
        """

        state = ctx.session.state

        # Check if we're receiving a response from user
        user_response = state.get("user_clarification_response")
        user_confirmed = state.get("user_confirmed_proceed", False)

        # If user confirmed to proceed, escalate (exit loop)
        if user_confirmed:
            yield Event(
                author=self.name,
                actions=EventActions(
                    escalate=True,
                    state_delta={
                        "awaiting_user_input": False,
                        "human_input_status": "user_confirmed_proceed",
                    }
                )
            )
            return

        # If user provided a response, incorporate it and ESCALATE
        # CLI will re-run the pipeline with the enriched query
        if user_response and not state.get("response_processed", False):
            # Build enriched query with user's clarification
            original_query = state.get("original_query", "")
            enriched_query = self._build_enriched_query(
                original_query, user_response, state)

            yield Event(
                author=self.name,
                actions=EventActions(
                    escalate=True,  # ESCALATE - let CLI re-run with new query
                    state_delta={
                        "awaiting_user_input": False,
                        "enriched_query": enriched_query,
                        "original_query": enriched_query,  # Update for next iteration
                        "response_processed": True,
                        "user_clarification_response": None,  # Clear for next round
                        "human_input_status": "response_incorporated",
                        "needs_reanalysis": True,  # Signal CLI to re-run intent analysis
                    }
                )
            )
            return

        # Otherwise, we need to request human input
        # First, check current confidence and prepare display
        intent_result = state.get("intent_result", {})
        current_confidence = state.get("current_confidence", 0)
        needs_clarification = state.get("needs_clarification", True)
        clarification_round = state.get("clarification_round", 0)

        # Parse intent if it's a string
        parsed_intent = self._parse_intent(intent_result)

        # Build criteria display
        criteria_display = self._build_criteria_display(parsed_intent)

        # Determine if we should ask for confirmation or clarification
        if not needs_clarification or current_confidence >= 75:
            # High confidence - ask for confirmation only
            yield Event(
                author=self.name,
                actions=EventActions(
                    escalate=True,  # ESCALATE to let CLI handle confirmation
                    state_delta={
                        "awaiting_user_input": True,
                        "input_type": "confirmation",
                        "intent_criteria_display": criteria_display,
                        "clarification_questions": [],
                        "response_processed": False,
                        "human_input_status": "awaiting_confirmation",
                        "parsed_intent": parsed_intent,
                    }
                )
            )
        else:
            # Low confidence - generate clarification questions
            questions = self._generate_clarification_questions(
                parsed_intent, clarification_round)

            yield Event(
                author=self.name,
                actions=EventActions(
                    escalate=True,  # ESCALATE to let CLI ask questions
                    state_delta={
                        "awaiting_user_input": True,
                        "input_type": "clarification",
                        "intent_criteria_display": criteria_display,
                        "clarification_questions": questions,
                        "response_processed": False,
                        "human_input_status": "awaiting_clarification",
                        "parsed_intent": parsed_intent,
                    }
                )
            )

    def _parse_intent(self, intent_result: Any) -> Dict[str, Any]:
        """Parse intent result from string or dict."""
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

    def _build_criteria_display(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Build formatted criteria checklist for display."""
        confidence = intent.get("confidence", 0)
        output_prefs = intent.get("output_preferences", {}) or {}

        criteria = [
            {
                "name": "Research Type",
                "met": bool(intent.get("research_type")),
                "value": intent.get("research_type", "Not specified"),
                "icon": "✅" if intent.get("research_type") else "❌",
            },
            {
                "name": "Domain/Subject Area",
                "met": bool(intent.get("domain")),
                "value": intent.get("domain", "Not specified"),
                "icon": "✅" if intent.get("domain") else "❌",
            },
            {
                "name": "Research Scope",
                "met": bool(intent.get("scope")),
                "value": intent.get("scope", "Not specified"),
                "icon": "✅" if intent.get("scope") else "❌",
            },
            {
                "name": "Key Entities",
                "met": bool(intent.get("key_entities")) and len(intent.get("key_entities", [])) > 0,
                "value": ", ".join(intent.get("key_entities", [])) or "None identified",
                "icon": "✅" if intent.get("key_entities") else "❌",
            },
            {
                "name": "Research Questions",
                "met": bool(intent.get("research_questions")) and len(intent.get("research_questions", [])) > 0,
                "value": f"{len(intent.get('research_questions', []))} questions",
                "icon": "✅" if intent.get("research_questions") else "❌",
            },
            {
                "name": "Decision Criteria",
                "met": bool(intent.get("decision_criteria")) and len(intent.get("decision_criteria", [])) > 0,
                "value": f"{len(intent.get('decision_criteria', []))} criteria",
                "icon": "✅" if intent.get("decision_criteria") else "⚠️",
            },
            {
                "name": "Success Criteria",
                "met": bool(intent.get("success_criteria")) and len(intent.get("success_criteria", [])) > 0,
                "value": f"{len(intent.get('success_criteria', []))} criteria",
                "icon": "✅" if intent.get("success_criteria") else "⚠️",
            },
            {
                "name": "Report Preferences",
                "met": bool(output_prefs),
                "value": self._format_output_preferences_summary(output_prefs),
                "icon": "✅" if output_prefs else "⚙️",
            },
        ]

        met_count = sum(1 for c in criteria if c["met"])

        return {
            "criteria": criteria,
            "confidence_score": confidence,
            "confidence_threshold": 75,
            "confidence_met": confidence >= 75,
            "criteria_met_count": met_count,
            "criteria_total_count": len(criteria),
            "missing_information": intent.get("missing_information", []),
            "assumptions": intent.get("assumptions", []),
            "research_questions": intent.get("research_questions", []),
            "output_preferences": output_prefs,
            "ready_to_proceed": confidence >= 75 and met_count >= 5,
        }

    def _format_output_preferences_summary(self, prefs: Dict[str, Any]) -> str:
        """Format output preferences for display."""
        if not prefs:
            return "Using defaults (customizable)"

        parts = []
        if prefs.get("report_length"):
            parts.append(prefs["report_length"])
        if prefs.get("audience"):
            parts.append(f"for {prefs['audience']}")
        if prefs.get("format_style"):
            parts.append(f"{prefs['format_style']} style")
        if prefs.get("include_visuals"):
            parts.append("+ visuals")

        return ", ".join(parts) if parts else "Using defaults"

    def _generate_clarification_questions(
        self,
        intent: Dict[str, Any],
        round_num: int
    ) -> List[str]:
        """Generate clarification questions based on missing information."""
        questions = []
        missing_info = intent.get("missing_information", [])

        # Generate questions based on what's missing
        if not intent.get("research_type"):
            questions.append(
                "What type of research are you looking for? (e.g., comparison, analysis, pros/cons evaluation)"
            )

        if not intent.get("scope"):
            questions.append(
                "How broad or specific should this research be? (broad overview / specific focus / detailed deep-dive)"
            )

        if not intent.get("key_entities") or len(intent.get("key_entities", [])) == 0:
            questions.append(
                "What are the main subjects, products, or concepts you want to research?"
            )

        if not intent.get("decision_criteria") or len(intent.get("decision_criteria", [])) == 0:
            questions.append(
                "What factors matter most to you in this research? (e.g., cost, quality, performance, safety)"
            )

        # Add questions from missing_information
        for missing in missing_info[:2]:  # Limit to 2 from missing_info
            if missing and len(questions) < 4:
                questions.append(f"Could you clarify: {missing}?")

        # If still no questions, generate a general one
        if not questions:
            questions.append(
                "Is there any additional context or constraints I should consider for this research?"
            )

        return questions[:3]  # Return max 3 questions

    def _build_enriched_query(
        self,
        original_query: str,
        user_response: str,
        state: Dict[str, Any]
    ) -> str:
        """Build enriched query incorporating user's clarification."""
        questions = state.get("clarification_questions", [])

        enriched = f"""Original research request: {original_query}

Additional clarification from user:
{user_response}
"""

        if questions:
            enriched += f"""
This was in response to the following clarification questions:
{chr(10).join(f'- {q}' for q in questions)}
"""

        return enriched


# Export the human input agent
human_input_agent = HumanInputAgent()
