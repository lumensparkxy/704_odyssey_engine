"""
Main Research Engine for Odyssey Engine.

This module orchestrates the entire research process from user query to final report.
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils.gemini_client import GeminiClient
from core.intent_analyzer import IntentAnalyzer
from core.data_gatherer import DataGatherer
from core.report_generator import ReportGenerator
from utils.storage import SessionStorage
from utils.confidence import ConfidenceScorer


class ResearchEngine:
    """Main research engine that orchestrates the research process."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the research engine with configuration."""
        self.config = config
        self.gemini_client = GeminiClient(config)
        self.intent_analyzer = IntentAnalyzer(self.gemini_client, config)
        self.data_gatherer = DataGatherer(self.gemini_client, config)
        self.report_generator = ReportGenerator(self.gemini_client, config)
        self.storage = SessionStorage(config)
        self.confidence_scorer = ConfidenceScorer(self.gemini_client, config)
        
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
        session_data = await self.storage.load_session(session_id)
        
        try:
            # Stage 1: Intent Analysis
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
                session_data["status"] = "needs_clarification"
                session_data["clarifying_questions"] = intent_result.get("questions", [])
                await self.storage.save_session(session_id, session_data)
                return {
                    "status": "needs_clarification",
                    "questions": intent_result.get("questions", []),
                    "session_data": session_data
                }
            
            # Stage 2: Data Gathering
            print("📊 Gathering information from multiple sources...")
            data_result = await self.data_gatherer.gather_data(intent_result)
            
            session_data["stages"]["data_gathering"] = {
                "status": "completed",
                "result": data_result,
                "confidence": await self.confidence_scorer.score_data_quality(data_result)
            }
            
            # Stage 3: Analysis and Compilation
            print("🧠 Analyzing and compiling information...")
            analysis_result = await self._analyze_and_compile(intent_result, data_result)
            
            session_data["stages"]["analysis"] = {
                "status": "completed",
                "result": analysis_result,
                "confidence": await self.confidence_scorer.score_analysis(analysis_result)
            }
            
            # Stage 4: Report Generation
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
            
            return {
                "status": "completed",
                "report": report,
                "confidence": overall_confidence,
                "session_data": session_data
            }
            
        except Exception as e:
            session_data["status"] = "error"
            session_data["error"] = str(e)
            session_data["error_at"] = datetime.now().isoformat()
            await self.storage.save_session(session_id, session_data)
            raise
    
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
        
        Return a list of themes with descriptions and supporting evidence.
        """
        
        response = await self.gemini_client.generate_response(prompt)
        return json.loads(response)
    
    async def _identify_conflicts(self, data_result: Dict) -> List[Dict]:
        """Identify conflicting information in the data."""
        prompt = f"""
        Analyze the following research data and identify any conflicting information:
        
        {json.dumps(data_result, indent=2)}
        
        Return conflicts with source reliability assessment.
        """
        
        response = await self.gemini_client.generate_response(prompt)
        return json.loads(response)
    
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
        """
        
        response = await self.gemini_client.generate_response(prompt)
        return json.loads(response)
    
    async def _generate_timeline(self, data_result: Dict) -> List[Dict]:
        """Generate timeline of events."""
        prompt = f"""
        Extract and organize chronological events from the following data:
        
        {json.dumps(data_result, indent=2)}
        
        Return as a timeline with dates and descriptions.
        """
        
        response = await self.gemini_client.generate_response(prompt)
        return json.loads(response)
    
    async def _generate_pros_cons(self, data_result: Dict) -> Dict:
        """Generate pros and cons analysis."""
        prompt = f"""
        Analyze the following data and extract pros and cons:
        
        {json.dumps(data_result, indent=2)}
        
        Return structured pros and cons with supporting evidence.
        """
        
        response = await self.gemini_client.generate_response(prompt)
        return json.loads(response)
    
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
