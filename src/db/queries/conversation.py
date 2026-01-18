"""Conversation database queries"""
import json
import logging
from typing import Optional
from datetime import datetime
from src.db.connection import db

logger = logging.getLogger(__name__)


async def save_conversation_message(
    user_id: str,
    role: str,
    content: str,
    message_type: str = "text",
    metadata: Optional[dict] = None
) -> None:
    """
    Save a message to conversation history

    Args:
        user_id: Telegram user ID
        role: 'user' or 'assistant'
        content: Message content
        message_type: Type of message (text, image, voice, etc.)
        metadata: Additional metadata (optional)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO conversation_history
                (user_id, role, content, message_type, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, role, content, message_type, json.dumps(metadata) if metadata else None)
            )
            await conn.commit()
    logger.debug(f"Saved {role} message for user {user_id}")


async def get_conversation_history(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    include_metadata: bool = False,
    message_types: Optional[list[str]] = None
) -> list[dict]:
    """
    Get recent conversation history for a user

    Args:
        user_id: Telegram user ID
        limit: Maximum number of messages to return
        offset: Number of messages to skip (for pagination)
        include_metadata: Whether to include metadata field
        message_types: Filter by message types (e.g., ['text', 'image'])

    Returns:
        List of message dicts with keys: id, role, content, timestamp, message_type, (metadata)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Build query dynamically based on parameters
            query = """
                SELECT id, role, content, timestamp, message_type
            """
            if include_metadata:
                query += ", metadata"

            query += """
                FROM conversation_history
                WHERE user_id = %s
            """

            params = [user_id]

            if message_types:
                placeholders = ", ".join(["%s"] * len(message_types))
                query += f" AND message_type IN ({placeholders})"
                params.extend(message_types)

            query += """
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])

            await cur.execute(query, params)
            messages = await cur.fetchall()

            # Reverse to get chronological order (oldest first)
            return list(reversed(messages))


async def clear_conversation_history(user_id: str) -> None:
    """
    Clear all conversation history for a user

    Args:
        user_id: Telegram user ID
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM conversation_history WHERE user_id = %s",
                (user_id,)
            )
            await conn.commit()
    logger.info(f"Cleared conversation history for user {user_id}")
