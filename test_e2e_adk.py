"""
End-to-End Test Script for ADK Pipeline.

Tests the complete research pipeline with a sample query.
"""

from agents.odyssey import root_agent
from google.genai import types
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


# Import our root agent


async def run_end_to_end_test():
    """Run a complete end-to-end test of the research pipeline."""

    print("=" * 70)
    print("🔍 ODYSSEY ENGINE - END-TO-END ADK PIPELINE TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Agent: {root_agent.name}")
    print(f"Sub-agents: {len(root_agent.sub_agents)}")
    for i, agent in enumerate(root_agent.sub_agents, 1):
        print(f"  {i}. {agent.name}")
    print("=" * 70)

    # Simple test query
    test_query = "What are 3 benefits of TypeScript over JavaScript?"

    print(f"\n📝 TEST QUERY:\n{test_query}\n")
    print("-" * 70)

    # Initialize ADK services
    session_service = InMemorySessionService()

    runner = Runner(
        app_name="odyssey_e2e_test",
        agent=root_agent,
        session_service=session_service,
    )

    async with runner:
        # Create session
        session = await session_service.create_session(
            app_name="odyssey_e2e_test",
            user_id="test_user",
            state={"original_query": test_query},
        )

        print(f"📋 Session ID: {session.id}")
        print("-" * 70)

        # Create user message
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=test_query)]
        )

        # Track events
        event_count = 0
        current_stage = None

        print("\n🚀 RUNNING PIPELINE...\n")

        try:
            async for event in runner.run_async(
                user_id="test_user",
                session_id=session.id,
                new_message=user_message,
            ):
                event_count += 1

                # Get author
                author = getattr(event, 'author', 'unknown')

                # Track stage changes
                if author != current_stage:
                    current_stage = author
                    print(f"\n📍 STAGE: {author}")
                    print("-" * 50)

                # Log minimal event info
                if hasattr(event, 'content') and event.content:
                    content = event.content
                    if hasattr(content, 'parts') and content.parts:
                        for part in content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text
                                print(f"  📄 Output: {len(text)} chars")
                                # Show first 300 chars
                                print(f"     Preview: {text[:300]}...")
                            elif hasattr(part, 'function_call') and part.function_call:
                                fc = part.function_call
                                fc_name = getattr(fc, 'name', 'unknown')
                                print(f"  🔧 Tool: {fc_name}")
                            elif hasattr(part, 'function_response') and part.function_response:
                                fr = part.function_response
                                fr_name = getattr(fr, 'name', 'unknown')
                                print(f"  ✅ Tool done: {fr_name}")

                # Limit to prevent runaway
                if event_count > 100:
                    print("\n⚠️ Event limit reached (100)")
                    break

        except Exception as e:
            print(f"\n❌ ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return

        print("\n" + "=" * 70)
        print("📊 RESULTS SUMMARY")
        print("=" * 70)

        # Get final session state
        final_session = await session_service.get_session(
            app_name="odyssey_e2e_test",
            user_id="test_user",
            session_id=session.id,
        )

        state = final_session.state if final_session else {}

        print(f"\n📈 Events processed: {event_count}")

        # Show state keys
        print(f"\n📦 State keys populated:")
        for key in state.keys():
            value = state[key]
            if isinstance(value, str):
                print(f"  • {key}: {len(value)} chars")
            elif isinstance(value, dict):
                print(f"  • {key}: dict with {len(value)} keys")
            elif isinstance(value, list):
                print(f"  • {key}: list with {len(value)} items")
            else:
                print(f"  • {key}: {type(value).__name__}")

        # Show report if generated
        if state.get("report_metadata"):
            metadata = state["report_metadata"]
            if isinstance(metadata, dict) and metadata.get("file_path"):
                print(f"\n📄 Report saved to: {metadata['file_path']}")

        # Show a snippet of the report content
        if state.get("report_content"):
            content = state["report_content"]
            print(f"\n📝 Report Preview (first 1000 chars):")
            print("-" * 50)
            print(content[:1000])
            print("-" * 50)

        print(
            f"\n✅ Pipeline completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_end_to_end_test())
