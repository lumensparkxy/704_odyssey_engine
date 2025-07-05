#!/usr/bin/env python3
"""
Debug script for _generate_clarifying_questions method.
This script runs the actual method with real Gemini API to see why it might be failing.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.intent_analyzer import IntentAnalyzer
from utils.gemini_client import GeminiClient


async def test_real_clarifying_questions():
    """Test the _generate_clarifying_questions method with real API calls."""
    
    # Load configuration
    config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "GEMINI_MODEL": "gemini-2.5-pro",
        "CONFIDENCE_THRESHOLD": 75,
        "MAX_FOLLOW_UP_QUESTIONS": 5
    }
    
    if not config["GEMINI_API_KEY"]:
        print("❌ No GEMINI_API_KEY found in environment variables")
        print("Please set your API key: export GEMINI_API_KEY='your_api_key_here'")
        return
    
    # Initialize components
    gemini_client = GeminiClient(config)
    intent_analyzer = IntentAnalyzer(gemini_client, config)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Technology Comparison",
            "intent_analysis": {
                "research_type": "comparison",
                "domain": "technology",
                "scope": "specific",
                "key_entities": ["iPhone", "Samsung Galaxy", "smartphones"],
                "research_questions": ["How do iPhone and Samsung Galaxy compare?"],
                "context_requirements": ["price range", "specific models"],
                "output_preferences": ["comparison table"],
                "confidence": 60,
                "missing_information": ["specific price range", "phone models", "feature priorities"]
            }
        },
        {
            "name": "Health Research", 
            "intent_analysis": {
                "research_type": "general_research",
                "domain": "health",
                "scope": "broad",
                "key_entities": ["exercise", "diet", "weight loss"],
                "research_questions": ["What are the best approaches to weight loss?"],
                "context_requirements": ["age group", "current health status"],
                "output_preferences": ["comprehensive guide"],
                "confidence": 45,
                "missing_information": ["age group", "health conditions", "time frame", "current fitness level"]
            }
        },
        {
            "name": "Business Analysis",
            "intent_analysis": {
                "research_type": "pros_cons",
                "domain": "business",
                "scope": "detailed",
                "key_entities": ["remote work", "office work", "productivity"],
                "research_questions": ["What are the pros and cons of remote work vs office work?"],
                "context_requirements": ["industry type", "company size"],
                "output_preferences": ["structured analysis"],
                "confidence": 70,
                "missing_information": ["industry sector", "company size", "employee demographics"]
            }
        },
        {
            "name": "Simple Query (likely to fail)",
            "intent_analysis": {
                "research_type": "general_research",
                "domain": "unknown",
                "scope": "broad",
                "key_entities": ["breakfast"],
                "research_questions": ["What is the best food for breakfast?"],
                "context_requirements": ["scope", "timeframe"],
                "output_preferences": ["comprehensive_report"],
                "confidence": 30,
                "missing_information": ["specific scope", "preferred timeframe"]
            }
        }
    ]
    
    print("🔍 Testing _generate_clarifying_questions with real API calls...")
    print("=" * 70)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 Test {i}: {scenario['name']}")
        print("-" * 50)
        
        try:
            # Call the actual method
            print("🤖 Calling _generate_clarifying_questions...")
            
            questions = await intent_analyzer._generate_clarifying_questions(scenario["intent_analysis"])
            
            print(f"✅ Success! Generated {len(questions)} questions:")
            
            for j, question in enumerate(questions, 1):
                print(f"\n   Question {j}:")
                print(f"   Q: {question.get('question', 'N/A')}")
                print(f"   Purpose: {question.get('purpose', 'N/A')}")
                if question.get('examples'):
                    print(f"   Examples: {', '.join(question.get('examples', []))}")
                print(f"   Allow Unknown: {question.get('allow_unknown', False)}")
            
            # Check if this looks like fallback questions
            if questions and "Can you provide more details about:" in questions[0].get("question", ""):
                print("\n   ⚠️  NOTE: These look like fallback questions - LLM generation may have failed")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*50)
    
    print("\n🏁 Testing complete!")
    
    # Show how to debug further
    print("\n💡 Debugging Tips:")
    print("1. If you see 'Can you provide more details about:' questions, the LLM generation failed")
    print("2. Check your GEMINI_API_KEY is valid")
    print("3. The method falls back to simple questions when JSON parsing fails")
    print("4. Try running with different intent_analysis data to see what works")


async def test_with_debug_logging():
    """Test with enhanced logging to see the actual LLM responses."""
    
    config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "GEMINI_MODEL": "gemini-2.5-pro",
        "CONFIDENCE_THRESHOLD": 75,
        "MAX_FOLLOW_UP_QUESTIONS": 3  # Smaller number for testing
    }
    
    if not config["GEMINI_API_KEY"]:
        print("❌ No GEMINI_API_KEY found")
        return
    
    # Create a custom IntentAnalyzer with debug logging
    class DebugIntentAnalyzer(IntentAnalyzer):
        async def _generate_clarifying_questions(self, intent_analysis):
            """Override with debug logging."""
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
            
            print("\n🔧 DEBUG: Sending prompt to LLM:")
            print("-" * 40)
            print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            print("-" * 40)
            
            response = await self.gemini_client.generate_response(prompt)
            
            print(f"\n🔧 DEBUG: Raw LLM response ({len(response)} chars):")
            print("-" * 40)
            print(response)
            print("-" * 40)
            
            try:
                parsed = json.loads(response)
                print(f"\n🔧 DEBUG: Successfully parsed JSON with {len(parsed)} questions")
                return parsed
            except json.JSONDecodeError as e:
                print(f"\n🔧 DEBUG: JSON parsing failed: {e}")
                print("🔧 DEBUG: Falling back to simple questions")
                return self._generate_fallback_questions(missing_info)
    
    gemini_client = GeminiClient(config)
    debug_analyzer = DebugIntentAnalyzer(gemini_client, config)
    
    # Simple test case
    intent_analysis = {
        "research_type": "comparison",
        "domain": "technology",
        "scope": "specific",
        "confidence": 60,
        "missing_information": ["price range", "specific models"]
    }
    
    print("🔧 DEBUGGING: Testing with enhanced logging...")
    questions = await debug_analyzer._generate_clarifying_questions(intent_analysis)
    
    print(f"\n🔧 FINAL RESULT: {len(questions)} questions generated")
    for i, q in enumerate(questions, 1):
        print(f"   {i}. {q}")


if __name__ == "__main__":
    print("🚀 Clarifying Questions Debug Tool")
    print("=" * 40)
    
    choice = input("\nChoose test mode:\n1. Standard tests\n2. Debug with logging\nEnter 1 or 2: ").strip()
    
    if choice == "2":
        asyncio.run(test_with_debug_logging())
    else:
        asyncio.run(test_real_clarifying_questions())
