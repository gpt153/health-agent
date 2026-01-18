"""
FoodService - Food Tracking Business Logic

Handles food photo analysis, meal logging, nutrition validation, and habits.
Separates food business logic from Telegram handlers.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import json

from src.models.food import FoodEntry, VisionAnalysisResult, FoodMacros
from src.db import queries
from src.utils.vision import analyze_food_photo
from src.utils.nutrition_search import verify_food_items
from src.agent.nutrition_validator import get_validator
from src.memory.mem0_manager import mem0_manager
from src.memory.habit_extractor import habit_extractor

logger = logging.getLogger(__name__)


class FoodService:
    """
    Service for food tracking and analysis.

    Responsibilities:
    - Food photo analysis coordination with vision AI
    - Nutrition validation with USDA database
    - Meal logging and retrieval
    - Food entry corrections
    - Integration with Mem0, habits, and food history
    """

    def __init__(self, db_connection, memory_manager):
        """
        Initialize FoodService.

        Args:
            db_connection: Database connection instance
            memory_manager: MemoryFileManager instance
        """
        self.db = db_connection
        self.memory = memory_manager
        logger.debug("FoodService initialized")

    async def analyze_food_photo(
        self,
        user_id: str,
        photo_path: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze food photo with full personalization and validation.

        Orchestrates the complete food analysis pipeline:
        1. Load user visual patterns
        2. Search semantic memory (Mem0)
        3. Get recent food history (7 days)
        4. Load food preparation habits
        5. Run vision AI analysis
        6. Verify with USDA database
        7. Multi-agent validation
        8. Return validated results

        Args:
            user_id: Telegram user ID
            photo_path: Path to saved photo file
            caption: Optional user-provided description

        Returns:
            dict: {
                'foods': List[FoodItem],  # Validated food items
                'total_calories': int,
                'total_macros': FoodMacros,
                'confidence': str,
                'validation_warnings': List[str],
                'clarifying_questions': List[str],
                'timestamp': datetime
            }
        """
        try:
            logger.info(f"Analyzing food photo for user {user_id}")

            # 1. Load user's visual patterns
            user_memory = await self.memory.load_user_memory(user_id)
            visual_patterns = user_memory.get("visual_patterns", "")

            # 2. Search semantic memory (Mem0)
            mem0_context = await self._get_mem0_context(user_id, caption)

            # 3. Get recent food history
            food_history_context = await self._get_food_history_context(user_id)

            # 4. Load food preparation habits
            habit_context = await self._get_habit_context(user_id)

            # 5. Run vision AI analysis with all context
            analysis = await analyze_food_photo(
                photo_path,
                caption=caption,
                user_id=user_id,
                visual_patterns=visual_patterns,
                semantic_context=mem0_context,
                food_history=food_history_context,
                food_habits=habit_context
            )

            # 6. Verify with USDA database
            verified_foods = await verify_food_items(analysis.foods)

            # 7. Multi-agent validation
            validator = get_validator()
            validated_analysis, validation_warnings = await validator.validate(
                vision_result=analysis,
                photo_path=photo_path,
                caption=caption,
                visual_patterns=visual_patterns,
                usda_verified_items=verified_foods,
                enable_cross_validation=True
            )

            # 8. Calculate totals from validated data
            total_calories = sum(f.calories for f in validated_analysis.foods)
            total_protein = sum(f.macros.protein for f in validated_analysis.foods)
            total_carbs = sum(f.macros.carbs for f in validated_analysis.foods)
            total_fat = sum(f.macros.fat for f in validated_analysis.foods)

            total_macros = FoodMacros(
                protein=total_protein,
                carbs=total_carbs,
                fat=total_fat
            )

            # Extract timestamp (from caption or current time)
            entry_timestamp = analysis.timestamp if analysis.timestamp else datetime.now()

            logger.info(f"Food analysis complete: {len(validated_analysis.foods)} items, {total_calories} cal")

            return {
                'foods': validated_analysis.foods,
                'total_calories': total_calories,
                'total_macros': total_macros,
                'confidence': validated_analysis.confidence,
                'validation_warnings': validation_warnings or [],
                'clarifying_questions': validated_analysis.clarifying_questions or [],
                'timestamp': entry_timestamp
            }

        except Exception as e:
            logger.error(f"Error analyzing food photo for {user_id}: {e}", exc_info=True)
            raise

    async def log_food_entry(
        self,
        user_id: str,
        photo_path: str,
        foods: List,
        total_calories: int,
        total_macros: FoodMacros,
        timestamp: datetime,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save food entry to database and trigger habit detection.

        Args:
            user_id: Telegram user ID
            photo_path: Path to photo file
            foods: List of FoodItem objects (validated)
            total_calories: Total calories
            total_macros: Total macros (FoodMacros object)
            timestamp: Entry timestamp
            notes: Optional notes/caption

        Returns:
            dict: {
                'success': bool,
                'entry_id': str,
                'message': str
            }
        """
        try:
            # Create FoodEntry object
            entry = FoodEntry(
                user_id=user_id,
                timestamp=timestamp,
                photo_path=photo_path,
                foods=foods,
                total_calories=total_calories,
                total_macros=total_macros,
                meal_type=None,  # Can be inferred from time
                notes=notes
            )

            # Save to database
            await queries.save_food_entry(entry)
            logger.info(f"Saved food entry for {user_id}, entry_id: {entry.id}")

            # Trigger habit detection for food patterns
            await self._detect_food_habits(user_id, entry.foods)

            return {
                'success': True,
                'entry_id': str(entry.id),
                'entry': entry,
                'message': 'Food entry saved successfully'
            }

        except Exception as e:
            logger.error(f"Error logging food entry for {user_id}: {e}", exc_info=True)
            return {
                'success': False,
                'entry_id': None,
                'message': f'Error saving food entry: {str(e)}'
            }

    async def get_food_entries(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get food entries for user within date range.

        Args:
            user_id: Telegram user ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of entries

        Returns:
            List of food entry dicts
        """
        try:
            if start_date and end_date:
                entries = await queries.get_food_entries_by_date(
                    user_id,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
            else:
                entries = await queries.get_recent_food_entries(user_id, limit)

            return entries or []

        except Exception as e:
            logger.error(f"Error getting food entries for {user_id}: {e}", exc_info=True)
            return []

    async def get_daily_nutrition_summary(
        self,
        user_id: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        Calculate nutrition totals for a specific day.

        Args:
            user_id: Telegram user ID
            target_date: Date to summarize

        Returns:
            dict: {
                'date': str,
                'total_calories': int,
                'total_protein': float,
                'total_carbs': float,
                'total_fat': float,
                'meal_count': int,
                'entries': List[dict]
            }
        """
        try:
            entries = await queries.get_food_entries_by_date(
                user_id,
                target_date.strftime('%Y-%m-%d'),
                target_date.strftime('%Y-%m-%d')
            )

            if not entries:
                return {
                    'date': target_date.isoformat(),
                    'total_calories': 0,
                    'total_protein': 0.0,
                    'total_carbs': 0.0,
                    'total_fat': 0.0,
                    'meal_count': 0,
                    'entries': []
                }

            # Sum up totals
            total_calories = 0
            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0

            for entry in entries:
                total_calories += entry.get('total_calories', 0)

                # Parse total_macros JSON
                macros_json = entry.get('total_macros', '{}')
                if isinstance(macros_json, str):
                    macros = json.loads(macros_json)
                else:
                    macros = macros_json

                total_protein += macros.get('protein', 0.0)
                total_carbs += macros.get('carbs', 0.0)
                total_fat += macros.get('fat', 0.0)

            return {
                'date': target_date.isoformat(),
                'total_calories': total_calories,
                'total_protein': round(total_protein, 1),
                'total_carbs': round(total_carbs, 1),
                'total_fat': round(total_fat, 1),
                'meal_count': len(entries),
                'entries': entries
            }

        except Exception as e:
            logger.error(f"Error calculating daily summary for {user_id}: {e}", exc_info=True)
            return {
                'date': target_date.isoformat(),
                'total_calories': 0,
                'total_protein': 0.0,
                'total_carbs': 0.0,
                'total_fat': 0.0,
                'meal_count': 0,
                'entries': [],
                'error': str(e)
            }

    # Private helper methods

    async def _get_mem0_context(self, user_id: str, caption: Optional[str]) -> str:
        """Get relevant food context from Mem0 semantic memory"""
        try:
            query = f"food photo {caption if caption else 'meal'}"
            food_memories = mem0_manager.search(user_id, query=query, limit=5)

            # Handle Mem0 returning dict with 'results' key or direct list
            if isinstance(food_memories, dict):
                food_memories = food_memories.get('results', [])

            if food_memories:
                context = "\n\n**Relevant context from past conversations:**\n"
                for mem in food_memories:
                    if isinstance(mem, dict):
                        memory_text = mem.get('memory', mem.get('text', str(mem)))
                    elif isinstance(mem, str):
                        memory_text = mem
                    else:
                        memory_text = str(mem)
                    context += f"- {memory_text}\n"

                logger.info(f"[FOOD] Added {len(food_memories)} Mem0 memories to context")
                return context

        except Exception as e:
            logger.warning(f"[FOOD] Failed to load Mem0 context: {e}")

        return ""

    async def _get_food_history_context(self, user_id: str) -> str:
        """Get recent food history (last 7 days) for context"""
        try:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')

            recent_foods = await queries.get_food_entries_by_date(
                user_id, start_date, end_date
            )

            if recent_foods:
                # Summarize recent patterns
                food_counts = {}
                for entry in recent_foods:
                    foods_data = entry.get('foods', [])
                    if isinstance(foods_data, str):
                        foods_data = json.loads(foods_data)

                    for food in foods_data:
                        food_name = food.get('food_name', food.get('name', 'unknown'))
                        food_counts[food_name] = food_counts.get(food_name, 0) + 1

                # Top 5 most logged foods
                top_foods = sorted(food_counts.items(), key=lambda x: x[1], reverse=True)[:5]

                if top_foods:
                    context = "\n\n**Your recent eating patterns (last 7 days):**\n"
                    for food_name, count in top_foods:
                        context += f"- {food_name} (logged {count}x this week)\n"

                    logger.info(f"[FOOD] Added food history context with {len(top_foods)} items")
                    return context

        except Exception as e:
            logger.warning(f"[FOOD] Failed to load food history: {e}")

        return ""

    async def _get_habit_context(self, user_id: str) -> str:
        """Get user's food preparation habits for context"""
        try:
            habits = await habit_extractor.get_user_habits(
                user_id,
                habit_type="food_prep",
                min_confidence=0.6
            )

            if habits:
                context = "\n\n**User's food preparation habits:**\n"
                for habit in habits:
                    habit_data = habit['habit_data']
                    food = habit_data.get('food', habit['habit_key'])
                    ratio = habit_data.get('ratio', '')
                    liquid = habit_data.get('liquid', '').replace('_', ' ')

                    context += f"- {food}: Always prepared with {liquid}"
                    if ratio:
                        context += f" ({ratio} ratio)"
                    context += f" (confidence: {habit['confidence']:.0%})\n"

                logger.info(f"[FOOD] Added {len(habits)} food habits to context")
                return context

        except Exception as e:
            logger.warning(f"[FOOD] Failed to load habits: {e}")

        return ""

    async def _detect_food_habits(self, user_id: str, foods: List) -> None:
        """Trigger habit detection for food patterns (non-blocking)"""
        try:
            for food_item in foods:
                parsed_components = {
                    "food": food_item.name,
                    "quantity": food_item.quantity,
                    "preparation": food_item.name
                }
                await habit_extractor.detect_food_prep_habit(
                    user_id,
                    food_item.name,
                    parsed_components
                )
        except Exception as e:
            logger.warning(f"[HABITS] Failed to detect habits: {e}")
            # Non-blocking - habit detection shouldn't fail food logging
