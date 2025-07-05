"""
Confidence Scoring for Odyssey Engine.

This module provides LLM-based confidence scoring for various stages of the research process.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Union

from utils.gemini_client import GeminiClient


class ConfidenceScorer:
    """Provides confidence scoring for research stages using LLM-based analysis."""
    
    def __init__(self, gemini_client: GeminiClient, config: Dict[str, Any]):
        """Initialize the confidence scorer."""
        self.gemini_client = gemini_client
        self.config = config
        self.confidence_threshold = config.get("CONFIDENCE_THRESHOLD", 75)
        
        # Scoring weights for different factors
        self.weights = {
            "data_quality": 0.3,
            "source_reliability": 0.25,
            "coverage_completeness": 0.2,
            "consistency": 0.15,
            "recency": 0.1
        }
    
    async def score_intent_analysis(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score confidence in intent analysis results.
        
        Args:
            intent_result: Results from intent analysis
            
        Returns:
            Confidence scoring details
        """
        # Extract factors for scoring
        confidence_factors = {
            "clarity_score": self._assess_query_clarity(intent_result),
            "completeness_score": self._assess_intent_completeness(intent_result),
            "specificity_score": self._assess_intent_specificity(intent_result),
            "feasibility_score": await self._assess_research_feasibility(intent_result)
        }
        
        # Calculate weighted score
        weighted_score = (
            confidence_factors["clarity_score"] * 0.3 +
            confidence_factors["completeness_score"] * 0.3 +
            confidence_factors["specificity_score"] * 0.2 +
            confidence_factors["feasibility_score"] * 0.2
        )
        
        return {
            "overall_confidence": min(100, max(0, weighted_score)),
            "confidence_level": self._get_confidence_level(weighted_score),
            "factors": confidence_factors,
            "recommendations": self._generate_intent_recommendations(confidence_factors)
        }
    
    async def score_data_quality(self, data_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score confidence in data gathering quality.
        
        Args:
            data_result: Results from data gathering
            
        Returns:
            Data quality confidence scoring
        """
        # Assess different aspects of data quality
        quality_factors = {
            "source_diversity": self._assess_source_diversity(data_result),
            "information_depth": await self._assess_information_depth(data_result),
            "source_reliability": self._assess_overall_source_reliability(data_result),
            "coverage_completeness": self._assess_coverage_completeness(data_result),
            "data_recency": await self._assess_data_recency(data_result)
        }
        
        # Calculate weighted confidence score
        weighted_score = sum(
            quality_factors[factor] * self.weights.get(factor.replace("_", ""), 0.2)
            for factor in quality_factors
        )
        
        return {
            "overall_confidence": min(100, max(0, weighted_score)),
            "confidence_level": self._get_confidence_level(weighted_score),
            "quality_factors": quality_factors,
            "data_reliability_assessment": await self._generate_reliability_assessment(data_result),
            "improvement_suggestions": self._generate_data_improvement_suggestions(quality_factors)
        }
    
    async def score_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score confidence in analysis and compilation results.
        
        Args:
            analysis_result: Results from analysis stage
            
        Returns:
            Analysis confidence scoring
        """
        analysis_factors = {
            "theme_coherence": await self._assess_theme_coherence(analysis_result),
            "conflict_resolution": self._assess_conflict_resolution(analysis_result),
            "synthesis_quality": await self._assess_synthesis_quality(analysis_result),
            "logical_consistency": await self._assess_logical_consistency(analysis_result)
        }
        
        weighted_score = sum(analysis_factors.values()) / len(analysis_factors)
        
        return {
            "overall_confidence": min(100, max(0, weighted_score)),
            "confidence_level": self._get_confidence_level(weighted_score),
            "analysis_factors": analysis_factors,
            "synthesis_assessment": await self._generate_synthesis_assessment(analysis_result)
        }
    
    async def score_report_quality(self, report_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score confidence in report generation quality.
        
        Args:
            report_result: Results from report generation
            
        Returns:
            Report quality confidence scoring
        """
        report_factors = {
            "completeness": self._assess_report_completeness(report_result),
            "clarity": await self._assess_report_clarity(report_result),
            "structure": self._assess_report_structure(report_result),
            "citation_quality": self._assess_citation_quality(report_result)
        }
        
        weighted_score = sum(report_factors.values()) / len(report_factors)
        
        return {
            "overall_confidence": min(100, max(0, weighted_score)),
            "confidence_level": self._get_confidence_level(weighted_score),
            "report_factors": report_factors,
            "quality_assessment": self._generate_report_quality_assessment(report_factors)
        }
    
    async def calculate_overall_confidence(self, stages: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Calculate overall confidence across all research stages.
        
        Args:
            stages: Dictionary of all stage results with confidence scores
            
        Returns:
            Overall confidence assessment
        """
        stage_confidences = {}
        stage_weights = {
            "intent_analysis": 0.15,
            "data_gathering": 0.35,
            "analysis": 0.30,
            "report_generation": 0.20
        }
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for stage_name, stage_data in stages.items():
            if stage_data.get("status") == "completed" and "confidence" in stage_data:
                confidence_score = stage_data["confidence"].get("overall_confidence", 0)
                weight = stage_weights.get(stage_name, 0.25)
                
                stage_confidences[stage_name] = confidence_score
                total_weighted_score += confidence_score * weight
                total_weight += weight
        
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0
        
        return {
            "overall_confidence": overall_score,
            "confidence_level": self._get_confidence_level(overall_score),
            "stage_confidences": stage_confidences,
            "meets_threshold": overall_score >= self.confidence_threshold,
            "confidence_breakdown": await self._generate_confidence_breakdown(stage_confidences),
            "recommendations": self._generate_overall_recommendations(stage_confidences, overall_score)
        }
    
    def _assess_query_clarity(self, intent_result: Dict[str, Any]) -> float:
        """Assess clarity of the original query."""
        research_questions = intent_result.get("research_questions", [])
        key_entities = intent_result.get("key_entities", [])
        
        clarity_score = 50.0  # Base score
        
        # More specific questions increase clarity
        if len(research_questions) > 0:
            clarity_score += 20
        
        # Clear entities increase clarity
        if len(key_entities) >= 2:
            clarity_score += 15
        
        # Defined scope increases clarity
        if intent_result.get("scope") == "specific":
            clarity_score += 15
        
        return min(100, clarity_score)
    
    def _assess_intent_completeness(self, intent_result: Dict[str, Any]) -> float:
        """Assess completeness of intent understanding."""
        required_fields = ["research_type", "domain", "key_entities", "research_questions"]
        completeness_score = 0.0
        
        for field in required_fields:
            if intent_result.get(field):
                completeness_score += 25
        
        # Bonus for additional context
        if intent_result.get("context_requirements"):
            completeness_score += 10
        
        return min(100, completeness_score)
    
    def _assess_intent_specificity(self, intent_result: Dict[str, Any]) -> float:
        """Assess specificity of the research intent."""
        specificity_score = 50.0
        
        # Specific research type
        if intent_result.get("research_type") != "general_research":
            specificity_score += 20
        
        # Specific domain
        if intent_result.get("domain") != "general":
            specificity_score += 15
        
        # Multiple specific entities
        entities = intent_result.get("key_entities", [])
        if len(entities) >= 3:
            specificity_score += 15
        
        return min(100, specificity_score)
    
    async def _assess_research_feasibility(self, intent_result: Dict[str, Any]) -> float:
        """Assess feasibility of conducting the research."""
        research_questions = intent_result.get("research_questions", [])
        
        if not research_questions:
            return 30.0
        
        # Use AI to assess feasibility
        prompt = f"""
        Assess the research feasibility of these questions on a scale of 0-100:
        
        Research Questions:
        {json.dumps(research_questions, indent=2)}
        
        Research Type: {intent_result.get("research_type", "unknown")}
        Domain: {intent_result.get("domain", "unknown")}
        
        Consider:
        1. Availability of public information
        2. Complexity of the research
        3. Data accessibility
        4. Time constraints for comprehensive research
        
        Return only a numeric score (0-100).
        """
        
        try:
            response = await self.gemini_client.generate_response(prompt)
            score = float(response.strip())
            return min(100, max(0, score))
        except (ValueError, TypeError):
            return 60.0  # Default moderate feasibility
    
    def _assess_source_diversity(self, data_result: Dict[str, Any]) -> float:
        """Assess diversity of data sources."""
        sources = data_result.get("sources", {})
        active_sources = [k for k, v in sources.items() if v and len(str(v)) > 100]
        
        # Score based on number of different source types
        diversity_score = len(active_sources) * 25
        return min(100, diversity_score)
    
    async def _assess_information_depth(self, data_result: Dict[str, Any]) -> float:
        """Assess depth of gathered information."""
        consolidated_info = data_result.get("consolidated_information", {})
        
        if not consolidated_info:
            return 20.0
        
        # Use AI to assess depth
        prompt = f"""
        Assess the depth and comprehensiveness of this research information on a scale of 0-100:
        
        {json.dumps(consolidated_info, indent=2, default=str)[:2000]}
        
        Consider:
        1. Detail level of information
        2. Multiple perspectives covered
        3. Supporting evidence provided
        4. Breadth of coverage
        
        Return only a numeric score (0-100).
        """
        
        try:
            response = await self.gemini_client.generate_response(prompt)
            score = float(response.strip())
            return min(100, max(0, score))
        except (ValueError, TypeError):
            # Fallback assessment based on content length
            content_length = len(str(consolidated_info))
            if content_length > 5000:
                return 80.0
            elif content_length > 2000:
                return 60.0
            elif content_length > 500:
                return 40.0
            else:
                return 20.0
    
    def _assess_overall_source_reliability(self, data_result: Dict[str, Any]) -> float:
        """Assess overall reliability of sources."""
        source_reliability = data_result.get("source_reliability", {})
        
        if not source_reliability:
            return 50.0
        
        # Calculate weighted average of source reliabilities
        total_score = 0.0
        total_weight = 0.0
        
        for source_type, reliability in source_reliability.items():
            if isinstance(reliability, (int, float)):
                total_score += reliability * 100  # Convert to 0-100 scale
                total_weight += 1
        
        return total_score / total_weight if total_weight > 0 else 50.0
    
    def _assess_coverage_completeness(self, data_result: Dict[str, Any]) -> float:
        """Assess completeness of research coverage."""
        coverage_assessment = data_result.get("coverage_assessment", {})
        overall_coverage = coverage_assessment.get("overall_coverage", 50.0)
        
        return min(100, max(0, overall_coverage))
    
    async def _assess_data_recency(self, data_result: Dict[str, Any]) -> float:
        """Assess recency of gathered data."""
        # This would analyze publication dates, last modified dates, etc.
        # For now, return a moderate score
        return 70.0
    
    async def _assess_theme_coherence(self, analysis_result: Dict[str, Any]) -> float:
        """Assess coherence of identified themes."""
        themes = analysis_result.get("themes", [])
        
        if not themes:
            return 30.0
        
        # Use AI to assess theme coherence
        prompt = f"""
        Assess the coherence and logical organization of these research themes on a scale of 0-100:
        
        {json.dumps(themes, indent=2)}
        
        Consider:
        1. Logical grouping of related concepts
        2. Clear theme definitions
        3. Non-overlapping categories
        4. Comprehensive coverage
        
        Return only a numeric score (0-100).
        """
        
        try:
            response = await self.gemini_client.generate_response(prompt)
            score = float(response.strip())
            return min(100, max(0, score))
        except (ValueError, TypeError):
            return 60.0
    
    def _assess_conflict_resolution(self, analysis_result: Dict[str, Any]) -> float:
        """Assess quality of conflict identification and resolution."""
        conflicts = analysis_result.get("conflicts", [])
        
        # Base score for identifying conflicts
        if len(conflicts) == 0:
            return 80.0  # No conflicts found or well-resolved
        
        # Assess quality of conflict handling
        resolved_conflicts = [c for c in conflicts if c.get("resolution") or c.get("reliability_assessment")]
        resolution_rate = len(resolved_conflicts) / len(conflicts) if conflicts else 1.0
        
        return resolution_rate * 100
    
    async def _assess_synthesis_quality(self, analysis_result: Dict[str, Any]) -> float:
        """Assess quality of information synthesis."""
        summaries = analysis_result.get("summaries", {})
        
        if not summaries:
            return 30.0
        
        # Count different types of summaries
        summary_types = len(summaries)
        quality_score = min(summary_types * 20, 80)
        
        # Bonus for executive summary quality
        if "executive" in summaries:
            executive_length = len(summaries["executive"])
            if 200 <= executive_length <= 500:  # Good length range
                quality_score += 20
        
        return min(100, quality_score)
    
    async def _assess_logical_consistency(self, analysis_result: Dict[str, Any]) -> float:
        """Assess logical consistency of analysis."""
        # This would check for logical consistency in the analysis
        # For now, return a moderate score
        return 75.0
    
    def _assess_report_completeness(self, report_result: Dict[str, Any]) -> float:
        """Assess completeness of the generated report."""
        sections = report_result.get("sections", {})
        required_sections = ["executive_summary", "key_findings", "detailed_sections", "bibliography"]
        
        completeness_score = 0.0
        for section in required_sections:
            if sections.get(section) and len(sections[section]) > 50:
                completeness_score += 25
        
        return completeness_score
    
    async def _assess_report_clarity(self, report_result: Dict[str, Any]) -> float:
        """Assess clarity of the report."""
        content = report_result.get("content", "")
        
        if len(content) < 500:
            return 30.0
        
        # Basic clarity indicators
        clarity_score = 50.0
        
        # Check for clear structure
        if content.count("#") >= 3:  # Multiple headers
            clarity_score += 15
        
        # Check for bullet points/lists
        if content.count("-") >= 5:
            clarity_score += 10
        
        # Check for reasonable length
        word_count = len(content.split())
        if 1000 <= word_count <= 5000:
            clarity_score += 25
        
        return min(100, clarity_score)
    
    def _assess_report_structure(self, report_result: Dict[str, Any]) -> float:
        """Assess structural quality of the report."""
        content = report_result.get("content", "")
        
        structure_score = 0.0
        
        # Check for required structural elements
        if "# " in content:  # Main title
            structure_score += 20
        if "## " in content:  # Section headers
            structure_score += 20
        if "Executive Summary" in content:
            structure_score += 20
        if "Key Findings" in content:
            structure_score += 20
        if "Sources" in content or "Bibliography" in content:
            structure_score += 20
        
        return structure_score
    
    def _assess_citation_quality(self, report_result: Dict[str, Any]) -> float:
        """Assess quality of citations and references."""
        content = report_result.get("content", "")
        
        # Count potential citations (URLs, references)
        citation_indicators = content.count("http") + content.count("www.") + content.count("[")
        
        if citation_indicators >= 5:
            return 90.0
        elif citation_indicators >= 3:
            return 70.0
        elif citation_indicators >= 1:
            return 50.0
        else:
            return 30.0
    
    def _get_confidence_level(self, score: float) -> str:
        """Convert numeric score to confidence level."""
        if score >= 90:
            return "Very High"
        elif score >= 75:
            return "High"
        elif score >= 60:
            return "Moderate"
        elif score >= 40:
            return "Low"
        else:
            return "Very Low"
    
    def _generate_intent_recommendations(self, factors: Dict[str, float]) -> List[str]:
        """Generate recommendations for improving intent analysis."""
        recommendations = []
        
        if factors["clarity_score"] < 70:
            recommendations.append("Consider providing more specific research questions")
        
        if factors["completeness_score"] < 70:
            recommendations.append("Additional context about research scope would be helpful")
        
        if factors["specificity_score"] < 70:
            recommendations.append("More specific entities or timeframes could improve results")
        
        if factors["feasibility_score"] < 60:
            recommendations.append("This research topic may have limited available information")
        
        return recommendations
    
    async def _generate_reliability_assessment(self, data_result: Dict[str, Any]) -> str:
        """Generate textual assessment of data reliability."""
        source_reliability = data_result.get("source_reliability", {})
        
        if not source_reliability:
            return "Data reliability could not be assessed due to insufficient source information."
        
        avg_reliability = sum(source_reliability.values()) / len(source_reliability)
        
        if avg_reliability >= 0.8:
            return "Data sources demonstrate high reliability with authoritative and credible sources."
        elif avg_reliability >= 0.6:
            return "Data sources show moderate reliability with generally trustworthy information."
        else:
            return "Data sources have mixed reliability; conclusions should be interpreted with caution."
    
    def _generate_data_improvement_suggestions(self, factors: Dict[str, float]) -> List[str]:
        """Generate suggestions for improving data quality."""
        suggestions = []
        
        if factors["source_diversity"] < 70:
            suggestions.append("Consider gathering information from additional source types")
        
        if factors["information_depth"] < 70:
            suggestions.append("More detailed information from each source would strengthen the analysis")
        
        if factors["source_reliability"] < 70:
            suggestions.append("Prioritize more authoritative and reliable sources")
        
        if factors["coverage_completeness"] < 70:
            suggestions.append("Additional research may be needed to fully address all aspects of the query")
        
        return suggestions
    
    async def _generate_synthesis_assessment(self, analysis_result: Dict[str, Any]) -> str:
        """Generate assessment of synthesis quality."""
        themes = analysis_result.get("themes", [])
        conflicts = analysis_result.get("conflicts", [])
        summaries = analysis_result.get("summaries", {})
        
        assessment_parts = []
        
        if len(themes) > 0:
            assessment_parts.append(f"Analysis identified {len(themes)} key themes.")
        
        if len(conflicts) > 0:
            assessment_parts.append(f"Found and addressed {len(conflicts)} information conflicts.")
        
        if len(summaries) > 1:
            assessment_parts.append("Multiple synthesis approaches were applied.")
        
        if not assessment_parts:
            return "Synthesis quality could not be fully assessed."
        
        return " ".join(assessment_parts)
    
    def _generate_report_quality_assessment(self, factors: Dict[str, float]) -> str:
        """Generate assessment of report quality."""
        avg_score = sum(factors.values()) / len(factors)
        
        if avg_score >= 80:
            return "Report demonstrates high quality with comprehensive coverage and clear structure."
        elif avg_score >= 60:
            return "Report shows good quality with adequate coverage and organization."
        else:
            return "Report quality could be improved with better structure and more comprehensive content."
    
    async def _generate_confidence_breakdown(self, stage_confidences: Dict[str, float]) -> Dict[str, str]:
        """Generate detailed breakdown of confidence across stages."""
        breakdown = {}
        
        for stage, confidence in stage_confidences.items():
            level = self._get_confidence_level(confidence)
            breakdown[stage] = f"{confidence:.1f}% ({level})"
        
        return breakdown
    
    def _generate_overall_recommendations(self, stage_confidences: Dict[str, float], overall_score: float) -> List[str]:
        """Generate recommendations for improving overall confidence."""
        recommendations = []
        
        # Find lowest confidence stage
        if stage_confidences:
            lowest_stage = min(stage_confidences, key=stage_confidences.get)
            lowest_score = stage_confidences[lowest_stage]
            
            if lowest_score < 60:
                recommendations.append(f"Consider improving {lowest_stage.replace('_', ' ')} (currently {lowest_score:.1f}%)")
        
        if overall_score < self.confidence_threshold:
            recommendations.append(f"Overall confidence ({overall_score:.1f}%) is below threshold ({self.confidence_threshold}%)")
            recommendations.append("Consider additional research or refinement of research scope")
        
        return recommendations
