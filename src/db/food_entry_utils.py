"""
Enhanced food entry utilities with mem0 synchronization
Fixes Issue #22: Food corrections not persisting across all systems
"""
import json
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from src.db import queries
from src.memory.mem0_manager import mem0_manager

logger = logging.getLogger(__name__)


async def update_food_entry_with_memory_sync(
    entry_id: str,
    user_id: str,
    total_calories: Optional[int] = None,
    total_macros: Optional[dict] = None,
    foods: Optional[list] = None,
    correction_note: Optional[str] = None,
    corrected_by: str = "user"
) -> Dict[str, Any]:
    """
    Update food entry and synchronize with mem0 memory system

    This ensures corrections are reflected across:
    1. PostgreSQL food_entries table
    2. Mem0 semantic memory
    3. Audit trail

    Args:
        entry_id: UUID of the food entry to update
        user_id: Telegram user ID
        total_calories: New total calories
        total_macros: New macros dict {protein, carbs, fat}
        foods: New foods list
        correction_note: Reason for correction
        corrected_by: 'user' or 'auto'

    Returns:
        dict with success status, old/new values, and memory sync status
    """
    # 1. Update PostgreSQL (includes audit trail)
    result = await queries.update_food_entry(
        entry_id=entry_id,
        user_id=user_id,
        total_calories=total_calories,
        total_macros=total_macros,
        foods=foods,
        correction_note=correction_note,
        corrected_by=corrected_by
    )

    if not result.get("success"):
        return result

    # 2. Synchronize with mem0
    try:
        # Search for memories related to this food entry
        old_memories = mem0_manager.search(
            user_id=user_id,
            query=f"food entry {entry_id}",
            limit=10
        )

        # Delete old memories about this specific entry
        deleted_count = 0
        for memory in old_memories:
            # Check if memory metadata references this entry_id
            metadata = memory.get('metadata', {})
            if isinstance(metadata, dict) and metadata.get('entry_id') == entry_id:
                mem0_manager.delete_memory(memory['id'])
                deleted_count += 1
                logger.info(f"Deleted outdated mem0 memory: {memory['id']}")

        # Create new corrected memory
        old_cals = result['old_values']['total_calories']
        new_cals = result['new_values']['total_calories']

        # Extract food names for memory
        food_names = []
        if foods:
            for food in foods:
                if isinstance(food, dict):
                    food_names.append(food.get('name', 'unknown'))

        food_description = ', '.join(food_names) if food_names else "meal"

        correction_message = (
            f"User corrected food entry: {food_description}. "
            f"Original estimate: {old_cals} calories, "
            f"corrected to: {new_cals} calories. "
            f"This is a user-verified value (higher confidence). "
        )

        if correction_note:
            correction_message += f"Reason: {correction_note}"

        # Add corrected memory with high-confidence metadata
        mem0_manager.add_message(
            user_id=user_id,
            message=correction_message,
            role="system",  # System message for factual updates
            metadata={
                'entry_id': entry_id,
                'type': 'food_correction',
                'verified': True,
                'corrected_by': corrected_by,
                'confidence': 'high'
            }
        )

        result['memory_sync'] = {
            'deleted_memories': deleted_count,
            'new_memory_added': True,
            'status': 'success'
        }

        logger.info(
            f"Mem0 sync completed for entry {entry_id}: "
            f"deleted {deleted_count} old memories, added 1 corrected memory"
        )

    except Exception as e:
        logger.error(f"Failed to sync mem0 for entry {entry_id}: {e}", exc_info=True)
        result['memory_sync'] = {
            'status': 'failed',
            'error': str(e)
        }

    return result


async def save_food_entry_with_memory(
    entry,  # FoodEntry model
    context: Optional[str] = None
) -> None:
    """
    Save food entry to PostgreSQL and create mem0 memory

    Args:
        entry: FoodEntry Pydantic model
        context: Optional context about the meal (e.g., "lunch with friends")
    """
    # 1. Save to PostgreSQL
    await queries.save_food_entry(entry)

    # 2. Create mem0 memory
    try:
        food_names = [f.name for f in entry.foods]
        food_description = ', '.join(food_names)

        memory_message = (
            f"User logged {entry.meal_type or 'a meal'}: {food_description}. "
            f"Total: {entry.total_calories} calories, "
            f"{entry.total_macros.protein}g protein, "
            f"{entry.total_macros.carbs}g carbs, "
            f"{entry.total_macros.fat}g fat."
        )

        if entry.notes:
            memory_message += f" Notes: {entry.notes}"

        if context:
            memory_message += f" Context: {context}"

        mem0_manager.add_message(
            user_id=entry.user_id,
            message=memory_message,
            role="system",
            metadata={
                'entry_id': str(entry.id),
                'type': 'food_log',
                'meal_type': entry.meal_type,
                'verified': False  # Not user-verified yet
            }
        )

        logger.info(f"Created mem0 memory for food entry {entry.id}")

    except Exception as e:
        logger.error(f"Failed to create mem0 memory for entry {entry.id}: {e}", exc_info=True)
        # Don't fail the entire operation if memory creation fails


async def get_food_entry_with_context(
    entry_id: str,
    user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get food entry with related memories for full context

    Returns:
        dict with entry data and related memories
    """
    # Get entry from PostgreSQL
    async with queries.db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, timestamp, photo_path, foods, total_calories,
                       total_macros, meal_type, notes, correction_note, corrected_by
                FROM food_entries
                WHERE id = %s AND user_id = %s
                """,
                (entry_id, user_id)
            )
            row = await cur.fetchone()

            if not row:
                return None

            entry = dict(row)

    # Get related memories
    try:
        memories = mem0_manager.search(
            user_id=user_id,
            query=f"food entry {entry_id}",
            limit=5
        )

        entry['related_memories'] = [
            {
                'id': m['id'],
                'memory': m['memory'],
                'metadata': m.get('metadata', {})
            }
            for m in memories
        ]

    except Exception as e:
        logger.error(f"Failed to fetch memories for entry {entry_id}: {e}")
        entry['related_memories'] = []

    return entry
