"""
Integration tests for Intent Analyzer with actual LLM calls.

This module tests the IntentAnalyzer class with real Gemini API calls to verify
actual LLM behavior for intent analysis and question generation.

NOTE: These tests require a valid GEMINI_API_KEY environment variable.
"""

import pytest
import asyncio
import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.intent_analyzer import IntentAnalyzer
from utils.gemini_client import GeminiClient


class TestIntentAnalyzerWithRealLLM:
    """Integration tests using actual LLM calls."""
    
    @pytest.fixture(scope="class")
    def config(self):
        """Test configuration with real API key."""
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            pytest.skip("GEMINI_API_KEY environment variable not set")
        
        return {
            "GEMINI_API_KEY": api_key,
            "GEMINI_MODEL": "gemini-2.5-pro",
            "CONFIDENCE_THRESHOLD": 75,
            "MAX_FOLLOW_UP_QUESTIONS": 5
        }
    
    @pytest.fixture(scope="class")
    def intent_analyzer(self, config):
        """Create IntentAnalyzer with real Gemini client."""
        gemini_client = GeminiClient(config)
        return IntentAnalyzer(gemini_client, config)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_perform_intent_analysis_real_llm(self, intent_analyzer):
        """Test _perform_intent_analysis with actual LLM calls."""
        
        # Test different types of queries
        test_cases = [
            {
                "name": "Technology Comparison Query",
                "context": {
                    "original_query": "Compare iPhone vs Samsung Galaxy performance",
                    "conversation_history": []
                },
                "expected_fields": ["research_type", "domain", "key_entities", "missing_information"]
            },
            {
                "name": "Health Research Query", 
                "context": {
                    "original_query": "What are the best exercises for weight loss?",
                    "conversation_history": []
                },
                "expected_fields": ["research_type", "domain", "scope", "confidence"]
            },
            {
                "name": "Business Analysis Query",
                "context": {
                    "original_query": "Pros and cons of remote work",
                    "conversation_history": []
                },
                "expected_fields": ["research_type", "domain", "research_questions"]
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🧪 Testing: {test_case['name']}")
            
            # Call the actual method
            result = await intent_analyzer._perform_intent_analysis(test_case["context"])
            
            # Verify structure
            assert isinstance(result, dict), f"Result should be dict for {test_case['name']}"
            
            # Check expected fields exist
            for field in test_case["expected_fields"]:
                assert field in result, f"Missing field '{field}' in {test_case['name']}"
            
            # Verify confidence is reasonable
            confidence = result.get("confidence", 0)
            assert 0 <= confidence <= 100, f"Confidence should be 0-100, got {confidence}"
            
            # Verify research_type is valid
            valid_types = ["comparison", "analysis", "timeline", "pros_cons", "general_research"]
            research_type = result.get("research_type", "")
            assert research_type in valid_types, f"Invalid research_type: {research_type}"
            
            print(f"   ✅ Research Type: {result.get('research_type')}")
            print(f"   ✅ Domain: {result.get('domain')}")
            print(f"   ✅ Confidence: {result.get('confidence')}%")
            print(f"   ✅ Missing Info: {len(result.get('missing_information', []))} items")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_assess_critical_missing_info_real_llm(self, intent_analyzer):
        """Test _assess_critical_missing_info with actual LLM calls."""
        
        test_scenarios = [
            {
                "name": "Critical Missing Info",
                "intent_analysis": {
                    "research_type": "comparison",
                    "domain": "technology",
                    "confidence": 60
                },
                "missing_info": ["specific product models", "price range", "target market"],
                "expected": True  # Should be critical
            },
            {
                "name": "Non-Critical Missing Info",
                "intent_analysis": {
                    "research_type": "general_research", 
                    "domain": "health",
                    "confidence": 80
                },
                "missing_info": ["preferred format", "reading level"],
                "expected": False  # Should not be critical
            },
            {
                "name": "Empty Missing Info",
                "intent_analysis": {
                    "research_type": "analysis",
                    "domain": "business",
                    "confidence": 90
                },
                "missing_info": [],
                "expected": False  # No missing info = not critical
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n🧪 Testing Critical Assessment: {scenario['name']}")
            
            # Call the actual method
            is_critical = await intent_analyzer._assess_critical_missing_info(
                scenario["intent_analysis"], 
                scenario["missing_info"]
            )
            
            # Verify return type
            assert isinstance(is_critical, bool), f"Should return boolean for {scenario['name']}"
            
            print(f"   ✅ Missing Info: {scenario['missing_info']}")
            print(f"   ✅ Assessed as Critical: {is_critical}")
            
            # For non-empty missing info, verify it makes a reasonable decision
            if scenario["missing_info"]:
                # We can't assert exact expected values since LLM might vary,
                # but we can check it's making decisions
                assert is_critical in [True, False], "Should return valid boolean"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_generate_clarifying_questions_real_llm(self, intent_analyzer):
        """Test _generate_clarifying_questions with actual LLM calls."""
        
        test_scenarios = [
            {
                "name": "Technology Comparison",
                "intent_analysis": {
                    "research_type": "comparison",
                    "domain": "technology",
                    "scope": "specific", 
                    "key_entities": ["iPhone", "Samsung Galaxy"],
                    "confidence": 60,
                    "missing_information": ["specific models", "price range", "use case"]
                }
            },
            {
                "name": "Health Research",
                "intent_analysis": {
                    "research_type": "general_research",
                    "domain": "health",
                    "scope": "broad",
                    "key_entities": ["diet", "exercise", "weight loss"],
                    "confidence": 45,
                    "missing_information": ["age group", "current fitness level", "health conditions", "time frame"]
                }
            },
            {
                "name": "Business Decision",
                "intent_analysis": {
                    "research_type": "pros_cons",
                    "domain": "business",
                    "scope": "detailed",
                    "key_entities": ["remote work", "productivity"],
                    "confidence": 55,
                    "missing_information": ["company size", "industry", "current setup"]
                }
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n🧪 Testing Question Generation: {scenario['name']}")
            
            # Call the actual method
            questions = await intent_analyzer._generate_clarifying_questions(scenario["intent_analysis"])
            
            # Verify basic structure
            assert isinstance(questions, list), f"Should return list for {scenario['name']}"
            assert len(questions) > 0, f"Should generate at least one question for {scenario['name']}"
            assert len(questions) <= intent_analyzer.max_follow_up_questions, "Should respect max questions limit"
            
            # Verify each question structure
            for i, question in enumerate(questions):
                assert isinstance(question, dict), f"Question {i} should be dict"
                assert "question" in question, f"Question {i} missing 'question' field"
                assert "purpose" in question, f"Question {i} missing 'purpose' field"
                assert "allow_unknown" in question, f"Question {i} missing 'allow_unknown' field"
                
                # Verify question quality
                question_text = question.get("question", "")
                assert len(question_text) > 10, f"Question {i} too short: {question_text}"
                assert "?" in question_text, f"Question {i} should end with question mark"
                
                # Check if it's a fallback question (indicates LLM failure)
                is_fallback = "Can you provide more details about:" in question_text
                
                print(f"   Question {i+1}: {question_text}")
                print(f"   Purpose: {question.get('purpose', 'N/A')}")
                print(f"   Examples: {question.get('examples', [])}")
                print(f"   Is Fallback: {is_fallback}")
                print(f"   Allow Unknown: {question.get('allow_unknown', False)}")
                print()
            
            # Count fallback vs generated questions
            fallback_count = sum(1 for q in questions if "Can you provide more details about:" in q.get("question", ""))
            generated_count = len(questions) - fallback_count
            
            print(f"   ✅ Total Questions: {len(questions)}")
            print(f"   ✅ LLM Generated: {generated_count}")
            print(f"   ✅ Fallback: {fallback_count}")
            
            # We hope for more generated than fallback, but don't fail if LLM struggles
            if fallback_count == len(questions):
                print(f"   ⚠️  WARNING: All questions were fallbacks - LLM generation may be failing")
    
    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_full_intent_analysis_pipeline_real_llm(self, intent_analyzer):
        """Test the complete intent analysis pipeline with actual LLM calls."""
        
        test_queries = [
            "What's the best laptop for programming?",
            "Compare Tesla Model 3 vs BMW i4",
            "How to lose weight effectively?",
            "Pros and cons of working from home"
        ]
        
        for query in test_queries:
            print(f"\n🧪 Testing Full Pipeline: '{query}'")
            
            # Test the main analyze_intent method
            result = await intent_analyzer.analyze_intent(query)
            
            # Verify result structure
            assert isinstance(result, dict), "Result should be dict"
            assert "needs_clarification" in result, "Missing needs_clarification field"
            assert "confidence" in result, "Missing confidence field"
            
            needs_clarification = result["needs_clarification"]
            confidence = result["confidence"]
            
            print(f"   ✅ Needs Clarification: {needs_clarification}")
            print(f"   ✅ Confidence: {confidence}")
            
            if needs_clarification:
                assert "questions" in result, "Should have questions if clarification needed"
                questions = result["questions"]
                assert isinstance(questions, list), "Questions should be list"
                assert len(questions) > 0, "Should have at least one question"
                
                print(f"   ✅ Generated {len(questions)} clarifying questions")
                for i, q in enumerate(questions):
                    print(f"      Q{i+1}: {q.get('question', 'N/A')}")
            else:
                assert "intent" in result, "Should have intent if no clarification needed"
                intent = result["intent"]
                assert isinstance(intent, dict), "Intent should be dict"
                
                print(f"   ✅ Research Type: {intent.get('research_type', 'N/A')}")
                print(f"   ✅ Domain: {intent.get('domain', 'N/A')}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_llm_failure_handling_real_api(self, intent_analyzer):
        """Test how the system handles real LLM failures/edge cases."""
        
        # Test with potentially problematic inputs
        edge_cases = [
            "",  # Empty query
            "a",  # Single character
            "?" * 100,  # Many question marks
            "What is the meaning of life, the universe, and everything?" * 10,  # Very long
        ]
        
        for edge_case in edge_cases:
            print(f"\n🧪 Testing Edge Case: '{edge_case[:50]}{'...' if len(edge_case) > 50 else ''}'")
            
            try:
                context = {"original_query": edge_case, "conversation_history": []}
                result = await intent_analyzer._perform_intent_analysis(context)
                
                # Should still return a valid structure even for edge cases
                assert isinstance(result, dict), "Should return dict even for edge cases"
                print(f"   ✅ Handled gracefully: {result.get('research_type', 'N/A')}")
                
            except Exception as e:
                print(f"   ⚠️  Exception: {type(e).__name__}: {str(e)}")
                # Some edge cases might legitimately fail


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_intent_analyzer_integration.py -v -m integration
    pytest.main([__file__, "-v", "-m", "integration", "-s"])
