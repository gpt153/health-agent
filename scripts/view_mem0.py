#!/usr/bin/env python3
"""
View Mem0 semantic memories from the database

Usage:
    python scripts/view_mem0.py [user_id] [--search "query"]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.mem0_manager import mem0_manager
from dotenv import load_dotenv

load_dotenv()


def view_all_memories(user_id: str):
    """View all memories for a user"""
    print(f"\n📚 All Memories for User: {user_id}\n")
    print("=" * 80)

    # Use direct database query to get all memories
    try:
        import psycopg
        from src.config import DATABASE_URL

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        payload->>'data' as memory,
                        payload->>'source' as source,
                        payload->>'metadata' as metadata,
                        payload->>'created_at' as created_at
                    FROM mem0
                    WHERE payload->>'user_id' = %s
                    ORDER BY (payload->>'created_at')::timestamp DESC
                    LIMIT 100
                """, (user_id,))

                results = cur.fetchall()

                if not results:
                    print("No memories found for this user.")
                    return

                for i, row in enumerate(results, 1):
                    memory, source, metadata, created_at = row
                    print(f"\n{i}. {memory}")
                    if source:
                        print(f"   Source: {source}")
                    if metadata:
                        print(f"   Metadata: {metadata}")
                    if created_at:
                        print(f"   Created: {created_at}")
                    print("-" * 80)

                print(f"\n✅ Total memories: {len(results)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def search_memories(user_id: str, query: str):
    """Search memories for a user"""
    print(f"\n🔍 Searching Memories for: '{query}'\n")
    print("=" * 80)

    results = mem0_manager.search(user_id, query, limit=20)

    if isinstance(results, dict):
        memories = results.get('results', [])
    else:
        memories = results

    if not memories:
        print("No matching memories found.")
        return

    for i, mem in enumerate(memories, 1):
        if isinstance(mem, dict):
            memory_text = mem.get('memory', mem.get('text', str(mem)))
            score = mem.get('score', 0)
        else:
            memory_text = str(mem)
            score = 0

        print(f"\n{i}. {memory_text}")
        print(f"   Relevance Score: {score:.3f}")
        print("-" * 80)

    print(f"\n✅ Found {len(memories)} matching memories")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/view_mem0.py [user_id] [--search 'query']")
        print("\nExample:")
        print("  python scripts/view_mem0.py 7376426503")
        print("  python scripts/view_mem0.py 7376426503 --search 'training schedule'")
        sys.exit(1)

    user_id = sys.argv[1]

    if len(sys.argv) > 2 and sys.argv[2] == "--search":
        if len(sys.argv) < 4:
            print("Error: --search requires a query")
            sys.exit(1)
        query = sys.argv[3]
        search_memories(user_id, query)
    else:
        view_all_memories(user_id)
