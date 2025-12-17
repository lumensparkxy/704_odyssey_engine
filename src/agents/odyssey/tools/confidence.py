"""
Confidence Scoring Tool.

Provides confidence assessment for various stages of the research pipeline.
"""

from typing import Dict, Any


def score_confidence(
    stage: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Score the confidence of a research stage result.

    This tool evaluates the quality and completeness of results from
    different stages of the research pipeline.

    Args:
        stage: The pipeline stage being scored 
               ("intent", "data_gathering", "analysis", "report")
        result: The result data to evaluate

    Returns:
        Dictionary containing:
        - score: Confidence score 0-100
        - level: Confidence level (very_high, high, moderate, low, very_low)
        - factors: Individual factor scores
        - recommendations: Suggestions for improvement
    """

    if stage == "intent":
        return _score_intent(result)
    elif stage == "data_gathering":
        return _score_data_gathering(result)
    elif stage == "analysis":
        return _score_analysis(result)
    elif stage == "report":
        return _score_report(result)
    else:
        return {
            "score": 50,
            "level": "moderate",
            "factors": {},
            "recommendations": [f"Unknown stage: {stage}"]
        }


def _score_intent(result: Dict[str, Any]) -> Dict[str, Any]:
    """Score intent analysis results."""
    factors = {}

    # Check for key fields
    factors["has_research_type"] = 20 if result.get("research_type") else 0
    factors["has_domain"] = 15 if result.get("domain") else 0
    factors["has_key_entities"] = 20 if result.get("key_entities") else 0
    factors["has_research_questions"] = 25 if result.get(
        "research_questions") else 0
    factors["low_missing_info"] = 20 if len(
        result.get("missing_information", [])) < 3 else 10

    score = sum(factors.values())

    return {
        "score": score,
        "level": _get_level(score),
        "factors": factors,
        "recommendations": _get_intent_recommendations(result, factors)
    }


def _score_data_gathering(result: Dict[str, Any]) -> Dict[str, Any]:
    """Score data gathering results."""
    factors = {}

    sources = result.get("sources", {})
    factors["has_internal_knowledge"] = 25 if sources.get(
        "internal_knowledge") else 0
    factors["has_search_results"] = 30 if sources.get("google_search") else 0
    factors["has_web_scraping"] = 20 if sources.get("web_scraping") else 0
    factors["has_consolidated_info"] = 25 if result.get(
        "consolidated_information") else 0

    score = sum(factors.values())

    return {
        "score": score,
        "level": _get_level(score),
        "factors": factors,
        "recommendations": _get_data_recommendations(result, factors)
    }


def _score_analysis(result: Dict[str, Any]) -> Dict[str, Any]:
    """Score analysis results."""
    factors = {}

    factors["has_themes"] = 30 if result.get("themes") else 0
    factors["has_conflicts"] = 20 if result.get("conflicts") is not None else 0
    factors["has_synthesis"] = 30 if result.get("synthesis") else 0
    factors["has_quality_assessment"] = 20 if result.get(
        "quality_assessment") else 0

    score = sum(factors.values())

    return {
        "score": score,
        "level": _get_level(score),
        "factors": factors,
        "recommendations": _get_analysis_recommendations(result, factors)
    }


def _score_report(result: Dict[str, Any]) -> Dict[str, Any]:
    """Score report generation results."""
    factors = {}

    content = result.get("content", "")
    factors["has_content"] = 30 if len(content) > 500 else 15 if content else 0
    factors["has_sections"] = 25 if result.get("sections") else 0
    factors["has_bibliography"] = 20 if "bibliography" in content.lower(
    ) or "sources" in content.lower() else 0
    factors["has_metadata"] = 15 if result.get("metadata") else 0
    factors["file_saved"] = 10 if result.get("file_path") else 0

    score = sum(factors.values())

    return {
        "score": score,
        "level": _get_level(score),
        "factors": factors,
        "recommendations": _get_report_recommendations(result, factors)
    }


def _get_level(score: int) -> str:
    """Convert score to confidence level."""
    if score >= 90:
        return "very_high"
    elif score >= 75:
        return "high"
    elif score >= 60:
        return "moderate"
    elif score >= 40:
        return "low"
    else:
        return "very_low"


def _get_intent_recommendations(result: Dict[str, Any], factors: Dict[str, int]) -> list:
    """Get recommendations for intent analysis."""
    recs = []
    if not factors.get("has_research_questions"):
        recs.append("Clarify specific research questions to answer")
    if not factors.get("has_key_entities"):
        recs.append("Identify key entities/subjects to research")
    if factors.get("low_missing_info", 0) < 20:
        recs.append("Address missing information through clarification")
    return recs


def _get_data_recommendations(result: Dict[str, Any], factors: Dict[str, int]) -> list:
    """Get recommendations for data gathering."""
    recs = []
    if not factors.get("has_search_results"):
        recs.append("Perform Google Search for current information")
    if not factors.get("has_web_scraping"):
        recs.append("Consider scraping relevant web sources")
    if not factors.get("has_consolidated_info"):
        recs.append("Consolidate information from all sources")
    return recs


def _get_analysis_recommendations(result: Dict[str, Any], factors: Dict[str, int]) -> list:
    """Get recommendations for analysis."""
    recs = []
    if not factors.get("has_themes"):
        recs.append("Identify major themes in the research")
    if not factors.get("has_synthesis"):
        recs.append("Synthesize findings into coherent narrative")
    return recs


def _get_report_recommendations(result: Dict[str, Any], factors: Dict[str, int]) -> list:
    """Get recommendations for report."""
    recs = []
    if factors.get("has_content", 0) < 30:
        recs.append("Expand report content with more detail")
    if not factors.get("has_bibliography"):
        recs.append("Add bibliography/sources section")
    return recs
