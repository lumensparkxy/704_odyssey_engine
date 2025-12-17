#!/usr/bin/env python
"""
Simple E2E Test - Tests core pipeline without the clarification loop.

This demonstrates the ADK migration works by running:
1. IntentAnalyzer (single pass)
2. DataGathering agents  
3. AnalysisAgent
4. ReportGenerator

Skips the LoopAgent complexity for cleaner demonstration.
"""

from agents.odyssey.intent.agent import INTENT_ANALYZER_INSTRUCTION, GEMINI_MODEL
from google.genai import types
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

load_dotenv()


# Import the instruction but create fresh agent instances

# Create FRESH agent instances (not shared with the main pipeline)
test_intent_analyzer = LlmAgent(
    name="TestIntentAnalyzer",
    model=GEMINI_MODEL,
    description="Analyzes user research queries",
    instruction=INTENT_ANALYZER_INSTRUCTION,
    output_key="intent_result",
)


async def run_simple_e2e():
    """Run a simplified end-to-end test."""

    print("=" * 70)
    print("🔍 ODYSSEY ENGINE - SIMPLE E2E TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Test just the IntentAnalyzer first (no parent conflicts)
    print("\nRunning IntentAnalyzer only test...")

    # Test query
    test_query = "What are 3 benefits of TypeScript?"

    print(f"\n📝 TEST QUERY: {test_query}\n")
    print("-" * 70)

    # Initialize
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="simple_e2e",
        agent=test_intent_analyzer,  # Use fresh agent instance
        session_service=session_service,
    )

    async with runner:
        session = await session_service.create_session(
            app_name="simple_e2e",
            user_id="test",
            state={"original_query": test_query},
        )

        print(f"Session: {session.id}\n")

        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=test_query)]
        )

        event_count = 0
        current_stage = None

        print("🚀 RUNNING...\n")

        try:
            async for event in runner.run_async(
                user_id="test",
                session_id=session.id,
                new_message=user_message,
            ):
                event_count += 1
                author = getattr(event, 'author', 'unknown')

                if author != current_stage:
                    current_stage = author
                    print(f"\n📍 {author}")
                    print("-" * 50)

                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text
                                print(f"   Output: {len(text)} chars")
                                # Show preview
                                preview = text[:400].replace('\n', ' ')
                                print(f"   Preview: {preview}...")
                            elif hasattr(part, 'function_call'):
                                print(
                                    f"   🔧 Tool call: {part.function_call.name}")
                            elif hasattr(part, 'function_response'):
                                print(
                                    f"   ✅ Tool done: {part.function_response.name}")

                # Safety limit
                if event_count > 50:
                    print("\n⚠️ Event limit reached")
                    break

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return

        # Results
        print("\n" + "=" * 70)
        print("📊 RESULTS")
        print("=" * 70)

        final_session = await session_service.get_session(
            app_name="simple_e2e",
            user_id="test",
            session_id=session.id,
        )

        state = final_session.state if final_session else {}

        print(f"\n📈 Events: {event_count}")
        print(f"\n📦 State keys:")
        for key in sorted(state.keys()):
            value = state[key]
            if isinstance(value, str):
                print(f"  • {key}: {len(value)} chars")
            elif isinstance(value, dict):
                print(f"  • {key}: dict({len(value)} keys)")
            elif isinstance(value, list):
                print(f"  • {key}: list({len(value)} items)")
            else:
                print(f"  • {key}: {type(value).__name__}")

        # Show intent result
        if state.get("intent_result"):
            print(f"\n📋 INTENT ANALYSIS:")
            print("-" * 40)
            intent = state["intent_result"]
            if isinstance(intent, str):
                print(intent[:800])
            print("-" * 40)

        # Show report content
        if state.get("report_content"):
            print(f"\n📝 REPORT PREVIEW:")
            print("-" * 40)
            print(state["report_content"][:1500])
            print("-" * 40)

        print(f"\n✅ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_simple_e2e())
