"""Test agent responses with empty conversation history"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.agent import get_agent_response
from src.memory.file_manager import memory_manager


async def test_query(user_id: str, question: str):
    """Test a single query with empty message history"""
    print(f"\n{'='*60}")
    print(f"❓ Question: {question}")
    print(f"{'='*60}")

    try:
        # Call agent with EMPTY message history
        response = await get_agent_response(
            telegram_id=user_id,
            user_message=question,
            memory_manager=memory_manager,
            reminder_manager=None,
            message_history=[],  # EMPTY - no conversation context!
            bot_application=None
        )

        print(f"✅ Response:\n{response}\n")
        return True

    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


async def main():
    user_id = "7376426503"

    print("🧪 Testing Mem0 + Patterns.md Integration")
    print("=" * 60)
    print("⚠️  Message history is EMPTY - only Mem0 and patterns.md available")
    print("=" * 60)

    # Test questions
    questions = [
        "Vilka dagar gymmar jag?",
        "När vaknar jag på morgonen?",
        "När ska jag ta mina morgoninjektioner?",
    ]

    results = []
    for question in questions:
        success = await test_query(user_id, question)
        results.append((question, success))
        await asyncio.sleep(2)  # Brief pause between tests

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for question, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {question}")

    passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {passed}/{len(results)} tests passed")


if __name__ == "__main__":
    asyncio.run(main())
