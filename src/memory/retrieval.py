"""Parallel memory retrieval for optimized performance"""
import asyncio
import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


async def retrieve_user_context(
    user_id: str,
    query: str,
    memory_manager,
) -> Dict:
    """
    Retrieve all user context in parallel for optimal performance

    Parallelizes:
    - Load memory files (~50ms)
    - Mem0 semantic search (~200-300ms)

    Target: <250ms total (limited by slowest operation)

    Args:
        user_id: User's Telegram ID
        query: Current user query for semantic search
        memory_manager: MemoryManager instance

    Returns:
        {
            'memory': {...},  # Profile, preferences, patterns
            'memories': [...],  # Mem0 search results
        }
    """
    start = time.time()

    # Import Mem0 manager
    from src.memory.mem0_manager import mem0_manager

    # Define parallel tasks
    tasks = [
        memory_manager.load_user_memory(user_id),  # ~50ms
        _search_mem0_safely(user_id, query),       # ~200-300ms
    ]

    # Execute in parallel
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results
        user_memory = results[0] if not isinstance(results[0], Exception) else {}
        memories = results[1] if not isinstance(results[1], Exception) else []

        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[MEMORY_RETRIEVAL] Task {i} failed: {result}", exc_info=result)

        elapsed = time.time() - start
        logger.info(f"[MEMORY_RETRIEVAL] Completed in {elapsed:.3f}s (target: <0.250s)")

        return {
            'memory': user_memory,
            'memories': memories,
        }
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"[MEMORY_RETRIEVAL] Failed after {elapsed:.3f}s: {e}", exc_info=True)

        # Return empty results on failure
        return {
            'memory': {},
            'memories': [],
        }


async def _search_mem0_safely(user_id: str, query: str) -> List:
    """
    Search Mem0 with error handling

    Args:
        user_id: User's Telegram ID
        query: Search query

    Returns:
        List of memory results (empty list on error)
    """
    from src.memory.mem0_manager import mem0_manager

    try:
        memories = mem0_manager.search(user_id, query, limit=5)

        # Handle Mem0 returning dict with 'results' key or direct list
        if isinstance(memories, dict):
            memories = memories.get('results', [])

        logger.info(f"[MEM0_RETRIEVAL] Found {len(memories)} memories")
        return memories if memories else []
    except Exception as e:
        logger.error(f"[MEM0_RETRIEVAL] Search failed: {e}", exc_info=True)
        return []
