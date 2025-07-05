"""
Intent Analyzer for understanding user research requests.

This module analyzes user queries to understand their intent, required information,
and generates follow-up questions for clarification.
"""

import json
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
        
        # If user has provided responses, assume clarification is complete and proceed
        if user_responses and len(user_responses) > 0:
            # Incorporate user responses into the analysis
            intent_analysis = await self._perform_intent_analysis_with_responses(context)
            return {
                "needs_clarification": False,
                "intent": intent_analysis,
                "confidence": intent_analysis.get("confidence", 80),
                "research_questions": intent_analysis.get("research_questions", [query]),
                "key_entities": intent_analysis.get("key_entities", []),
                "domain": intent_analysis.get("domain", "general"),
                "scope": intent_analysis.get("scope", "broad")
            }
        
        # Analyze the intent for first time
        intent_analysis = await self._perform_intent_analysis(context)
        
        # Determine if we need clarification
        needs_clarification = await self._needs_clarification(intent_analysis)
        
        if needs_clarification:
            questions = await self._generate_clarifying_questions(intent_analysis)
            return {
                "needs_clarification": True,
                "questions": questions,
                "partial_intent": intent_analysis,
                "confidence": intent_analysis.get("confidence", 0)
            }
        
        return {
            "needs_clarification": False,
            "intent": intent_analysis,
            "confidence": intent_analysis.get("confidence", 100),
            "research_questions": intent_analysis.get("research_questions", [query]),
            "key_entities": intent_analysis.get("key_entities", []),
            "domain": intent_analysis.get("domain", "general"),
            "scope": intent_analysis.get("scope", "broad")
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
        8. confidence: Confidence in this analysis (0-100)
        
        For food/breakfast research, focus on nutritional value, health benefits, convenience, and general recommendations.
        """
        
        response = await self.gemini_client.generate_response(prompt)
        try:
            return json.loads(response)
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
        8. confidence: Confidence in this analysis (0-100)
        9. missing_information: What key information is still needed
        
        Example:
        {{
            "research_type": "comparison",
            "domain": "automotive",
            "scope": "specific",
            "key_entities": ["Tesla", "Toyota", "market share"],
            "research_questions": ["What is Tesla's market share vs Toyota?"],
            "context_requirements": ["geographic scope", "time period"],
            "output_preferences": ["comparison table", "visual charts"],
            "confidence": 60,
            "missing_information": ["specific geographic region", "exact time period"]
        }}
        """
        
        response = await self.gemini_client.generate_response(prompt)
        try:
            return json.loads(response)
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
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback to simple questions
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
    
    async def get_intent_confidence(self, intent_analysis: Dict[str, Any]) -> float:
        """Get confidence score for intent analysis."""
        return float(intent_analysis.get("confidence", 0)) / 100.0
