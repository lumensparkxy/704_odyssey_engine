#!/usr/bin/env python3
"""
Integration test runner for Intent Analyzer with real LLM calls.

This script runs integration tests that make actual calls to the Gemini API
to test the real behavior of intent analysis methods.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_api_key():
    """Check if GEMINI_API_KEY is set."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set!")
        print()
        print("To run these tests, you need to set your Gemini API key:")
        print("export GEMINI_API_KEY='your_api_key_here'")
        print()
        print("You can get an API key from: https://aistudio.google.com/app/apikey")
        return False
    
    print(f"✅ GEMINI_API_KEY found (length: {len(api_key)} chars)")
    return True

def run_integration_tests():
    """Run the integration tests with actual LLM calls."""
    
    if not check_api_key():
        return 1
    
    # Change to the project root directory
    project_root = Path(__file__).parent.parent
    
    print("\n🚀 Running Intent Analyzer Integration Tests with Real LLM Calls...")
    print("=" * 70)
    print("⚠️  WARNING: These tests make actual API calls and may incur costs!")
    print("=" * 70)
    
    # Ask for confirmation
    response = input("\nContinue with real API tests? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Tests cancelled by user.")
        return 0
    
    try:
        # Run the integration tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_intent_analyzer_integration.py", 
            "-v",  # Verbose output
            "-s",  # Don't capture output (show prints)
            "-m", "integration",  # Only run integration tests
            "--tb=short",  # Short traceback format
            "--maxfail=5"  # Stop after 5 failures
        ], cwd=project_root, capture_output=False)
        
        print("\n" + "=" * 70)
        if result.returncode == 0:
            print("✅ All integration tests passed!")
        else:
            print(f"❌ Some tests failed (return code: {result.returncode})")
            print("\nCommon issues:")
            print("- API key issues: Check your GEMINI_API_KEY")
            print("- Rate limiting: Wait a moment and try again")
            print("- Network issues: Check your internet connection")
            
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user (Ctrl+C)")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def run_specific_test():
    """Run a specific test method."""
    
    if not check_api_key():
        return 1
    
    tests = {
        "1": "test_perform_intent_analysis_real_llm",
        "2": "test_assess_critical_missing_info_real_llm", 
        "3": "test_generate_clarifying_questions_real_llm",
        "4": "test_full_intent_analysis_pipeline_real_llm",
        "5": "test_llm_failure_handling_real_api"
    }
    
    print("\nAvailable tests:")
    for key, test_name in tests.items():
        print(f"  {key}. {test_name}")
    
    choice = input("\nEnter test number (1-5): ").strip()
    
    if choice not in tests:
        print("❌ Invalid choice")
        return 1
    
    test_name = tests[choice]
    project_root = Path(__file__).parent.parent
    
    print(f"\n🧪 Running specific test: {test_name}")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            f"tests/test_intent_analyzer_integration.py::{test_name}",
            "-v", "-s", "--tb=short"
        ], cwd=project_root, capture_output=False)
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return 1

if __name__ == "__main__":
    print("🤖 Intent Analyzer Integration Test Runner")
    print("Testing with REAL LLM API calls")
    print("=" * 50)
    
    choice = input("\nChoose:\n1. Run all integration tests\n2. Run specific test\nEnter 1 or 2: ").strip()
    
    if choice == "2":
        exit_code = run_specific_test()
    else:
        exit_code = run_integration_tests()
    
    sys.exit(exit_code)
