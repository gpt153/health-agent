"""Fixed seeding script that properly saves to Mem0"""
import asyncio
import os
import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.memory.mem0_manager import mem0_manager


def seed_patterns_for_user(user_id: str):
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

    # Extract key facts to seed
    lines = patterns_content.split('\n')
    facts_to_seed = []

    current_section = ""
    for line in lines:
        if line.startswith('## '):
            current_section = line.replace('##', '').strip()
        elif line.strip() and line.startswith('- ') and current_section:
            fact = f"{current_section}: {line.strip()[2:]}"
            facts_to_seed.append(fact)

    print(f"   Extracted {len(facts_to_seed)} facts")

    # Add each fact individually to Mem0
    for fact in facts_to_seed:
        try:
            mem0_manager.add_message(
                user_id=user_id,
                message=fact,
                role="user",
                metadata={"source": "patterns.md", "migration": True}
            )
            print(f"   ✓ Added: {fact[:60]}...")
            time.sleep(0.1)  # Small delay to ensure processing
        except Exception as e:
            print(f"   ✗ Failed to add fact: {e}")

    # Also add the full Training Schedule section
    if "Training Schedule" in patterns_content:
        import re
        match = re.search(r'## Training Schedule\n(.*?)(?=\n##|\Z)', patterns_content, re.DOTALL)
        if match:
            training_info = match.group(1).strip()
            try:
                mem0_manager.add_message(
                    user_id=user_id,
                    message=f"My training schedule: {training_info}",
                    role="user",
                    metadata={"source": "patterns.md", "section": "training", "migration": True}
                )
                print(f"   ✓ Added full training schedule")
                time.sleep(0.5)  # Extra delay for this important one
            except Exception as e:
                print(f"   ✗ Failed to add training schedule: {e}")

    print(f"✅ Seeded patterns for user {user_id}")


def main():
    """Seed patterns for all users"""
    print("🌱 Starting FIXED Mem0 seeding from patterns.md files...\n")

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
        seed_patterns_for_user(user_id)
        print()

    print("=" * 50)
    print("✨ Seeding complete!")

    # Verify seeding worked
    print("\n🔍 Verifying data was saved...")
    import psycopg
    conn = psycopg.connect("postgresql://postgres:postgres@localhost:5434/health_agent")
    cur = conn.cursor()
    for user_dir in user_dirs:
        user_id = user_dir.name
        cur.execute("SELECT COUNT(*) FROM mem0 WHERE payload->>'user_id' = %s", (user_id,))
        count = cur.fetchone()[0]
        print(f"   User {user_id}: {count} memories in database")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
