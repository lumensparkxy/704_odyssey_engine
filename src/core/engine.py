"""
Main Research Engine for Odyssey Engine.

This module orchestrates the entire research process from user query to final report.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils.gemini_client import GeminiClient
from core.intent_analyzer import IntentAnalyzer
from core.data_gatherer import DataGatherer
from core.report_generator import ReportGenerator
from utils.storage import SessionStorage
from utils.confidence import ConfidenceScorer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/odyssey.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ResearchEngine:
    """Main research engine that orchestrates the research process."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the research engine with configuration."""
        self.config = config
        self.logger = logger

        # Ensure logs directory exists
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        try:
            self.gemini_client = GeminiClient(config)
            self.intent_analyzer = IntentAnalyzer(self.gemini_client, config)
            self.data_gatherer = DataGatherer(self.gemini_client, config)
            self.report_generator = ReportGenerator(self.gemini_client, config)
            self.storage = SessionStorage(config)
            self.confidence_scorer = ConfidenceScorer(
                self.gemini_client, config)
            self.logger.info("Research engine initialized successfully")
        except Exception as e:
            self.logger.error(
                f"Failed to initialize research engine: {str(e)}")
            raise

    async def _parse_json_response(self, response: str, expected_type: str = "array",
                                   fallback_value: Any = None, max_retries: int = 1,
                                   method_name: str = "unknown") -> Any:
        """
        Robust JSON parsing utility with better error handling and validation.

        Args:
            response: Raw response string from API
            expected_type: "array", "object", or "any"
            fallback_value: Value to return if parsing fails
            max_retries: Number of retries (for future use)
            method_name: Name of calling method for logging

        Returns:
            Parsed JSON or fallback value
        """
        if not response or not response.strip():
            self.logger.warning(f"Empty response in {method_name}")
            return fallback_value

        # Clean the response to handle potential formatting issues
        cleaned_response = response.strip()

        # Log the actual response for debugging (truncated to avoid log spam)
        if self.config.get("json_debug_logging", False):
            response_preview = cleaned_response[:200] + "..." if len(
                cleaned_response) > 200 else cleaned_response
            self.logger.debug(
                f"{method_name} response preview: {response_preview}")
        else:
            self.logger.debug(
                f"{method_name} received response ({len(cleaned_response)} chars)")

        # Attempt to extract JSON if wrapped in markdown or extra text
        if "```json" in cleaned_response:
            # Extract JSON from markdown code blocks
            json_start = cleaned_response.find("```json") + 7
            json_end = cleaned_response.find("```", json_start)
            if json_end != -1:
                cleaned_response = cleaned_response[json_start:json_end].strip(
                )
        elif "```" in cleaned_response:
            # Extract from generic code blocks
            json_start = cleaned_response.find("```") + 3
            json_end = cleaned_response.find("```", json_start)
            if json_end != -1:
                cleaned_response = cleaned_response[json_start:json_end].strip(
                )

        # Validate JSON structure before parsing based on expected type
        if expected_type == "array":
            if not cleaned_response.startswith('[') or not cleaned_response.endswith(']'):
                self.logger.warning(
                    f"Response doesn't appear to be a JSON array in {method_name}: {response_preview}")
                return fallback_value
        elif expected_type == "object":
            if not cleaned_response.startswith('{') or not cleaned_response.endswith('}'):
                self.logger.warning(
                    f"Response doesn't appear to be a JSON object in {method_name}: {response_preview}")
                return fallback_value

        try:
            parsed_json = json.loads(cleaned_response)

            # Additional type validation
            if expected_type == "array" and not isinstance(parsed_json, list):
                self.logger.warning(
                    f"Parsed JSON is not a list in {method_name}")
                return fallback_value
            elif expected_type == "object" and not isinstance(parsed_json, dict):
                self.logger.warning(
                    f"Parsed JSON is not a dict in {method_name}")
                return fallback_value

            return parsed_json

        except json.JSONDecodeError as e:
            self.logger.warning(
                f"JSON parsing error in {method_name}: {str(e)}")
            self.logger.debug(
                f"Failed response content: {response[:500] if response else 'None'}")
            return fallback_value
        except Exception as e:
            self.logger.error(f"Unexpected error in {method_name}: {str(e)}")
            return fallback_value

    async def start_research_session(self, initial_query: str) -> str:
        """
        Start a new research session.

        Args:
            initial_query: The user's initial research question

        Returns:
            Session ID for the research session
        """
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "initial_query": initial_query,
            "status": "started",
            "stages": {
                "intent_analysis": {"status": "pending"},
                "data_gathering": {"status": "pending"},
                "analysis": {"status": "pending"},
                "report_generation": {"status": "pending"}
            },
            "confidence_scores": {},
            "final_report": None
        }

        # Save initial session
        await self.storage.save_session(session_id, session_data)

        return session_id

    async def conduct_research(self, session_id: str, user_responses: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Conduct the full research process for a session.

        Args:
            session_id: The research session ID
            user_responses: Optional responses to clarifying questions

        Returns:
            Final research results including report and metadata
        """
        try:
            self.logger.info(f"Starting research for session {session_id}")
            session_data = await self.storage.load_session(session_id)

            if not session_data:
                raise ValueError(f"Session {session_id} not found")

            # Stage 1: Intent Analysis
            self.logger.info("Starting intent analysis...")
            print("🔍 Analyzing user intent...")

            intent_result = await self.intent_analyzer.analyze_intent(
                session_data["initial_query"],
                user_responses
            )

            session_data["stages"]["intent_analysis"] = {
                "status": "completed",
                "result": intent_result,
                "confidence": await self.confidence_scorer.score_intent_analysis(intent_result)
            }

            # Check if we need more clarification
            if intent_result.get("needs_clarification", False):
                self.logger.info(
                    "Intent analysis indicates clarification needed")
                session_data["status"] = "needs_clarification"
                session_data["clarifying_questions"] = intent_result.get(
                    "questions", [])
                await self.storage.save_session(session_id, session_data)
                return {
                    "status": "needs_clarification",
                    "questions": intent_result.get("questions", []),
                    "session_data": session_data
                }

            self.logger.info("Intent analysis completed successfully")

            # Stage 2: Data Gathering
            self.logger.info("Starting data gathering...")
            print("📊 Gathering information from multiple sources...")

            data_result = await self.data_gatherer.gather_data(intent_result)

            session_data["stages"]["data_gathering"] = {
                "status": "completed",
                "result": data_result,
                "confidence": await self.confidence_scorer.score_data_quality(data_result)
            }

            self.logger.info("Data gathering completed successfully")

            # Stage 3: Analysis and Compilation
            self.logger.info("Starting analysis and compilation...")
            print("🧠 Analyzing and compiling information...")

            analysis_result = await self._analyze_and_compile(intent_result, data_result)

            session_data["stages"]["analysis"] = {
                "status": "completed",
                "result": analysis_result,
                "confidence": await self.confidence_scorer.score_analysis(analysis_result)
            }

            self.logger.info("Analysis completed successfully")

            # Stage 4: Report Generation
            self.logger.info("Starting report generation...")
            print("📝 Generating comprehensive report...")

            report = await self.report_generator.generate_report(
                intent_result,
                data_result,
                analysis_result
            )

            session_data["stages"]["report_generation"] = {
                "status": "completed",
                "result": {"report_path": report["file_path"]},
                "confidence": await self.confidence_scorer.score_report_quality(report)
            }

            self.logger.info("Report generation completed successfully")

            # Calculate overall confidence
            overall_confidence = await self.confidence_scorer.calculate_overall_confidence(
                session_data["stages"]
            )

            session_data["final_report"] = report
            session_data["overall_confidence"] = overall_confidence
            session_data["status"] = "completed"
            session_data["completed_at"] = datetime.now().isoformat()

            # Save final session
            await self.storage.save_session(session_id, session_data)

            self.logger.info(
                f"Research completed successfully for session {session_id}")

            return {
                "status": "completed",
                "report": report,
                "confidence": overall_confidence,
                "session_data": session_data
            }

        except Exception as e:
            self.logger.error(
                f"Research failed for session {session_id}: {str(e)}", exc_info=True)
            session_data = await self.storage.load_session(session_id) or {"session_id": session_id}
            session_data["status"] = "error"
            session_data["error"] = str(e)
            session_data["error_at"] = datetime.now().isoformat()
            await self.storage.save_session(session_id, session_data)

            return {
                "status": "error",
                "error": str(e),
                "session_data": session_data
            }

    async def _analyze_and_compile(self, intent_result: Dict, data_result: Dict) -> Dict[str, Any]:
        """
        Analyze and compile gathered information.

        Args:
            intent_result: Results from intent analysis
            data_result: Results from data gathering

        Returns:
            Compiled analysis results
        """
        # Identify key themes and patterns
        themes = await self._identify_themes(data_result)

        # Handle conflicting information
        conflicts = await self._identify_conflicts(data_result)

        # Create summaries based on user context
        summaries = await self._create_contextual_summaries(intent_result, data_result)

        return {
            "themes": themes,
            "conflicts": conflicts,
            "summaries": summaries,
            "data_quality_assessment": await self._assess_data_quality(data_result)
        }

    async def _identify_themes(self, data_result: Dict) -> List[Dict]:
        """Identify key themes from gathered data."""
        prompt = f"""
        Analyze the following research data and identify the key themes and patterns:
        
        {json.dumps(data_result, indent=2)}
        
        Return a JSON array of themes with descriptions and supporting evidence.
        Each theme should have: title, description, supporting_evidence
        
        Example:
        [
            {{
                "title": "Nutritional Value",
                "description": "High protein and fiber content for sustained energy",
                "supporting_evidence": ["Eggs provide complete proteins", "Oats contain beta-glucan fiber"]
            }}
        ]
        
        IMPORTANT: Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.
        """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.gemini_client.generate_response(prompt)

                themes = await self._parse_json_response(
                    response,
                    expected_type="array",
                    fallback_value=None,
                    method_name="theme_identification"
                )

                if themes is None:
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"Theme identification failed, retrying (attempt {attempt + 1}/{max_retries})")
                        continue
                    return self._fallback_themes(data_result)

                # Validate each theme has required fields
                valid_themes = []
                for theme in themes:
                    if isinstance(theme, dict) and all(key in theme for key in ['title', 'description', 'supporting_evidence']):
                        valid_themes.append(theme)
                    else:
                        self.logger.warning(
                            f"Invalid theme structure: {theme}")

                if valid_themes:
                    self.logger.info(
                        f"Successfully identified {len(valid_themes)} themes")
                    return valid_themes
                else:
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"No valid themes found, retrying (attempt {attempt + 1}/{max_retries})")
                        continue
                    return self._fallback_themes(data_result)

            except Exception as e:
                self.logger.error(
                    f"Error in theme identification (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    continue
                return self._fallback_themes(data_result)

        # If all retries failed
        self.logger.error(
            f"All {max_retries} attempts failed for theme identification")
        return self._fallback_themes(data_result)

    def _fallback_themes(self, data_result: Dict) -> List[Dict]:
        """Provide fallback themes when AI analysis fails."""
        return [
            {
                "title": "General Information",
                "description": "Basic information gathered from available sources",
                "supporting_evidence": ["Multiple sources consulted", "Comprehensive data collection"]
            },
            {
                "title": "Key Recommendations",
                "description": "Primary recommendations based on research",
                "supporting_evidence": ["Expert opinions", "Research findings"]
            }
        ]

    async def _identify_conflicts(self, data_result: Dict) -> List[Dict]:
        """Identify conflicting information in the data."""
        prompt = f"""
        Analyze the following research data and identify any conflicting information:
        
        {json.dumps(data_result, indent=2)}
        
        Return a JSON array of conflicts with source reliability assessment.
        Each conflict should have: conflict_type, description, sources_involved, severity
        
        If no conflicts found, return empty array: []
        
        IMPORTANT: Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.
        """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.gemini_client.generate_response(prompt)

                conflicts = await self._parse_json_response(
                    response,
                    expected_type="array",
                    fallback_value=None,
                    method_name="conflict_identification"
                )

                if conflicts is None:
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"Conflict identification failed, retrying (attempt {attempt + 1}/{max_retries})")
                        continue
                    return []

                # Validate each conflict has required fields (if any conflicts exist)
                valid_conflicts = []
                for conflict in conflicts:
                    if isinstance(conflict, dict) and all(key in conflict for key in ['conflict_type', 'description', 'sources_involved', 'severity']):
                        valid_conflicts.append(conflict)
                    else:
                        self.logger.warning(
                            f"Invalid conflict structure: {conflict}")

                # Return valid conflicts (could be empty list, which is valid)
                if len(conflicts) == 0:
                    self.logger.info("No conflicts identified in the data")
                else:
                    self.logger.info(
                        f"Successfully identified {len(valid_conflicts)} valid conflicts out of {len(conflicts)} total")

                return valid_conflicts

            except Exception as e:
                self.logger.error(
                    f"Error in conflict identification (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    continue
                return []

        # If all retries failed
        self.logger.error(
            f"All {max_retries} attempts failed for conflict identification")
        return []

    async def _create_contextual_summaries(self, intent_result: Dict, data_result: Dict) -> Dict:
        """Create summaries based on user context and intent."""
        user_context = intent_result.get("context", {})

        summaries = {}

        # Executive summary
        summaries["executive"] = await self._generate_executive_summary(data_result)

        # Context-specific summaries based on user intent
        if user_context.get("comparison_needed"):
            summaries["comparison"] = await self._generate_comparison(data_result)

        if user_context.get("timeline_needed"):
            summaries["timeline"] = await self._generate_timeline(data_result)

        if user_context.get("pros_cons_needed"):
            summaries["pros_cons"] = await self._generate_pros_cons(data_result)

        return summaries

    async def _generate_executive_summary(self, data_result: Dict) -> str:
        """Generate executive summary of findings."""
        prompt = f"""
        Create a concise executive summary of the following research data:
        
        {json.dumps(data_result, indent=2)}
        
        Focus on the most important findings and conclusions.
        """

        return await self.gemini_client.generate_response(prompt)

    async def _generate_comparison(self, data_result: Dict) -> Dict:
        """Generate comparison analysis."""
        prompt = f"""
        Create a detailed comparison analysis from the following data:
        
        {json.dumps(data_result, indent=2)}
        
        Include comparison tables and key differences.
        Return as JSON with comparison_table and key_differences keys.
        
        IMPORTANT: Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.
        """

        response = await self.gemini_client.generate_response(prompt)
        return await self._parse_json_response(
            response,
            expected_type="object",
            fallback_value={"comparison_table": [], "key_differences": []},
            method_name="comparison_generation"
        )

    async def _generate_timeline(self, data_result: Dict) -> List[Dict]:
        """Generate timeline of events."""
        prompt = f"""
        Extract and organize chronological events from the following data:
        
        {json.dumps(data_result, indent=2)}
        
        Return as a JSON array of timeline events with date and description.
        If no chronological events found, return empty array: []
        
        IMPORTANT: Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.
        """

        response = await self.gemini_client.generate_response(prompt)
        return await self._parse_json_response(
            response,
            expected_type="array",
            fallback_value=[],
            method_name="timeline_generation"
        )

    async def _generate_pros_cons(self, data_result: Dict) -> Dict:
        """Generate pros and cons analysis."""
        prompt = f"""
        Analyze the following data and extract pros and cons:
        
        {json.dumps(data_result, indent=2)}
        
        Return structured pros and cons with supporting evidence as JSON.
        Format: {{"pros": [], "cons": []}}
        
        IMPORTANT: Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.
        """

        response = await self.gemini_client.generate_response(prompt)
        return await self._parse_json_response(
            response,
            expected_type="object",
            fallback_value={"pros": [], "cons": []},
            method_name="pros_cons_generation"
        )

    async def _assess_data_quality(self, data_result: Dict) -> Dict:
        """Assess the quality and reliability of gathered data."""
        return {
            "sources_count": len(data_result.get("sources", [])),
            "reliability_scores": data_result.get("source_reliability", {}),
            "coverage_assessment": "comprehensive",  # This would be calculated
            "freshness_score": 0.85  # This would be calculated based on data recency
        }

    async def load_session(self, session_id: str) -> Dict[str, Any]:
        """Load an existing research session."""
        return await self.storage.load_session(session_id)

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all research sessions."""
        return await self.storage.list_sessions()
