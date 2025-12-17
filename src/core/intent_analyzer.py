"""
Intent Analyzer for understanding user research requests.

This module analyzes user queries to understand their intent, required information,
and generates follow-up questions for clarification.
"""

import json
import re
from typing import Dict, List, Optional, Any

from utils.gemini_client import GeminiClient


class IntentAnalyzer:
    """Analyzes user intent and generates clarifying questions."""

    def __init__(self, gemini_client: GeminiClient, config: Dict[str, Any]):
        """Initialize the intent analyzer."""
        self.gemini_client = gemini_client
        self.config = config
        self.confidence_threshold = config.get("CONFIDENCE_THRESHOLD", 75)
        self.max_follow_up_questions = config.get("MAX_FOLLOW_UP_QUESTIONS", 5)
        self.force_clarification_on_uncertainty = bool(
            config.get("FORCE_CLARIFICATION_ON_UNCERTAINTY", True)
        )

    async def analyze_intent(self, query: str, user_responses: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze user intent and determine if clarification is needed.

        Args:
            query: The user's research query
            user_responses: Optional responses to previous clarifying questions

        Returns:
            Intent analysis result with clarification needs
        """
        # Build context from previous responses
        context = self._build_context(query, user_responses)

        # If user has provided responses, incorporate them but still check confidence
        if user_responses and len(user_responses) > 0:
            # Incorporate user responses into the analysis
            intent_analysis = await self._perform_intent_analysis_with_responses(context)

            # Even with responses, we must check if confidence meets threshold
            confidence = intent_analysis.get("confidence", 80)
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                confidence_value = 80

            # If still below threshold after user responses, flag it but let engine decide
            # The engine's validation will be the final gate
            needs_more_clarification = confidence_value < self.confidence_threshold

            return {
                "needs_clarification": needs_more_clarification,
                "questions": await self._generate_clarifying_questions(intent_analysis) if needs_more_clarification else [],
                "intent": intent_analysis,
                "context": self._derive_context(intent_analysis),
                "confidence": confidence_value,
                "research_questions": intent_analysis.get("research_questions", [query]),
                "key_entities": intent_analysis.get("key_entities", []),
                "domain": intent_analysis.get("domain", "general"),
                "scope": intent_analysis.get("scope", "broad"),
                "decision_criteria": intent_analysis.get("decision_criteria", []),
                "success_criteria": intent_analysis.get("success_criteria", []),
                "user_responses_provided": True  # Flag to indicate user already answered
            }

        # Analyze the intent for first time
        intent_analysis = await self._perform_intent_analysis(context)

        # If the user explicitly signals uncertainty, be stricter about asking questions.
        # This prevents "fast intent" runs where the model returns high confidence but the
        # user clearly asked us to clarify constraints.
        if (not user_responses) and self.force_clarification_on_uncertainty:
            intent_analysis = self._apply_uncertainty_heuristics(
                query, intent_analysis)

        # Determine if we need clarification
        needs_clarification = await self._needs_clarification(intent_analysis)

        if needs_clarification:
            questions = await self._generate_clarifying_questions(intent_analysis)
            return {
                "needs_clarification": True,
                "questions": questions,
                "partial_intent": intent_analysis,
                "context": self._derive_context(intent_analysis),
                "confidence": intent_analysis.get("confidence", 0),
                "decision_criteria": intent_analysis.get("decision_criteria", []),
                "success_criteria": intent_analysis.get("success_criteria", []),
                "missing_information": intent_analysis.get("missing_information", [])
            }

        return {
            "needs_clarification": False,
            "intent": intent_analysis,
            "context": self._derive_context(intent_analysis),
            "confidence": intent_analysis.get("confidence", 100),
            "research_questions": intent_analysis.get("research_questions", [query]),
            "key_entities": intent_analysis.get("key_entities", []),
            "domain": intent_analysis.get("domain", "general"),
            "scope": intent_analysis.get("scope", "broad"),
            "decision_criteria": intent_analysis.get("decision_criteria", []),
            "success_criteria": intent_analysis.get("success_criteria", [])
        }

    def _build_context(self, query: str, user_responses: Optional[Dict] = None) -> Dict[str, Any]:
        """Build context from query and user responses."""
        context = {
            "original_query": query,
            "user_responses": user_responses or {},
            "conversation_history": []
        }

        if user_responses:
            for question, answer in user_responses.items():
                context["conversation_history"].append({
                    "question": question,
                    "answer": answer
                })

        return context

    async def _perform_intent_analysis_with_responses(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform intent analysis incorporating user responses."""
        prompt = f"""
        Analyze the following research query with user-provided clarifications:
        
        Original Query: {context['original_query']}
        
        User Clarifications:
        {json.dumps(context.get('conversation_history', []), indent=2)}
        
        Based on the original query and the user's clarifications, provide a comprehensive intent analysis.
        Even if the user said "unknown" to some questions, use your best judgment to proceed with the research.
        
        Return a JSON response with:
        1. research_type: (comparison, analysis, timeline, pros_cons, general_research)
        2. domain: The subject domain (food, nutrition, health, etc.)
        3. scope: (broad, specific, detailed)
        4. key_entities: List of main entities/subjects to research
        5. research_questions: Specific questions to answer based on the original query
        6. context_requirements: What context is needed (can be empty if sufficient info provided)
        7. output_preferences: How to present the information
        8. decision_criteria: List of criteria to use for decisions (e.g., cost, latency, quality, risk)
        9. success_criteria: List of what “good” looks like for the user / project
        10. confidence: Confidence in this analysis (0-100)
        
        For food/breakfast research, focus on nutritional value, health benefits, convenience, and general recommendations.
        """

        # Use grounding to ensure the model knows about recent entities/models
        result = await self.gemini_client.generate_with_grounding(prompt)
        response = result["response"]

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code blocks
            try:
                json_match = re.search(
                    r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1).strip()
                    return json.loads(json_content)

                # If no code blocks, try cleaning common markdown artifacts
                cleaned_response = response.strip()
                if cleaned_response.startswith('```') and cleaned_response.endswith('```'):
                    lines = cleaned_response.split('\n')
                    if len(lines) > 2:
                        cleaned_response = '\n'.join(lines[1:-1])

                return json.loads(cleaned_response)
            except json.JSONDecodeError:
                # Fallback intent analysis
                return {
                    "research_type": "general_research",
                    "domain": "nutrition",
                    "scope": "broad",
                    "key_entities": [context['original_query']],
                    "research_questions": [f"What are the best options for: {context['original_query']}?"],
                    "context_requirements": [],
                    "output_preferences": ["comprehensive_report"],
                    "confidence": 70
                }

    async def _perform_intent_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the core intent analysis."""
        prompt = f"""
        Analyze the following research query and context to understand the user's intent:
        
        Original Query: {context['original_query']}
        
        Previous Conversation:
        {json.dumps(context.get('conversation_history', []), indent=2)}
        
        Please analyze and return a JSON response with:
        1. research_type: (comparison, analysis, timeline, pros_cons, general_research)
        2. domain: The subject domain (technology, finance, science, etc.)
        3. scope: (broad, specific, detailed)
        4. key_entities: List of main entities/subjects to research
        5. research_questions: Specific questions to answer
        6. context_requirements: What context is needed
        7. output_preferences: How the user likely wants the information presented
        8. decision_criteria: List of criteria to use for decisions (e.g., cost, latency, quality, risk)
        9. success_criteria: List of what “good” looks like for the user / project
        10. confidence: Confidence in this analysis (0-100)
        11. missing_information: What key information is still needed
        
        IMPORTANT: Use Google Search to verify if any mentioned entities (like model versions, products, events) exist, even if they are very recent. Do not assume they are hypothetical without checking.
        
        Example:
        {{
            "research_type": "comparison",
            "domain": "automotive",
            "scope": "specific",
            "key_entities": ["Tesla", "Toyota", "market share"],
            "research_questions": ["What is Tesla's market share vs Toyota?"],
            "context_requirements": ["geographic scope", "time period"],
            "output_preferences": ["comparison table", "visual charts"],
            "decision_criteria": ["cost", "range", "charging availability"],
            "success_criteria": ["clear recommendation", "sources cited", "covers latest year"],
            "confidence": 60,
            "missing_information": ["specific geographic region", "exact time period"]
        }}
        """

        # Use grounding to ensure the model knows about recent entities/models
        result = await self.gemini_client.generate_with_grounding(prompt)
        response = result["response"]

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code blocks
            try:
                import re
                json_match = re.search(
                    r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1).strip()
                    return json.loads(json_content)

                # If no code blocks, try cleaning common markdown artifacts
                cleaned_response = response.strip()
                if cleaned_response.startswith('```') and cleaned_response.endswith('```'):
                    lines = cleaned_response.split('\n')
                    if len(lines) > 2:
                        cleaned_response = '\n'.join(lines[1:-1])

                return json.loads(cleaned_response)
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                return self._parse_fallback_response(response, context)

    async def _needs_clarification(self, intent_analysis: Dict[str, Any]) -> bool:
        """Determine if clarification is needed based on confidence and missing info."""
        confidence = intent_analysis.get("confidence", 0)
        missing_info = intent_analysis.get("missing_information", [])

        # Need clarification if confidence is low or critical info is missing
        if confidence < self.confidence_threshold:
            return True

        if len(missing_info) > 0:
            # Check if missing information is critical
            critical_missing = await self._assess_critical_missing_info(intent_analysis, missing_info)
            return critical_missing

        return False

    def _apply_uncertainty_heuristics(self, query: str, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristics to request clarification when the user explicitly says they're unsure.

        We only *nudge* the model's output; we don't attempt to fully rewrite it.
        """
        if not isinstance(intent_analysis, dict):
            return intent_analysis

        q = (query or "").lower()
        uncertainty_markers = (
            "not sure",
            "i'm not sure",
            "im not sure",
            "unsure",
            "don't know",
            "dont know",
            "ask me what you need",
            "ask me what you need.",
            "unknown",
        )

        if not any(m in q for m in uncertainty_markers):
            return intent_analysis

        missing_information = intent_analysis.get("missing_information")
        if not isinstance(missing_information, list):
            missing_information = []

        # If the model didn't include missing info, add the common blockers for "decision" queries.
        if len(missing_information) == 0:
            missing_information.extend(
                [
                    "constraints (latency, cost, throughput)",
                    "success criteria / definition of done",
                    "deployment context (users, traffic, data freshness needs)",
                ]
            )

        # If criteria fields are missing/empty, treat them as missing.
        decision_criteria = intent_analysis.get("decision_criteria", [])
        if not isinstance(decision_criteria, list) or len(decision_criteria) == 0:
            missing_information.append(
                "decision criteria (cost, latency, quality, risk)")

        success_criteria = intent_analysis.get("success_criteria", [])
        if not isinstance(success_criteria, list) or len(success_criteria) == 0:
            missing_information.append("success criteria")

        # Force clarification by nudging confidence below threshold.
        try:
            conf = int(intent_analysis.get("confidence", 0))
        except Exception:
            conf = 0
        intent_analysis["confidence"] = min(
            conf, int(self.confidence_threshold) - 1)
        intent_analysis["missing_information"] = list(
            dict.fromkeys(missing_information))

        return intent_analysis

    async def _assess_critical_missing_info(self, intent_analysis: Dict, missing_info: List[str]) -> bool:
        """Assess if missing information is critical for research."""
        prompt = f"""
        Given this research intent analysis:
        {json.dumps(intent_analysis, indent=2)}
        
        And this missing information:
        {missing_info}
        
        Determine if the missing information is critical for conducting effective research.
        Consider:
        - Can research proceed without this information?
        - Would the results be significantly less valuable?
        - Is this information readily available through search?
        
        Return only "true" if critical clarification is needed, "false" otherwise.
        """

        response = await self.gemini_client.generate_response(prompt)
        return response.strip().lower() == "true"

    async def _generate_clarifying_questions(self, intent_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate clarifying questions based on intent analysis."""
        missing_info = intent_analysis.get("missing_information", [])
        research_type = intent_analysis.get("research_type", "general")

        prompt = f"""
        Generate clarifying questions to gather missing information for this research:
        
        Intent Analysis:
        {json.dumps(intent_analysis, indent=2)}
        
        Missing Information:
        {missing_info}
        
        Generate {min(len(missing_info), self.max_follow_up_questions)} clear, specific questions that will help gather the missing information.
        
        Each question should:
        1. Be easy to understand
        2. Have a clear purpose
        3. Include examples or options when helpful
        4. Allow for "I don't know" responses
        
        Return as JSON array with objects containing:
        - question: The question text
        - purpose: Why this information is needed
        - examples: Example answers (optional)
        - allow_unknown: Whether "I don't know" is acceptable
        
        Example:
        [
            {{
                "question": "What specific time period are you interested in? (e.g., 2023, last 5 years, current)",
                "purpose": "To focus the research on relevant timeframe",
                "examples": ["2023 only", "2020-2023", "most recent data"],
                "allow_unknown": true
            }}
        ]
        """

        response = await self.gemini_client.generate_response(prompt)
        try:
            # Try parsing the response as-is first
            return json.loads(response)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code blocks
            try:
                # Look for JSON wrapped in ```json ... ``` or ``` ... ```
                import re
                json_match = re.search(
                    r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1).strip()
                    return json.loads(json_content)

                # If no code blocks, try cleaning common markdown artifacts
                cleaned_response = response.strip()
                if cleaned_response.startswith('```') and cleaned_response.endswith('```'):
                    # Remove outer code block markers
                    lines = cleaned_response.split('\n')
                    if len(lines) > 2:
                        cleaned_response = '\n'.join(lines[1:-1])

                return json.loads(cleaned_response)
            except json.JSONDecodeError:
                # Final fallback to simple questions
                return self._generate_fallback_questions(missing_info)

    def _parse_fallback_response(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse response when JSON parsing fails."""
        return {
            "research_type": "general_research",
            "domain": "unknown",
            "scope": "broad",
            "key_entities": [context["original_query"]],
            "research_questions": [context["original_query"]],
            "context_requirements": ["scope", "timeframe"],
            "output_preferences": ["comprehensive_report"],
            "confidence": 30,
            "missing_information": ["specific scope", "preferred timeframe"]
        }

    def _generate_fallback_questions(self, missing_info: List[str]) -> List[Dict[str, str]]:
        """Generate fallback questions when AI generation fails."""
        questions = []

        for info in missing_info[:self.max_follow_up_questions]:
            questions.append({
                "question": f"Can you provide more details about: {info}?",
                "purpose": f"To clarify {info}",
                "examples": [],
                "allow_unknown": True
            })

        return questions

    def _derive_context(self, intent_analysis: Dict[str, Any]) -> Dict[str, bool]:
        """Derive context flags from intent analysis."""
        research_type = intent_analysis.get("research_type", "general")
        output_preferences = intent_analysis.get("output_preferences", [])

        return {
            "comparison_needed": research_type == "comparison" or "comparison" in output_preferences,
            "timeline_needed": research_type == "timeline" or "timeline" in output_preferences,
            "pros_cons_needed": research_type == "pros_cons" or "pros_cons" in output_preferences,
            "detailed_report": "detailed" in intent_analysis.get("scope", "broad")
        }

    async def get_intent_confidence(self, intent_analysis: Dict[str, Any]) -> float:
        """Get confidence score for intent analysis."""
        return float(intent_analysis.get("confidence", 0)) / 100.0
