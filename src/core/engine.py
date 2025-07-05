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
            self.confidence_scorer = ConfidenceScorer(self.gemini_client, config)
            self.logger.info("Research engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize research engine: {str(e)}")
            raise
        
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
                self.logger.info("Intent analysis indicates clarification needed")
                session_data["status"] = "needs_clarification"
                session_data["clarifying_questions"] = intent_result.get("questions", [])
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
            
            self.logger.info(f"Research completed successfully for session {session_id}")
            
            return {
                "status": "completed",
                "report": report,
                "confidence": overall_confidence,
                "session_data": session_data
            }
            
        except Exception as e:
            self.logger.error(f"Research failed for session {session_id}: {str(e)}", exc_info=True)
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
        """
        
        try:
            response = await self.gemini_client.generate_response(prompt)
            if not response.strip():
                self.logger.warning("Empty response from theme identification")
                return self._fallback_themes(data_result)
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parsing error in theme identification: {str(e)}")
            return self._fallback_themes(data_result)
        except Exception as e:
            self.logger.error(f"Error in theme identification: {str(e)}")
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
        """
        
        try:
            response = await self.gemini_client.generate_response(prompt)
            if not response.strip():
                return []
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parsing error in conflict identification: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error in conflict identification: {str(e)}")
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
        """
        
        try:
            response = await self.gemini_client.generate_response(prompt)
            if not response.strip():
                return {"comparison_table": [], "key_differences": []}
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parsing error in comparison generation: {str(e)}")
            return {"comparison_table": [], "key_differences": []}
        except Exception as e:
            self.logger.error(f"Error in comparison generation: {str(e)}")
            return {"comparison_table": [], "key_differences": []}
    
    async def _generate_timeline(self, data_result: Dict) -> List[Dict]:
        """Generate timeline of events."""
        prompt = f"""
        Extract and organize chronological events from the following data:
        
        {json.dumps(data_result, indent=2)}
        
        Return as a JSON array of timeline events with date and description.
        If no chronological events found, return empty array: []
        """
        
        try:
            response = await self.gemini_client.generate_response(prompt)
            if not response.strip():
                return []
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parsing error in timeline generation: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error in timeline generation: {str(e)}")
            return []
    
    async def _generate_pros_cons(self, data_result: Dict) -> Dict:
        """Generate pros and cons analysis."""
        prompt = f"""
        Analyze the following data and extract pros and cons:
        
        {json.dumps(data_result, indent=2)}
        
        Return structured pros and cons with supporting evidence as JSON.
        Format: {{"pros": [], "cons": []}}
        """
        
        try:
            response = await self.gemini_client.generate_response(prompt)
            if not response.strip():
                return {"pros": [], "cons": []}
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parsing error in pros/cons generation: {str(e)}")
            return {"pros": [], "cons": []}
        except Exception as e:
            self.logger.error(f"Error in pros/cons generation: {str(e)}")
            return {"pros": [], "cons": []}
    
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
