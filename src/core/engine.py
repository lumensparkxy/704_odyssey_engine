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
        response_preview = cleaned_response[:200] + "..." if len(
            cleaned_response) > 200 else cleaned_response

        if self.config.get("json_debug_logging", False):
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

            # Validate Stage 1 output before persisting / proceeding
            self._validate_intent_result(intent_result)

            intent_confidence = await self.confidence_scorer.score_intent_analysis(intent_result)
            session_data["stages"]["intent_analysis"] = {
                "status": "completed",
                "result": intent_result,
                "confidence": intent_confidence
            }

            # Check if we need more clarification (either explicitly requested OR confidence below threshold)
            needs_clarification = intent_result.get(
                "needs_clarification", False)

            # CONFIDENCE GATING: Force clarification if confidence is below threshold
            confidence_threshold = self.config.get("CONFIDENCE_THRESHOLD", 75)
            max_clarification_rounds = self.config.get(
                "MAX_FOLLOW_UP_QUESTIONS", 5)
            intent_confidence_score = intent_result.get("confidence", 0)
            try:
                confidence_value = float(intent_confidence_score)
            except (TypeError, ValueError):
                confidence_value = 0

            # Track clarification rounds
            clarification_round = session_data.get("clarification_round", 0)
            if user_responses:
                clarification_round += 1
                session_data["clarification_round"] = clarification_round

            # Check if we've exhausted clarification attempts
            if clarification_round >= max_clarification_rounds and confidence_value < confidence_threshold:
                self.logger.warning(
                    f"⚠️  MAX CLARIFICATION ROUNDS REACHED ({clarification_round}/{max_clarification_rounds}). "
                    f"Proceeding with confidence {confidence_value}% despite being below threshold ({confidence_threshold}%)."
                )
                # Force proceed - don't ask for more clarification
                needs_clarification = False
                intent_result["needs_clarification"] = False
                intent_result["forced_proceed"] = True
                intent_result["max_clarifications_reached"] = True
            elif not needs_clarification and confidence_value < confidence_threshold:
                self.logger.warning(
                    f"⚠️  CONFIDENCE BELOW THRESHOLD: Intent confidence ({confidence_value}%) "
                    f"is below threshold ({confidence_threshold}%). Round {clarification_round + 1}/{max_clarification_rounds}."
                )
                # Generate clarifying questions based on missing information
                questions = await self._generate_confidence_clarifying_questions(intent_result, confidence_threshold)
                needs_clarification = True
                intent_result["needs_clarification"] = True
                intent_result["questions"] = questions
                intent_result["confidence_gate_triggered"] = True

            if needs_clarification:
                questions = intent_result.get("questions", [])
                self.logger.info(
                    f"Intent analysis indicates clarification needed - "
                    f"{len(questions)} questions generated, confidence: {confidence_value}% "
                    f"(threshold: {confidence_threshold}%), round: {clarification_round + 1}/{max_clarification_rounds}")
                session_data["status"] = "needs_clarification"
                session_data["clarifying_questions"] = questions
                session_data["stages"]["intent_analysis"]["result"] = intent_result
                await self.storage.save_session(session_id, session_data)
                return {
                    "status": "needs_clarification",
                    "questions": questions,
                    "confidence": confidence_value,
                    "confidence_threshold": confidence_threshold,
                    "clarification_round": clarification_round + 1,
                    "max_clarification_rounds": max_clarification_rounds,
                    "session_data": session_data
                }

            # Log detailed intent analysis results
            self._log_intent_analysis_details(intent_result, intent_confidence)

            # Update session status to in_progress as we're now actively researching
            session_data["status"] = "in_progress"
            await self.storage.save_session(session_id, session_data)

            # Stage 2: Data Gathering
            self.logger.info("Starting data gathering...")
            print("")
            print("☕ " + "="*55)
            print("☕  DATA GATHERING STAGE")
            print("☕  This may take 2-5 minutes depending on your query.")
            print("☕  Feel free to grab a coffee! ☕")
            print("☕ " + "="*55)
            print("")
            print("📊 Gathering information from multiple sources...")

            data_result = await self.data_gatherer.gather_data(intent_result)

            # Validate Stage 2 output before persisting / proceeding
            self._validate_data_result(data_result)

            data_confidence = await self.confidence_scorer.score_data_quality(data_result)
            session_data["stages"]["data_gathering"] = {
                "status": "completed",
                "result": data_result,
                "confidence": data_confidence
            }

            # Log detailed data gathering results
            self._log_data_gathering_details(data_result, data_confidence)

            # Stage 3: Analysis and Compilation
            self.logger.info("Starting analysis and compilation...")
            print("")
            print("🧪 " + "="*55)
            print("🧪  ANALYSIS & COMPILATION STAGE")
            print("🧪  Synthesizing information from all sources...")
            print("🧪  This typically takes 1-2 minutes.")
            print("🧪 " + "="*55)
            print("")
            print("🧠 Analyzing and compiling information...")

            analysis_result = await self._analyze_and_compile(intent_result, data_result)

            # Validate Stage 3 output before persisting / proceeding
            self._validate_analysis_result(analysis_result)

            analysis_confidence = await self.confidence_scorer.score_analysis(analysis_result)
            session_data["stages"]["analysis"] = {
                "status": "completed",
                "result": analysis_result,
                "confidence": analysis_confidence
            }

            # Log detailed analysis results
            self._log_analysis_details(analysis_result, analysis_confidence)

            # Stage 4: Report Generation
            self.logger.info("Starting report generation...")
            print("📝 Generating comprehensive report...")

            report = await self.report_generator.generate_report(
                intent_result,
                data_result,
                analysis_result
            )

            # Validate Stage 4 output before persisting / completing
            self._validate_report_result(report)

            report_confidence = await self.confidence_scorer.score_report_quality(report)
            session_data["stages"]["report_generation"] = {
                "status": "completed",
                "result": {"report_path": report["file_path"]},
                "confidence": report_confidence
            }

            # Log detailed report generation results
            self._log_report_generation_details(report, report_confidence)

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

    async def conduct_research_forced(self, session_id: str) -> Dict[str, Any]:
        """
        Force research to proceed even with low confidence.

        This is called when max clarification rounds have been reached.
        It skips the confidence threshold check and proceeds with whatever
        understanding we have.

        Args:
            session_id: The research session ID

        Returns:
            Research results
        """
        self.logger.info(
            f"Force-proceeding research for session {session_id} (max clarifications reached)")

        session_data = await self.storage.load_session(session_id)
        if not session_data:
            return {"status": "error", "error": f"Session {session_id} not found"}

        # Get the latest intent result from session
        intent_stage = session_data.get(
            "stages", {}).get("intent_analysis", {})
        intent_result = intent_stage.get("result", {})

        if not intent_result:
            return {"status": "error", "error": "No intent analysis found in session"}

        # Force needs_clarification to False to proceed
        intent_result["needs_clarification"] = False
        intent_result["forced_proceed"] = True

        # Ensure we have minimum required fields
        if not intent_result.get("research_questions"):
            intent_result["research_questions"] = [
                session_data.get("initial_query", "")]
        if not intent_result.get("domain"):
            intent_result["domain"] = "general"
        if not intent_result.get("key_entities"):
            intent_result["key_entities"] = []

        self.logger.warning(
            f"Forcing research with confidence {intent_result.get('confidence', 'N/A')}% "
            f"(below threshold, but max clarifications reached)"
        )

        # Update session status to in_progress
        session_data["status"] = "in_progress"
        await self.storage.save_session(session_id, session_data)

        try:
            # Stage 2: Data Gathering (skip confidence check)
            self.logger.info("Starting data gathering (forced mode)...")
            print("")
            print("☕ " + "="*55)
            print("☕  DATA GATHERING STAGE (Forced Mode)")
            print("☕  This may take 2-5 minutes depending on your query.")
            print("☕  Feel free to grab a coffee! ☕")
            print("☕ " + "="*55)
            print("")
            print("📊 Gathering information from multiple sources...")

            data_result = await self.data_gatherer.gather_data(intent_result)
            self._validate_data_result(data_result)

            data_confidence = await self.confidence_scorer.score_data_quality(data_result)
            session_data["stages"]["data_gathering"] = {
                "status": "completed",
                "result": data_result,
                "confidence": data_confidence
            }
            self._log_data_gathering_details(data_result, data_confidence)

            # Stage 3: Analysis
            self.logger.info("Starting analysis and compilation...")
            print("")
            print("🧪 " + "="*55)
            print("🧪  ANALYSIS & COMPILATION STAGE")
            print("🧪  Synthesizing information from all sources...")
            print("🧪  This typically takes 1-2 minutes.")
            print("🧪 " + "="*55)
            print("")
            print("🧠 Analyzing and compiling information...")

            analysis_result = await self._analyze_and_compile(intent_result, data_result)
            self._validate_analysis_result(analysis_result)

            analysis_confidence = await self.confidence_scorer.score_analysis(analysis_result)
            session_data["stages"]["analysis"] = {
                "status": "completed",
                "result": analysis_result,
                "confidence": analysis_confidence
            }
            self._log_analysis_details(analysis_result, analysis_confidence)

            # Stage 4: Report Generation
            self.logger.info("Starting report generation...")
            print("")
            print("📄 " + "="*55)
            print("📄  REPORT GENERATION STAGE")
            print("📄  Creating your comprehensive research report...")
            print("📄  Almost there! This takes about 1 minute.")
            print("📄 " + "="*55)
            print("")
            print("📝 Generating comprehensive report...")

            report = await self.report_generator.generate_report(
                intent_result, data_result, analysis_result
            )
            self._validate_report_result(report)

            report_confidence = await self.confidence_scorer.score_report_quality(report)
            session_data["stages"]["report_generation"] = {
                "status": "completed",
                "result": {"report_path": report["file_path"]},
                "confidence": report_confidence
            }
            self._log_report_generation_details(report, report_confidence)

            # Calculate overall confidence
            overall_confidence = await self.confidence_scorer.calculate_overall_confidence(
                session_data["stages"]
            )

            session_data["final_report"] = report
            session_data["overall_confidence"] = overall_confidence
            session_data["status"] = "completed"
            session_data["forced_completion"] = True
            session_data["completed_at"] = datetime.now().isoformat()

            await self.storage.save_session(session_id, session_data)

            self.logger.info(
                f"Research completed (forced) for session {session_id}")

            return {
                "status": "completed",
                "report": report,
                "confidence": overall_confidence,
                "session_data": session_data,
                "forced": True
            }

        except Exception as e:
            self.logger.error(
                f"Forced research failed: {str(e)}", exc_info=True)
            session_data["status"] = "error"
            session_data["error"] = str(e)
            await self.storage.save_session(session_id, session_data)
            return {"status": "error", "error": str(e), "session_data": session_data}

    def _validate_intent_result(self, intent_result: Any) -> None:
        """Validate intent analysis output.

        The engine should not proceed to the next stage if intent analysis is
        missing required structure. Note: Low confidence is NOT an error - 
        it triggers the clarification flow instead.
        """
        if not isinstance(intent_result, dict):
            raise ValueError("intent_analysis result must be a dict")

        if "needs_clarification" not in intent_result:
            raise ValueError(
                "intent_analysis result missing 'needs_clarification'")

        needs_clarification = intent_result.get("needs_clarification")
        if not isinstance(needs_clarification, bool):
            raise ValueError(
                "intent_analysis 'needs_clarification' must be a bool")

        # If we need clarification, we must have at least one question.
        if needs_clarification:
            questions = intent_result.get("questions", [])
            if not isinstance(questions, list) or len(questions) == 0:
                raise ValueError(
                    "intent_analysis requires non-empty 'questions' when clarification is needed")
            return

        # Otherwise, we must have usable research questions to drive the pipeline.
        research_questions = intent_result.get("research_questions")
        if not isinstance(research_questions, list) or not any(isinstance(q, str) and q.strip() for q in research_questions):
            raise ValueError(
                "intent_analysis requires non-empty 'research_questions' when clarification is not needed")

        key_entities = intent_result.get("key_entities", [])
        if key_entities is not None and not isinstance(key_entities, list):
            raise ValueError(
                "intent_analysis 'key_entities' must be a list when provided")

        domain = intent_result.get("domain", "")
        if not isinstance(domain, str) or not domain.strip():
            raise ValueError(
                "intent_analysis 'domain' must be a non-empty string")

    async def _generate_confidence_clarifying_questions(
        self, intent_result: Dict[str, Any], threshold: float
    ) -> List[Dict[str, str]]:
        """Generate clarifying questions when confidence is below threshold.

        This is called by the engine when the intent analyzer returns low confidence
        but didn't generate questions itself.
        """
        confidence = intent_result.get("confidence", 0)
        missing_info = intent_result.get("missing_information", [])
        decision_criteria = intent_result.get("decision_criteria", [])
        success_criteria = intent_result.get("success_criteria", [])

        self.logger.info(
            f"Generating clarifying questions: confidence={confidence}%, "
            f"missing_info={len(missing_info)}, decision_criteria={len(decision_criteria)}, "
            f"success_criteria={len(success_criteria)}"
        )

        questions = []

        # If we have missing information from the analysis, use those
        if missing_info:
            for info in missing_info[:3]:
                questions.append({
                    "question": f"Can you clarify: {info}?",
                    "purpose": f"To gather missing information about {info}",
                    "examples": [],
                    "allow_unknown": True
                })

        # If no decision criteria, ask about them
        if not decision_criteria:
            questions.append({
                "question": "What criteria are most important for your decision? (e.g., cost, performance, ease of use, scalability, time to implement)",
                "purpose": "To understand how to evaluate and compare options",
                "examples": ["cost and time to market", "performance and scalability", "ease of maintenance"],
                "allow_unknown": True
            })

        # If no success criteria, ask about them
        if not success_criteria:
            questions.append({
                "question": "What would a successful outcome look like for this research? What decisions are you trying to make?",
                "purpose": "To understand the end goal and tailor the research accordingly",
                "examples": ["A clear recommendation with justification", "Comparison table with pros/cons", "Implementation timeline"],
                "allow_unknown": True
            })

        # If still no questions, generate generic ones based on low confidence
        if not questions:
            questions.append({
                "question": "Could you provide more context about your specific use case or constraints?",
                "purpose": f"Current analysis confidence ({confidence}%) is below threshold ({threshold}%). More context would help.",
                "examples": ["Budget constraints", "Timeline requirements", "Technical limitations"],
                "allow_unknown": True
            })

        self.logger.info(
            f"Generated {len(questions)} clarifying questions for low-confidence intent")
        return questions

    def _validate_data_result(self, data_result: Any) -> None:
        """Validate data gathering output."""
        if not isinstance(data_result, dict):
            raise ValueError("data_gathering result must be a dict")

        sources = data_result.get("sources")
        if not isinstance(sources, dict) or len(sources) == 0:
            raise ValueError(
                "data_gathering requires non-empty 'sources' dict")

        consolidated = data_result.get("consolidated_information")
        if consolidated is None or not isinstance(consolidated, dict):
            raise ValueError(
                "data_gathering requires 'consolidated_information' dict")

        coverage = data_result.get("coverage_assessment")
        if coverage is None or not isinstance(coverage, dict):
            raise ValueError(
                "data_gathering requires 'coverage_assessment' dict")

    def _validate_analysis_result(self, analysis_result: Any) -> None:
        """Validate analysis & compilation output."""
        if not isinstance(analysis_result, dict):
            raise ValueError("analysis result must be a dict")

        themes = analysis_result.get("themes")
        if not isinstance(themes, list):
            raise ValueError("analysis requires 'themes' list")

        conflicts = analysis_result.get("conflicts")
        if not isinstance(conflicts, list):
            raise ValueError("analysis requires 'conflicts' list")

        summaries = analysis_result.get("summaries")
        if not isinstance(summaries, dict):
            raise ValueError("analysis requires 'summaries' dict")

    def _validate_report_result(self, report: Any) -> None:
        """Validate report generation output."""
        if not isinstance(report, dict):
            raise ValueError("report_generation result must be a dict")

        file_path = report.get("file_path")
        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError(
                "report_generation requires non-empty 'file_path'")

        try:
            if not Path(file_path).exists():
                raise ValueError(
                    f"report_generation file_path does not exist: {file_path}")
        except Exception as e:
            # Normalize path-related issues into a ValueError
            raise ValueError(
                f"report_generation invalid file_path: {file_path}") from e

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

    def _log_intent_analysis_details(self, intent_result: Dict[str, Any], confidence: Dict[str, Any]) -> None:
        """Log detailed intent analysis results for visibility."""
        self.logger.info("=" * 60)
        self.logger.info("INTENT ANALYSIS COMPLETED")
        self.logger.info("=" * 60)

        # Confidence score
        conf_score = intent_result.get("confidence", "N/A")
        self.logger.info(f"  📊 Confidence Score: {conf_score}%")

        # Research type and domain
        self.logger.info(
            f"  🔍 Research Type: {intent_result.get('research_type', 'N/A')}")
        self.logger.info(f"  🌐 Domain: {intent_result.get('domain', 'N/A')}")
        self.logger.info(f"  📐 Scope: {intent_result.get('scope', 'N/A')}")

        # Key entities
        key_entities = intent_result.get("key_entities", [])
        if key_entities:
            self.logger.info(
                f"  🏷️  Key Entities ({len(key_entities)}): {', '.join(str(e) for e in key_entities[:5])}")
            if len(key_entities) > 5:
                self.logger.info(f"      ... and {len(key_entities) - 5} more")

        # Research questions
        research_questions = intent_result.get("research_questions", [])
        self.logger.info(
            f"  ❓ Research Questions ({len(research_questions)}):")
        for i, q in enumerate(research_questions[:3], 1):
            self.logger.info(
                f"      {i}. {q[:100]}{'...' if len(str(q)) > 100 else ''}")
        if len(research_questions) > 3:
            self.logger.info(
                f"      ... and {len(research_questions) - 3} more")

        # Decision criteria
        decision_criteria = intent_result.get("decision_criteria", [])
        if decision_criteria:
            self.logger.info(
                f"  ⚖️  Decision Criteria ({len(decision_criteria)}): {', '.join(str(c) for c in decision_criteria[:5])}")
        else:
            self.logger.info("  ⚖️  Decision Criteria: None specified")

        # Success criteria
        success_criteria = intent_result.get("success_criteria", [])
        if success_criteria:
            self.logger.info(
                f"  ✅ Success Criteria ({len(success_criteria)}):")
            for i, c in enumerate(success_criteria[:3], 1):
                self.logger.info(
                    f"      {i}. {c[:80]}{'...' if len(str(c)) > 80 else ''}")
        else:
            self.logger.info("  ✅ Success Criteria: None specified")

        # Context flags
        context = intent_result.get("context", {})
        if context:
            flags = [k for k, v in context.items() if v]
            if flags:
                self.logger.info(f"  🚩 Context Flags: {', '.join(flags)}")

        # Scorer confidence breakdown
        if isinstance(confidence, dict):
            self.logger.info(f"  📈 Scorer Assessment: {confidence}")

        self.logger.info("=" * 60)

    def _log_data_gathering_details(self, data_result: Dict[str, Any], confidence: Dict[str, Any]) -> None:
        """Log detailed data gathering results for visibility."""
        self.logger.info("=" * 60)
        self.logger.info("DATA GATHERING COMPLETED")
        self.logger.info("=" * 60)

        # Sources summary
        sources = data_result.get("sources", {})
        self.logger.info(f"  📚 Total Sources: {len(sources)}")
        for source_type, source_data in sources.items():
            if isinstance(source_data, dict):
                item_count = len(source_data.get(
                    "items", source_data.get("results", [])))
            elif isinstance(source_data, list):
                item_count = len(source_data)
            else:
                item_count = 1 if source_data else 0
            self.logger.info(f"      • {source_type}: {item_count} items")

        # Coverage assessment
        coverage = data_result.get("coverage_assessment", {})
        if coverage:
            self.logger.info(f"  📊 Coverage Assessment:")
            coverage_pct = coverage.get(
                "coverage_percentage", coverage.get("overall", "N/A"))
            self.logger.info(f"      • Overall: {coverage_pct}")
            gaps = coverage.get("gaps", [])
            if gaps:
                self.logger.info(
                    f"      • Gaps: {', '.join(str(g) for g in gaps[:3])}")

        # Consolidated information summary
        consolidated = data_result.get("consolidated_information", {})
        if consolidated:
            self.logger.info(
                f"  🔗 Consolidated Sections: {len(consolidated)} topics covered")

        # Confidence breakdown
        if isinstance(confidence, dict):
            self.logger.info(f"  📈 Quality Assessment: {confidence}")

        self.logger.info("=" * 60)

    def _log_analysis_details(self, analysis_result: Dict[str, Any], confidence: Dict[str, Any]) -> None:
        """Log detailed analysis results for visibility."""
        self.logger.info("=" * 60)
        self.logger.info("ANALYSIS & COMPILATION COMPLETED")
        self.logger.info("=" * 60)

        # Themes
        themes = analysis_result.get("themes", [])
        self.logger.info(f"  🎯 Themes Identified: {len(themes)}")
        for i, theme in enumerate(themes[:5], 1):
            if isinstance(theme, dict):
                title = theme.get("title", "Untitled")
                evidence_count = len(theme.get("supporting_evidence", []))
                self.logger.info(
                    f"      {i}. {title} ({evidence_count} evidence points)")
        if len(themes) > 5:
            self.logger.info(f"      ... and {len(themes) - 5} more themes")

        # Conflicts
        conflicts = analysis_result.get("conflicts", [])
        if conflicts:
            self.logger.info(f"  ⚠️  Conflicts Found: {len(conflicts)}")
            for i, conflict in enumerate(conflicts[:3], 1):
                if isinstance(conflict, dict):
                    conf_type = conflict.get("conflict_type", "unknown")
                    severity = conflict.get("severity", "N/A")
                    self.logger.info(f"      {i}. [{severity}] {conf_type}")
        else:
            self.logger.info("  ✓ No conflicts identified")

        # Summaries
        summaries = analysis_result.get("summaries", {})
        summary_types = list(summaries.keys())
        if summary_types:
            self.logger.info(
                f"  📝 Summaries Generated: {', '.join(summary_types)}")

        # Data quality
        quality = analysis_result.get("data_quality_assessment", {})
        if quality:
            self.logger.info(f"  📊 Data Quality:")
            self.logger.info(
                f"      • Sources: {quality.get('sources_count', 'N/A')}")
            self.logger.info(
                f"      • Freshness: {quality.get('freshness_score', 'N/A')}")
            self.logger.info(
                f"      • Coverage: {quality.get('coverage_assessment', 'N/A')}")

        # Confidence breakdown
        if isinstance(confidence, dict):
            self.logger.info(f"  📈 Analysis Quality: {confidence}")

        self.logger.info("=" * 60)

    def _log_report_generation_details(self, report: Dict[str, Any], confidence: Dict[str, Any]) -> None:
        """Log detailed report generation results for visibility."""
        self.logger.info("=" * 60)
        self.logger.info("REPORT GENERATION COMPLETED")
        self.logger.info("=" * 60)

        # Report file
        file_path = report.get("file_path", "N/A")
        self.logger.info(f"  📄 Report File: {file_path}")

        # Report sections
        sections = report.get("sections", [])
        if sections and isinstance(sections, list):
            self.logger.info(f"  📑 Sections ({len(sections)}):")
            for section in sections[:6]:
                self.logger.info(f"      • {section}")
            if len(sections) > 6:
                self.logger.info(f"      ... and {len(sections) - 6} more")

        # Report metadata
        metadata = report.get("metadata", {})
        if metadata and isinstance(metadata, dict):
            word_count = metadata.get("word_count", "N/A")
            self.logger.info(f"  📊 Word Count: {word_count}")
            sources_cited = metadata.get("sources_cited", "N/A")
            self.logger.info(f"  🔗 Sources Cited: {sources_cited}")

        # Confidence breakdown
        if isinstance(confidence, dict):
            self.logger.info(f"  📈 Report Quality: {confidence}")

        self.logger.info("=" * 60)
        self.logger.info("✅ Research pipeline completed successfully!")
        self.logger.info("=" * 60)

    async def load_session(self, session_id: str) -> Dict[str, Any]:
        """Load an existing research session."""
        return await self.storage.load_session(session_id)

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all research sessions."""
        return await self.storage.list_sessions()
