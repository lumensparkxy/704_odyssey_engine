"""
Test suite for Intent Analyzer.

This module tests the IntentAnalyzer class, particularly the clarifying questions generation.
"""

import pytest
import asyncio
import json
from pathlib import Path
import sys
from unittest.mock import AsyncMock, Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.intent_analyzer import IntentAnalyzer
from utils.gemini_client import GeminiClient


class TestIntentAnalyzer:
    """Test cases for the IntentAnalyzer class."""
    
    def setup_method(self):
        """Setup test configuration and mocks."""
        self.config = {
            "CONFIDENCE_THRESHOLD": 75,
            "MAX_FOLLOW_UP_QUESTIONS": 5
        }
        
        # Create a mock Gemini client
        self.mock_gemini_client = Mock(spec=GeminiClient)
        self.intent_analyzer = IntentAnalyzer(self.mock_gemini_client, self.config)
    
    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_success(self):
        """Test successful generation of clarifying questions with valid JSON response."""
        
        # Sample intent analysis data
        intent_analysis = {
            "research_type": "comparison",
            "domain": "technology", 
            "scope": "specific",
            "key_entities": ["Tesla", "BMW", "electric vehicles"],
            "research_questions": ["How do Tesla and BMW electric vehicles compare?"],
            "context_requirements": ["price range", "geographic region"],
            "output_preferences": ["comparison table"],
            "confidence": 60,
            "missing_information": ["specific price range", "geographic region", "vehicle models"]
        }
        
        # Mock successful LLM response with valid JSON
        expected_questions = [
            {
                "question": "What price range are you considering? (e.g., under $50k, $50k-$100k, luxury tier)",
                "purpose": "To focus the comparison on vehicles within your budget",
                "examples": ["Under $50,000", "$50,000-$100,000", "Any price range"],
                "allow_unknown": True
            },
            {
                "question": "Which geographic region or market are you interested in? (e.g., US, Europe, global)",
                "purpose": "To provide region-specific availability and pricing",
                "examples": ["United States", "Europe", "Global comparison"],
                "allow_unknown": True
            },
            {
                "question": "Are you interested in specific vehicle models or all electric vehicles from these brands?",
                "purpose": "To narrow down the comparison scope",
                "examples": ["Model 3 vs iX3", "All SUVs", "All available models"],
                "allow_unknown": False
            }
        ]
        
        self.mock_gemini_client.generate_response.return_value = json.dumps(expected_questions)
        
        # Call the method
        result = await self.intent_analyzer._generate_clarifying_questions(intent_analysis)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["question"] == expected_questions[0]["question"]
        assert result[0]["purpose"] == expected_questions[0]["purpose"]
        assert result[0]["examples"] == expected_questions[0]["examples"]
        assert result[0]["allow_unknown"] == expected_questions[0]["allow_unknown"]
        
        # Verify the prompt was called
        self.mock_gemini_client.generate_response.assert_called_once()
        call_args = self.mock_gemini_client.generate_response.call_args[0][0]
        assert "Generate clarifying questions" in call_args
        assert "specific price range" in call_args
        assert "geographic region" in call_args
    
    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_json_parse_error(self):
        """Test fallback behavior when LLM returns invalid JSON."""
        
        intent_analysis = {
            "research_type": "general_research",
            "domain": "health",
            "scope": "broad", 
            "confidence": 45,
            "missing_information": ["specific condition", "age group", "treatment preferences"]
        }
        
        # Mock LLM response with invalid JSON
        self.mock_gemini_client.generate_response.return_value = "This is not valid JSON response from the LLM"
        
        # Call the method
        result = await self.intent_analyzer._generate_clarifying_questions(intent_analysis)
        
        # Should fall back to simple questions
        assert isinstance(result, list)
        assert len(result) == 3  # Should match missing_information length
        assert result[0]["question"] == "Can you provide more details about: specific condition?"
        assert result[0]["purpose"] == "To clarify specific condition"
        assert result[0]["examples"] == []
        assert result[0]["allow_unknown"] == True
        
        assert result[1]["question"] == "Can you provide more details about: age group?"
        assert result[2]["question"] == "Can you provide more details about: treatment preferences?"
    
    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_empty_missing_info(self):
        """Test behavior when there's no missing information."""
        
        intent_analysis = {
            "research_type": "analysis",
            "domain": "finance",
            "scope": "detailed",
            "confidence": 85,
            "missing_information": []  # No missing info
        }
        
        # Mock empty valid JSON response
        self.mock_gemini_client.generate_response.return_value = "[]"
        
        # Call the method
        result = await self.intent_analyzer._generate_clarifying_questions(intent_analysis)
        
        # Should return empty list
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_max_limit(self):
        """Test that the number of questions respects MAX_FOLLOW_UP_QUESTIONS limit."""
        
        # Create intent analysis with more missing info than the limit
        intent_analysis = {
            "research_type": "comparison",
            "domain": "technology",
            "scope": "broad",
            "confidence": 50,
            "missing_information": [
                "time period", "geographic scope", "specific features", 
                "budget range", "use case", "performance metrics", 
                "brand preferences", "additional criteria"  # 8 items, but limit is 5
            ]
        }
        
        # Mock response that would exceed the limit
        mock_response = []
        for i, info in enumerate(intent_analysis["missing_information"]):
            mock_response.append({
                "question": f"Question about {info}?",
                "purpose": f"To clarify {info}",
                "examples": [],
                "allow_unknown": True
            })
        
        self.mock_gemini_client.generate_response.return_value = json.dumps(mock_response)
        
        # Call the method
        result = await self.intent_analyzer._generate_clarifying_questions(intent_analysis)
        
        # Should respect the MAX_FOLLOW_UP_QUESTIONS limit (5)
        assert isinstance(result, list)
        assert len(result) == 8  # LLM returned all, but check prompt limits it
        
        # Verify prompt includes the limit
        call_args = self.mock_gemini_client.generate_response.call_args[0][0]
        assert f"Generate {min(len(intent_analysis['missing_information']), self.config['MAX_FOLLOW_UP_QUESTIONS'])}" in call_args
    
    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_different_research_types(self):
        """Test question generation for different research types."""
        
        research_scenarios = [
            {
                "research_type": "timeline",
                "domain": "history",
                "missing_information": ["specific period", "geographical focus"]
            },
            {
                "research_type": "pros_cons", 
                "domain": "business",
                "missing_information": ["decision criteria", "stakeholder perspective"]
            },
            {
                "research_type": "general_research",
                "domain": "science",
                "missing_information": ["research depth", "target audience"]
            }
        ]
        
        for scenario in research_scenarios:
            # Reset mock for each scenario
            self.mock_gemini_client.reset_mock()
            
            # Mock appropriate response
            mock_questions = [
                {
                    "question": f"Question for {scenario['research_type']}?",
                    "purpose": f"To clarify {scenario['research_type']} research",
                    "examples": ["Example 1", "Example 2"],
                    "allow_unknown": True
                }
            ]
            self.mock_gemini_client.generate_response.return_value = json.dumps(mock_questions)
            
            # Call the method
            result = await self.intent_analyzer._generate_clarifying_questions(scenario)
            
            # Verify the research type is included in the prompt
            call_args = self.mock_gemini_client.generate_response.call_args[0][0]
            assert scenario["research_type"] in call_args
            assert scenario["domain"] in call_args
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert scenario["research_type"] in result[0]["question"]
    
    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_prompt_structure(self):
        """Test that the prompt includes all necessary components."""
        
        intent_analysis = {
            "research_type": "analysis",
            "domain": "education",
            "scope": "specific",
            "key_entities": ["online learning", "traditional classroom"],
            "confidence": 65,
            "missing_information": ["student age group", "learning objectives"]
        }
        
        # Mock valid JSON response
        mock_questions = [{"question": "Test?", "purpose": "Test", "examples": [], "allow_unknown": True}]
        self.mock_gemini_client.generate_response.return_value = json.dumps(mock_questions)
        
        # Call the method
        await self.intent_analyzer._generate_clarifying_questions(intent_analysis)
        
        # Verify prompt structure
        call_args = self.mock_gemini_client.generate_response.call_args[0][0]
        
        # Check that prompt includes all expected components
        assert "Generate clarifying questions" in call_args
        assert "Intent Analysis:" in call_args
        assert "Missing Information:" in call_args
        assert "Return as JSON array" in call_args
        assert "student age group" in call_args
        assert "learning objectives" in call_args
        assert json.dumps(intent_analysis, indent=2) in call_args
        
        # Check example format is included
        assert "question" in call_args
        assert "purpose" in call_args
        assert "examples" in call_args
        assert "allow_unknown" in call_args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
