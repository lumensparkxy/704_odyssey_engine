#!/usr/bin/env python
"""Test a single agent to validate ADK integration."""
from agents.odyssey.intent.agent import intent_analyzer_agent as IntentAnalyzerAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
import asyncio
import os
import sys

# Set environment
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "false")

# Add src to path
sys.path.insert(0, '/Users/admin/learn_python/704_odyssey_engine/src')


# Import the intent analyzer agent


async def test_single_agent():
    """Test IntentAnalyzerAgent directly."""
    print("=" * 60)
    print("🧪 SINGLE AGENT TEST: IntentAnalyzerAgent")
    print("=" * 60)

    # Create runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=IntentAnalyzerAgent,
        app_name="test_intent",
        session_service=session_service
    )

    # Create session
    session = await session_service.create_session(
        app_name="test_intent",
        user_id="test_user"
    )

    query = "What are 3 benefits of TypeScript?"
    print(f"\n📝 Query: {query}")
    print(f"📋 Session: {session.id}")
    print("\n🚀 Running agent...\n")

    from google.genai import types
    content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )

    event_count = 0
    final_response = None

    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content
    ):
        event_count += 1
        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'parts') and event.content.parts:
                text = event.content.parts[0].text
                if text:
                    final_response = text
                    print(f"📄 Response ({len(text)} chars)")

    print("\n" + "=" * 60)
    print(f"✅ COMPLETED - {event_count} events processed")
    print("=" * 60)

    if final_response:
        print("\n📋 RESPONSE PREVIEW:")
        print("-" * 40)
        print(final_response[:1500] +
              "..." if len(final_response) > 1500 else final_response)
        print("-" * 40)

    return final_response

if __name__ == "__main__":
    result = asyncio.run(test_single_agent())
    print("\n✅ Test completed successfully!" if result else "\n❌ No response received")
