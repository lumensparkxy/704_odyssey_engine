#!/usr/bin/env python3
"""
Test runner for Intent Analyzer tests.
Run this to specifically test the _generate_clarifying_questions method.
"""

import subprocess
import sys
from pathlib import Path

def run_intent_analyzer_tests():
    """Run the intent analyzer tests specifically."""
    
    # Change to the project root directory
    project_root = Path(__file__).parent.parent
    
    print("🧪 Running Intent Analyzer Tests...")
    print("=" * 50)
    
    try:
        # Run the specific test file
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_intent_analyzer.py", 
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "-s"  # Don't capture output
        ], cwd=project_root, capture_output=False)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with return code: {result.returncode}")
            
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_intent_analyzer_tests()
    sys.exit(exit_code)
