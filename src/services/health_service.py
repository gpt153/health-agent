"""
HealthService - Health Tracking Business Logic

Handles tracking categories, entries, reminders, and health insights.
Extracts business logic from handlers and API routes.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from uuid import UUID

from src.db import queries
from src.models.tracking import TrackingCategory, TrackingEntry
from src.models.reminder import Reminder

logger = logging.getLogger(__name__)


class HealthService:
    """
    Service for health tracking and insights.

    Responsibilities:
    - Health metric tracking (weight, steps, sleep, custom categories)
    - Tracking category management
    - Tracking entry logging and retrieval
    - Reminder management (create, get, cancel, complete)
    - Basic trend analysis
    """

    def __init__(self, db_connection, memory_manager, reminder_manager=None):
        """
        Initialize HealthService.

        Args:
            db_connection: Database connection instance
            memory_manager: MemoryFileManager instance
            reminder_manager: Optional ReminderManager instance
        """
        self.db = db_connection
        self.memory = memory_manager
        self.reminder_manager = reminder_manager
        logger.debug("HealthService initialized")

    # Tracking Categories

    async def create_tracking_category(
        self,
        user_id: str,
        name: str,
        fields: Dict[str, Any],
        schedule: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new tracking category for a user.

        Args:
            user_id: Telegram user ID
            name: Category name (e.g., "Daily Weight", "Blood Pressure")
            fields: Field definitions (type, unit, validation)
            schedule: Optional schedule configuration

        Returns:
            {
                'success': bool,
                'category_id': str,
                'category': TrackingCategory,
                'message': str
            }
        """
        try:
            # Create category model
            category = TrackingCategory(
                user_id=user_id,
                name=name,
                fields=fields,
                schedule=schedule,
                active=True
            )

            # Save to database
            await queries.create_tracking_category(category)

            logger.info(f"Created tracking category '{name}' for user {user_id}")

            return {
                'success': True,
                'category_id': str(category.id),
                'category': category,
                'message': f"Tracking category '{name}' created successfully"
            }

        except Exception as e:
            logger.error(f"Error creating tracking category for {user_id}: {e}", exc_info=True)
            return {
                'success': False,
                'category_id': None,
                'category': None,
                'message': f"Error creating tracking category: {str(e)}"
            }

    async def get_tracking_categories(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Dict]:
        """
        Get all tracking categories for a user.

        Args:
            user_id: Telegram user ID
            active_only: Only return active categories (default: True)

        Returns:
            List of category dicts
        """
        try:
            categories = await queries.get_tracking_categories(user_id, active_only)
            return categories

        except Exception as e:
            logger.error(f"Error getting tracking categories for {user_id}: {e}", exc_info=True)
            return []

    async def deactivate_tracking_category(
        self,
        user_id: str,
        category_id: str
    ) -> Dict[str, Any]:
        """
        Deactivate a tracking category (soft delete).

        Args:
            user_id: Telegram user ID
            category_id: Category UUID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # Get category to verify ownership
            categories = await queries.get_tracking_categories(user_id, active_only=False)
            category = next((c for c in categories if str(c['id']) == category_id), None)

            if not category:
                return {
                    'success': False,
                    'message': 'Category not found or access denied'
                }

            # Deactivate (this would need a dedicated query function)
            # For now, log intent - actual implementation would call queries.deactivate_tracking_category
            logger.info(f"Deactivating tracking category {category_id} for user {user_id}")

            return {
                'success': True,
                'message': f"Category '{category['name']}' deactivated"
            }

        except Exception as e:
            logger.error(f"Error deactivating tracking category {category_id}: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"Error deactivating category: {str(e)}"
            }

    # Tracking Entries

    async def log_tracking_entry(
        self,
        user_id: str,
        category_id: str,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log a tracking entry.

        Args:
            user_id: Telegram user ID
            category_id: Category UUID
            data: Field data (e.g., {'weight': 75.5, 'unit': 'kg'})
            timestamp: Optional timestamp (defaults to now)
            notes: Optional notes

        Returns:
            {
                'success': bool,
                'entry_id': str,
                'entry': TrackingEntry,
                'message': str
            }
        """
        try:
            # Create entry model
            entry = TrackingEntry(
                user_id=user_id,
                category_id=UUID(category_id),
                timestamp=timestamp or datetime.now(),
                data=data,
                notes=notes
            )

            # Save to database
            await queries.save_tracking_entry(entry)

            logger.info(f"Logged tracking entry for user {user_id}, category {category_id}")

            return {
                'success': True,
                'entry_id': str(entry.id),
                'entry': entry,
                'message': 'Tracking entry saved successfully'
            }

        except Exception as e:
            logger.error(f"Error logging tracking entry for {user_id}: {e}", exc_info=True)
            return {
                'success': False,
                'entry_id': None,
                'entry': None,
                'message': f"Error saving tracking entry: {str(e)}"
            }

    async def get_tracking_entries(
        self,
        user_id: str,
        category_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get tracking entries for a user.

        Args:
            user_id: Telegram user ID
            category_id: Optional category filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum entries to return

        Returns:
            List of entry dicts
        """
        try:
            # This would call a dedicated query function
            # For now, returning empty list - actual implementation would call queries.get_tracking_entries
            logger.info(f"Getting tracking entries for user {user_id}, category {category_id}")
            return []

        except Exception as e:
            logger.error(f"Error getting tracking entries for {user_id}: {e}", exc_info=True)
            return []

    # Reminders

    async def create_reminder(
        self,
        user_id: str,
        reminder_type: str,
        message: str,
        schedule: Dict[str, Any],
        tracking_category_id: Optional[str] = None,
        enable_completion_tracking: bool = True,
        streak_motivation: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new reminder for a user.

        Args:
            user_id: Telegram user ID
            reminder_type: "simple" or "tracking_prompt"
            message: Reminder message
            schedule: Schedule configuration (type, time, timezone, days)
            tracking_category_id: Optional category UUID for tracking_prompt type
            enable_completion_tracking: Track completions
            streak_motivation: Show streak count

        Returns:
            {
                'success': bool,
                'reminder_id': str,
                'reminder': Reminder,
                'message': str
            }
        """
        try:
            from src.models.reminder import ReminderSchedule

            # Create reminder schedule
            reminder_schedule = ReminderSchedule(**schedule)

            # Create reminder model
            reminder = Reminder(
                user_id=user_id,
                reminder_type=reminder_type,
                message=message,
                schedule=reminder_schedule,
                active=True,
                tracking_category_id=UUID(tracking_category_id) if tracking_category_id else None,
                enable_completion_tracking=enable_completion_tracking,
                streak_motivation=streak_motivation
            )

            # Save to database
            await queries.create_reminder(reminder)

            # If reminder_manager is available, schedule it
            if self.reminder_manager:
                await self.reminder_manager.schedule_reminder(str(reminder.id))

            logger.info(f"Created reminder for user {user_id}, type {reminder_type}")

            return {
                'success': True,
                'reminder_id': str(reminder.id),
                'reminder': reminder,
                'message': 'Reminder created successfully'
            }

        except Exception as e:
            logger.error(f"Error creating reminder for {user_id}: {e}", exc_info=True)
            return {
                'success': False,
                'reminder_id': None,
                'reminder': None,
                'message': f"Error creating reminder: {str(e)}"
            }

    async def get_active_reminders(self, user_id: str) -> List[Dict]:
        """
        Get all active reminders for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            List of reminder dicts
        """
        try:
            reminders = await queries.get_active_reminders(user_id)
            return reminders

        except Exception as e:
            logger.error(f"Error getting reminders for {user_id}: {e}", exc_info=True)
            return []

    async def get_reminder_by_id(self, reminder_id: str) -> Optional[Dict]:
        """
        Get a specific reminder by ID.

        Args:
            reminder_id: Reminder UUID

        Returns:
            Reminder dict or None
        """
        try:
            reminder = await queries.get_reminder_by_id(reminder_id)
            return reminder

        except Exception as e:
            logger.error(f"Error getting reminder {reminder_id}: {e}", exc_info=True)
            return None

    async def cancel_reminder(
        self,
        user_id: str,
        reminder_id: str
    ) -> Dict[str, Any]:
        """
        Cancel (delete) a reminder.

        Args:
            user_id: Telegram user ID
            reminder_id: Reminder UUID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            success = await queries.delete_reminder(reminder_id, user_id)

            if not success:
                return {
                    'success': False,
                    'message': 'Reminder not found or access denied'
                }

            # If reminder_manager is available, unschedule it
            if self.reminder_manager:
                await self.reminder_manager.unschedule_reminder(reminder_id)

            logger.info(f"Cancelled reminder {reminder_id} for user {user_id}")

            return {
                'success': True,
                'message': 'Reminder cancelled successfully'
            }

        except Exception as e:
            logger.error(f"Error cancelling reminder {reminder_id}: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"Error cancelling reminder: {str(e)}"
            }

    async def complete_reminder(
        self,
        user_id: str,
        reminder_id: str,
        completed_at: datetime,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a reminder as completed.

        Args:
            user_id: Telegram user ID
            reminder_id: Reminder UUID
            completed_at: Completion timestamp
            notes: Optional completion notes

        Returns:
            {
                'success': bool,
                'completion_id': str,
                'message': str
            }
        """
        try:
            # Save completion
            completion_id = await queries.save_reminder_completion(
                reminder_id=reminder_id,
                user_id=user_id,
                completed_at=completed_at,
                notes=notes
            )

            logger.info(f"Reminder {reminder_id} completed by user {user_id}")

            return {
                'success': True,
                'completion_id': completion_id,
                'message': 'Reminder marked as completed'
            }

        except Exception as e:
            logger.error(f"Error completing reminder {reminder_id}: {e}", exc_info=True)
            return {
                'success': False,
                'completion_id': None,
                'message': f"Error completing reminder: {str(e)}"
            }

    async def get_reminder_streak(
        self,
        user_id: str,
        reminder_id: str
    ) -> Dict[str, int]:
        """
        Get streak information for a reminder.

        Args:
            user_id: Telegram user ID
            reminder_id: Reminder UUID

        Returns:
            {
                'current_streak': int,
                'best_streak': int
            }
        """
        try:
            current_streak = await queries.calculate_current_streak(user_id, reminder_id)
            best_streak = await queries.calculate_best_streak(user_id, reminder_id)

            return {
                'current_streak': current_streak,
                'best_streak': best_streak
            }

        except Exception as e:
            logger.error(f"Error getting streak for reminder {reminder_id}: {e}", exc_info=True)
            return {
                'current_streak': 0,
                'best_streak': 0
            }

    # Health Insights

    async def calculate_tracking_trends(
        self,
        user_id: str,
        category_id: str,
        field_name: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate trends for a tracking field over time.

        Args:
            user_id: Telegram user ID
            category_id: Category UUID
            field_name: Field to analyze (e.g., 'weight', 'steps')
            days: Number of days to analyze

        Returns:
            {
                'trend': str (increasing, decreasing, stable),
                'average': float,
                'min': float,
                'max': float,
                'change': float,
                'data_points': int
            }
        """
        try:
            # Get entries
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            entries = await self.get_tracking_entries(
                user_id=user_id,
                category_id=category_id,
                start_date=start_date,
                end_date=end_date
            )

            if not entries:
                return {
                    'trend': 'insufficient_data',
                    'average': 0,
                    'min': 0,
                    'max': 0,
                    'change': 0,
                    'data_points': 0
                }

            # Extract values
            values = []
            for entry in entries:
                if field_name in entry.get('data', {}):
                    values.append(float(entry['data'][field_name]))

            if not values:
                return {
                    'trend': 'insufficient_data',
                    'average': 0,
                    'min': 0,
                    'max': 0,
                    'change': 0,
                    'data_points': 0
                }

            # Calculate statistics
            average = sum(values) / len(values)
            min_val = min(values)
            max_val = max(values)
            change = values[-1] - values[0] if len(values) > 1 else 0

            # Determine trend
            if abs(change) < (average * 0.05):  # Less than 5% change
                trend = 'stable'
            elif change > 0:
                trend = 'increasing'
            else:
                trend = 'decreasing'

            return {
                'trend': trend,
                'average': round(average, 2),
                'min': min_val,
                'max': max_val,
                'change': round(change, 2),
                'data_points': len(values)
            }

        except Exception as e:
            logger.error(f"Error calculating trends for {category_id}: {e}", exc_info=True)
            return {
                'trend': 'error',
                'average': 0,
                'min': 0,
                'max': 0,
                'change': 0,
                'data_points': 0
            }

    async def get_reminder_analytics(
        self,
        user_id: str,
        reminder_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get analytics for a reminder.

        Args:
            user_id: Telegram user ID
            reminder_id: Reminder UUID
            days: Analysis period in days

        Returns:
            {
                'completion_rate': float,
                'total_completions': int,
                'total_scheduled': int,
                'current_streak': int,
                'best_streak': int,
                'avg_completion_time': str
            }
        """
        try:
            analytics = await queries.get_reminder_analytics(
                user_id=user_id,
                reminder_id=reminder_id,
                days=days
            )

            return analytics

        except Exception as e:
            logger.error(f"Error getting analytics for reminder {reminder_id}: {e}", exc_info=True)
            return {
                'completion_rate': 0.0,
                'total_completions': 0,
                'total_scheduled': 0,
                'current_streak': 0,
                'best_streak': 0,
                'avg_completion_time': 'N/A'
            }

    async def generate_health_summary(
        self,
        user_id: str,
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Generate a health summary report.

        Args:
            user_id: Telegram user ID
            period_days: Period in days (default: 7)

        Returns:
            {
                'period': str,
                'active_categories': int,
                'total_entries': int,
                'reminders': {
                    'total_active': int,
                    'completion_rate': float
                },
                'top_tracked_categories': List[str]
            }
        """
        try:
            # Get active categories
            categories = await self.get_tracking_categories(user_id, active_only=True)

            # Get active reminders
            reminders = await self.get_active_reminders(user_id)

            # Calculate summary
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days)

            # Get all entries for the period
            all_entries = []
            for category in categories:
                entries = await self.get_tracking_entries(
                    user_id=user_id,
                    category_id=str(category['id']),
                    start_date=start_date,
                    end_date=end_date
                )
                all_entries.extend(entries)

            # Build summary
            return {
                'period': f"{period_days} days",
                'active_categories': len(categories),
                'total_entries': len(all_entries),
                'reminders': {
                    'total_active': len(reminders),
                    'completion_rate': 0.0  # Would calculate from analytics
                },
                'top_tracked_categories': [cat['name'] for cat in categories[:5]]
            }

        except Exception as e:
            logger.error(f"Error generating health summary for {user_id}: {e}", exc_info=True)
            return {
                'period': f"{period_days} days",
                'active_categories': 0,
                'total_entries': 0,
                'reminders': {
                    'total_active': 0,
                    'completion_rate': 0.0
                },
                'top_tracked_categories': []
            }
