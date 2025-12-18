#!/usr/bin/env python3
"""Mem0 Memory Management Tool - View, edit, and delete memories"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.memory.mem0_manager import mem0_manager
import argparse

def list_memories(user_id: str, limit: int = 50):
    """List all memories for a user"""
    try:
        # Ensure mem0 is initialized
        mem0_manager._ensure_initialized()
        
        # Get all memories via database query
        from src.db.connection import db
        
        async def get_memories():
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT id, payload->>'data' as memory, payload->>'metadata' as metadata
                        FROM mem0 
                        WHERE payload->>'user_id' = %s
                        ORDER BY id DESC
                        LIMIT %s
                        """,
                        (user_id, limit)
                    )
                    return await cur.fetchall()
        
        import asyncio
        memories = asyncio.run(get_memories())
        
        if not memories:
            print(f"No memories found for user {user_id}")
            return
        
        print(f"\n📝 Memories for user {user_id}:")
        print("=" * 80)
        for i, mem in enumerate(memories, 1):
            memory_id = str(mem['id'])
            memory_text = mem['memory']
            print(f"\n{i}. ID: {memory_id}")
            print(f"   Memory: {memory_text}")
            print(f"   {'-' * 76}")
        
        print(f"\nTotal: {len(memories)} memories")
        
    except Exception as e:
        print(f"❌ Error listing memories: {e}")
        import traceback
        traceback.print_exc()


def search_memories(user_id: str, query: str, limit: int = 10):
    """Search memories"""
    try:
        mem0_manager._ensure_initialized()
        results = mem0_manager.search(user_id, query, limit=limit)
        
        if isinstance(results, dict):
            memories = results.get('results', [])
        else:
            memories = results if results else []
        
        if not memories:
            print(f"No memories found matching '{query}'")
            return
        
        print(f"\n🔍 Search results for '{query}':")
        print("=" * 80)
        for i, mem in enumerate(memories, 1):
            if isinstance(mem, dict):
                memory_text = mem.get('memory', mem.get('text', str(mem)))
                score = mem.get('score', 'N/A')
                print(f"\n{i}. [Score: {score:.3f if isinstance(score, float) else score}]")
                print(f"   {memory_text}")
        
    except Exception as e:
        print(f"❌ Error searching memories: {e}")
        import traceback
        traceback.print_exc()


def delete_memory(user_id: str, memory_id: str):
    """Delete a specific memory"""
    try:
        mem0_manager._ensure_initialized()
        
        # Delete from database directly
        from src.db.connection import db
        import asyncio
        
        async def delete():
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM mem0 WHERE id = %s", (memory_id,))
                    conn.commit()
        
        asyncio.run(delete())
        print(f"✅ Deleted memory {memory_id}")
    except Exception as e:
        print(f"❌ Error deleting memory: {e}")


def add_memory(user_id: str, text: str):
    """Add a new memory"""
    try:
        mem0_manager._ensure_initialized()
        mem0_manager.add_message(user_id, text, role="user", metadata={"source": "manual_add"})
        print(f"✅ Added memory: {text}")
    except Exception as e:
        print(f"❌ Error adding memory: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Manage Mem0 memories")
    parser.add_argument("user_id", help="Telegram user ID")
    parser.add_argument("action", choices=["list", "search", "delete", "add"], help="Action to perform")
    parser.add_argument("--query", help="Search query (for search)")
    parser.add_argument("--id", help="Memory ID (for delete)")
    parser.add_argument("--text", help="Memory text (for add)")
    parser.add_argument("--limit", type=int, default=50, help="Limit results (default: 50)")
    
    args = parser.parse_args()
    
    if args.action == "list":
        list_memories(args.user_id, args.limit)
    
    elif args.action == "search":
        if not args.query:
            print("❌ --query required for search")
            return
        search_memories(args.user_id, args.query, args.limit)
    
    elif args.action == "delete":
        if not args.id:
            print("❌ --id required for delete")
            return
        confirm = input(f"Delete memory {args.id}? (yes/no): ")
        if confirm.lower() == "yes":
            delete_memory(args.user_id, args.id)
    
    elif args.action == "add":
        if not args.text:
            print("❌ --text required for add")
            return
        add_memory(args.user_id, args.text)


if __name__ == "__main__":
    main()
