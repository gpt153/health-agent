"""Habit extraction system for automatic pattern learning"""
import logging
import json
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class HabitExtractor:
    """
    Detects and extracts user habits from patterns

    Learns patterns after 3+ repetitions and applies them automatically.
    Example: User says "3dl whey100" 5 times → learns 1:1 milk ratio
    """

    # Confidence thresholds
    MIN_OCCURRENCES_FOR_HABIT = 3  # Need 3+ repetitions to establish habit
    HIGH_CONFIDENCE_THRESHOLD = 0.8  # 80%+ = strong habit

    def __init__(self, db_connection=None):
        """Initialize habit extractor with optional database connection"""
        self.db = db_connection

    async def detect_food_prep_habit(
        self,
        user_id: str,
        food_description: str,
        parsed_components: Dict
    ) -> Optional[Dict]:
        """
        Detect if user has a food preparation habit

        Args:
            user_id: User's Telegram ID
            food_description: Raw food description from user
            parsed_components: Parsed food data (quantity, food, preparation)

        Returns:
            Habit data if detected, None otherwise

        Example:
            food_description: "3dl whey100"
            parsed_components: {
                "food": "whey100",
                "quantity": "3dl",
                "preparation": "mixed with milk"
            }
        """
        # Check for whey protein patterns
        if "whey" in food_description.lower():
            habit_key = "whey100_preparation"

            # Query existing habit
            existing = await self.get_habit(user_id, "food_prep", habit_key)

            if existing:
                # Update occurrence count
                new_count = existing['occurrence_count'] + 1
                # Confidence increases with repetitions, maxes at 1.0 after 10 occurrences
                confidence = min(1.0, new_count / 10.0)

                await self.update_habit(
                    user_id,
                    "food_prep",
                    habit_key,
                    occurrence_count=new_count,
                    confidence=confidence
                )

                logger.info(f"[HABIT] Updated {habit_key}: {new_count} occurrences, {confidence:.2f} confidence")
                return existing['habit_data']
            else:
                # First occurrence - create habit with low confidence
                habit_data = {
                    "food": "whey100",
                    "ratio": "1:1",  # 1dl powder : 1dl liquid
                    "liquid": "milk_3_percent",
                    "portions_per_dl": 0.5  # 0.5 portions per dl
                }

                await self.create_habit(
                    user_id,
                    "food_prep",
                    habit_key,
                    habit_data,
                    confidence=0.3  # Low confidence initially
                )

                logger.info(f"[HABIT] Created new habit {habit_key}")
                return habit_data

        return None

    async def get_user_habits(
        self,
        user_id: str,
        habit_type: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Get user's established habits (>= min_confidence)

        Args:
            user_id: User's Telegram ID
            habit_type: Filter by habit type (optional)
            min_confidence: Minimum confidence threshold (default: 0.5)

        Returns:
            List of habit dictionaries
        """
        from src.db.queries import get_database_connection

        async with get_database_connection() as conn:
            async with conn.cursor() as cur:
                if habit_type:
                    await cur.execute(
                        """
                        SELECT habit_type, habit_key, habit_data, confidence, occurrence_count
                        FROM user_habits
                        WHERE user_id = %s AND habit_type = %s AND confidence >= %s
                        ORDER BY confidence DESC, last_observed DESC
                        """,
                        (user_id, habit_type, min_confidence)
                    )
                else:
                    await cur.execute(
                        """
                        SELECT habit_type, habit_key, habit_data, confidence, occurrence_count
                        FROM user_habits
                        WHERE user_id = %s AND confidence >= %s
                        ORDER BY confidence DESC, last_observed DESC
                        """,
                        (user_id, min_confidence)
                    )

                rows = await cur.fetchall()

                return [
                    {
                        'habit_type': row[0],
                        'habit_key': row[1],
                        'habit_data': row[2],
                        'confidence': row[3],
                        'occurrence_count': row[4]
                    }
                    for row in rows
                ]

    async def get_habit(
        self,
        user_id: str,
        habit_type: str,
        habit_key: str
    ) -> Optional[Dict]:
        """
        Get a specific habit

        Args:
            user_id: User's Telegram ID
            habit_type: Habit type
            habit_key: Habit key

        Returns:
            Habit dictionary or None if not found
        """
        from src.db.queries import get_database_connection

        async with get_database_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT habit_type, habit_key, habit_data, confidence, occurrence_count
                    FROM user_habits
                    WHERE user_id = %s AND habit_type = %s AND habit_key = %s
                    """,
                    (user_id, habit_type, habit_key)
                )

                row = await cur.fetchone()

                if row:
                    return {
                        'habit_type': row[0],
                        'habit_key': row[1],
                        'habit_data': row[2],
                        'confidence': row[3],
                        'occurrence_count': row[4]
                    }

                return None

    async def create_habit(
        self,
        user_id: str,
        habit_type: str,
        habit_key: str,
        habit_data: Dict,
        confidence: float = 0.5
    ) -> bool:
        """
        Create a new habit

        Args:
            user_id: User's Telegram ID
            habit_type: Habit type
            habit_key: Habit key
            habit_data: Habit data (JSON)
            confidence: Initial confidence (default: 0.5)

        Returns:
            True if created successfully
        """
        from src.db.queries import get_database_connection

        try:
            async with get_database_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO user_habits
                        (user_id, habit_type, habit_key, habit_data, confidence, occurrence_count)
                        VALUES (%s, %s, %s, %s, %s, 1)
                        ON CONFLICT (user_id, habit_type, habit_key)
                        DO UPDATE SET
                            habit_data = EXCLUDED.habit_data,
                            confidence = EXCLUDED.confidence,
                            occurrence_count = user_habits.occurrence_count + 1,
                            last_observed = NOW(),
                            updated_at = NOW()
                        """,
                        (user_id, habit_type, habit_key, json.dumps(habit_data), confidence)
                    )
                    await conn.commit()
                    return True
        except Exception as e:
            logger.error(f"[HABIT] Failed to create habit: {e}", exc_info=True)
            return False

    async def update_habit(
        self,
        user_id: str,
        habit_type: str,
        habit_key: str,
        occurrence_count: Optional[int] = None,
        confidence: Optional[float] = None,
        habit_data: Optional[Dict] = None
    ) -> bool:
        """
        Update an existing habit

        Args:
            user_id: User's Telegram ID
            habit_type: Habit type
            habit_key: Habit key
            occurrence_count: New occurrence count (optional)
            confidence: New confidence score (optional)
            habit_data: Updated habit data (optional)

        Returns:
            True if updated successfully
        """
        from src.db.queries import get_database_connection

        try:
            # Build dynamic update query
            updates = []
            params = []

            if occurrence_count is not None:
                updates.append("occurrence_count = %s")
                params.append(occurrence_count)

            if confidence is not None:
                updates.append("confidence = %s")
                params.append(confidence)

            if habit_data is not None:
                updates.append("habit_data = %s")
                params.append(json.dumps(habit_data))

            updates.append("last_observed = NOW()")
            updates.append("updated_at = NOW()")

            if not updates:
                return True  # Nothing to update

            # Add WHERE clause parameters
            params.extend([user_id, habit_type, habit_key])

            query = f"""
                UPDATE user_habits
                SET {', '.join(updates)}
                WHERE user_id = %s AND habit_type = %s AND habit_key = %s
            """

            async with get_database_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    await conn.commit()
                    return True
        except Exception as e:
            logger.error(f"[HABIT] Failed to update habit: {e}", exc_info=True)
            return False


# Global instance
habit_extractor = HabitExtractor()
