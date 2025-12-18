"""Test new unanticipated questions with XML-structured prompts"""
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
        import traceback
        traceback.print_exc()
        return False


async def main():
    user_id = "7376426503"

    print("🧪 Testing NEW UNANTICIPATED Questions")
    print("=" * 60)
    print("⚠️  Testing XML-structured prompts with questions we haven't coded")
    print("=" * 60)

    # NEW test questions we haven't explicitly coded for
    questions = [
        "Hur mycket kaffe dricker jag?",
        "Vad är mina kaloriintag på träningsdagar?",
        "När går jag och lägger mig?",
        "Vilka dagar är mina vilodar?",  # Rest days - inverse of training days
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

    if passed == len(results):
        print("\n✅ ALL TESTS PASSED - XML structure is working!")
        print("If Telegram still fails, there's a Telegram bot issue.")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed - need to improve prompts")


if __name__ == "__main__":
    asyncio.run(main())
