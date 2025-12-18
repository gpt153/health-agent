"""One-time migration: Seed existing patterns.md files into Mem0"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.memory.mem0_manager import mem0_manager


async def seed_patterns_for_user(user_id: str):
    """Seed patterns.md content into Mem0 for a user"""
    patterns_file = Path(f"data/{user_id}/patterns.md")

    if not patterns_file.exists():
        print(f"❌ No patterns.md found for user {user_id}")
        return

    # Read patterns content
    with open(patterns_file, 'r') as f:
        patterns_content = f.read()

    if not patterns_content.strip() or len(patterns_content) < 50:
        print(f"⚠️  Patterns file for {user_id} is too short, skipping")
        return

    print(f"📝 Seeding patterns for user {user_id}...")
    print(f"   Content length: {len(patterns_content)} characters")

    # Add patterns to Mem0 as an assistant message
    # This allows Mem0 to extract facts from the structured data
    mem0_manager.add_message(
        user_id=user_id,
        message=f"Here is the user's patterns and schedules:\n\n{patterns_content}",
        role="assistant",
        metadata={"source": "patterns.md", "migration": True}
    )

    print(f"✅ Seeded patterns for user {user_id}")


async def main():
    """Seed patterns for all users"""
    print("🌱 Starting Mem0 seeding from patterns.md files...\n")

    data_dir = Path("data")
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return

    # Find all user directories
    user_dirs = [d for d in data_dir.iterdir() if d.is_dir() and d.name.isdigit()]

    if not user_dirs:
        print("❌ No user directories found in data/")
        return

    print(f"Found {len(user_dirs)} user(s)")
    print("=" * 50)

    for user_dir in user_dirs:
        user_id = user_dir.name
        await seed_patterns_for_user(user_id)
        print()

    print("=" * 50)
    print("✨ Seeding complete!")
    print("\nYou can now ask the bot about training schedules, etc.")


if __name__ == "__main__":
    asyncio.run(main())
