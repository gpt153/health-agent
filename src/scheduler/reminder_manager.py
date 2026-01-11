"""Reminder scheduler using Telegram JobQueue"""
import logging
from datetime import time, datetime
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes
from src.db.queries import get_active_reminders, get_tracking_categories
from src.utils.datetime_helpers import now_utc

logger = logging.getLogger(__name__)


class ReminderManager:
    """Manage scheduled reminders and tracking prompts"""

    def __init__(self, application: Application):
        self.application = application
        self.job_queue = application.job_queue

    async def load_reminders(self) -> None:
        """Load all active reminders from database and schedule them"""
        logger.info("Loading reminders from database...")

        try:
            # Get all active reminders from database
            from src.db.queries import get_active_reminders_all
            import json

            # Get reminders for all users
            all_reminders = await get_active_reminders_all()

            scheduled_count = 0
            for reminder in all_reminders:
                user_id = reminder["user_id"]
                reminder_id = str(reminder["id"])  # Get reminder UUID
                reminder_type = reminder["reminder_type"]
                message = reminder["message"]

                # Parse schedule JSON
                schedule = json.loads(reminder["schedule"]) if isinstance(reminder["schedule"], str) else reminder["schedule"]
                reminder_time = schedule.get("time", "09:00")
                timezone = schedule.get("timezone", "UTC")
                days = schedule.get("days", list(range(7)))  # Extract days filter

                # Schedule the reminder with reminder_id
                await self.schedule_custom_reminder(
                    user_id=user_id,
                    reminder_time=reminder_time,
                    message=message,
                    reminder_type=reminder_type,
                    user_timezone=timezone,
                    reminder_id=reminder_id,
                    days=days  # Pass days filter
                )

                scheduled_count += 1

            logger.info(f"Loaded and scheduled {scheduled_count} reminders from database")

        except Exception as e:
            logger.error(f"Failed to load reminders: {e}", exc_info=True)

    async def schedule_tracking_reminder(
        self, user_id: str, category_name: str, reminder_time: str, message: str, user_timezone: str = "UTC"
    ) -> None:
        """
        Schedule a tracking reminder for a user

        Args:
            user_id: Telegram user ID
            category_name: Name of tracking category
            reminder_time: Time in "HH:MM" format (user's local time)
            message: Reminder message to send
            user_timezone: IANA timezone string (e.g., "America/New_York")
        """
        try:
            # Parse time and apply user's timezone
            hour, minute = map(int, reminder_time.split(":"))

            # Create timezone-aware time
            tz = ZoneInfo(user_timezone)
            scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)

            # Schedule daily job
            self.job_queue.run_daily(
                callback=self._send_tracking_reminder,
                time=scheduled_time,
                data={
                    "user_id": user_id,
                    "category_name": category_name,
                    "message": message,
                },
                name=f"tracking_reminder_{user_id}_{category_name}",
            )

            logger.info(
                f"Scheduled tracking reminder for {user_id}: {category_name} at {reminder_time} {user_timezone}"
            )

        except Exception as e:
            logger.error(f"Failed to schedule tracking reminder: {e}", exc_info=True)

    async def schedule_custom_reminder(
        self,
        user_id: str,
        reminder_time: str,
        message: str,
        reminder_type: str = "daily",
        user_timezone: str = "UTC",
        reminder_id: str = None,
        days: list[int] = None,
        reminder_date: str = None
    ) -> None:
        """
        Schedule a custom reminder

        Args:
            user_id: Telegram user ID
            reminder_time: Time in "HH:MM" format (user's local time)
            message: Reminder message to send
            reminder_type: "daily", "weekly", or "once"
            user_timezone: IANA timezone string (e.g., "America/New_York")
            reminder_id: UUID of reminder in database (optional, for completion tracking)
            days: List of weekday integers (0=Monday, 6=Sunday). None = all days.
            reminder_date: Date string in YYYY-MM-DD format (required for reminder_type="once")
        """
        try:
            # Parse time and apply user's timezone
            hour, minute = map(int, reminder_time.split(":"))

            # Create timezone-aware time
            tz = ZoneInfo(user_timezone)

            # Schedule based on type
            if reminder_type == "daily":
                scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)

                # Default to all days if not specified
                if days is None:
                    days = list(range(7))

                self.job_queue.run_daily(
                    callback=self._send_custom_reminder,
                    time=scheduled_time,
                    data={
                        "user_id": user_id,
                        "message": message,
                        "reminder_id": reminder_id,
                        "scheduled_time": reminder_time,
                        "timezone": user_timezone,
                        "days": days  # Include days filter
                    },
                    name=f"custom_reminder_{reminder_id}",  # Use UUID for uniqueness
                )

                logger.info(
                    f"Scheduled {reminder_type} reminder for {user_id} "
                    f"at {reminder_time} {user_timezone} (days: {days})"
                )

            elif reminder_type == "once":
                # Parse date and time into full datetime
                from datetime import datetime, date
                reminder_date_obj = date.fromisoformat(reminder_date)

                # Create timezone-aware datetime
                reminder_datetime = datetime.combine(
                    reminder_date_obj,
                    time(hour, minute),
                    tzinfo=tz
                )

                # Schedule one-time job
                self.job_queue.run_once(
                    callback=self._send_custom_reminder,
                    when=reminder_datetime,
                    data={
                        "user_id": user_id,
                        "message": message,
                        "reminder_id": reminder_id,
                        "scheduled_time": reminder_time,
                        "timezone": user_timezone,
                        "days": None  # Not applicable for one-time reminders
                    },
                    name=f"custom_reminder_{reminder_id}",
                )

                logger.info(
                    f"Scheduled one-time reminder for {user_id} "
                    f"at {reminder_datetime.isoformat()}"
                )

            else:
                logger.warning(f"Reminder type {reminder_type} not implemented yet")

        except Exception as e:
            logger.error(f"Failed to schedule custom reminder: {e}", exc_info=True)

    async def cancel_reminder(self, job_name: str) -> bool:
        """
        Cancel a scheduled reminder by job name

        Args:
            job_name: Name of the job to cancel

        Returns:
            True if cancelled, False if not found
        """
        jobs = self.job_queue.get_jobs_by_name(job_name)

        if jobs:
            for job in jobs:
                job.schedule_removal()
            logger.info(f"Cancelled reminder: {job_name}")
            return True

        logger.warning(f"Reminder not found: {job_name}")
        return False

    async def cancel_reminder_by_id(self, reminder_id: str) -> bool:
        """
        Cancel a scheduled reminder by its reminder_id

        Args:
            reminder_id: UUID of the reminder

        Returns:
            True if cancelled, False if not found
        """
        job_name = f"custom_reminder_{reminder_id}"
        return await self.cancel_reminder(job_name)

    async def schedule_sleep_quiz(
        self, user_id: str, preferred_time: time, user_timezone: str = "UTC", language_code: str = "en"
    ) -> None:
        """
        Schedule automated sleep quiz for a user.

        Args:
            user_id: Telegram user ID
            preferred_time: Preferred time for quiz (user's local time)
            user_timezone: IANA timezone string
            language_code: User's language code for translations
        """
        try:
            # Create timezone-aware time
            tz = ZoneInfo(user_timezone)

            # Handle both time objects and strings
            if isinstance(preferred_time, str):
                hour, minute = map(int, preferred_time.split(':')[:2])
                scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)
            else:
                scheduled_time = time(hour=preferred_time.hour, minute=preferred_time.minute, tzinfo=tz)

            # Schedule daily job
            self.job_queue.run_daily(
                callback=self._send_sleep_quiz,
                time=scheduled_time,
                data={
                    "user_id": user_id,
                    "language_code": language_code,
                    "scheduled_time": scheduled_time.strftime("%H:%M"),
                    "timezone": user_timezone
                },
                name=f"sleep_quiz_{user_id}",
            )

            logger.info(
                f"Scheduled sleep quiz for {user_id} at {scheduled_time.strftime('%H:%M')} {user_timezone}"
            )

        except Exception as e:
            logger.error(f"Failed to schedule sleep quiz: {e}", exc_info=True)

    async def _send_sleep_quiz(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send automated sleep quiz to user"""
        data = context.job.data
        user_id = data["user_id"]
        language_code = data.get("language_code", "en")
        scheduled_time_str = data.get("scheduled_time", "")

        try:
            from src.i18n.translations import t

            # Store scheduled time for pattern tracking (in UTC)
            scheduled_time = now_utc().replace(
                hour=int(scheduled_time_str.split(':')[0]),
                minute=int(scheduled_time_str.split(':')[1]),
                second=0,
                microsecond=0
            )

            # Store in bot_data for later reference in quiz completion
            if not hasattr(context, 'bot_data'):
                context.bot_data = {}
            context.bot_data[f"sleep_quiz_scheduled_{user_id}"] = scheduled_time

            # Send quiz trigger message with /sleep_quiz command hint
            message = t('quiz_welcome', lang=language_code)
            message += "\n\nTap /sleep_quiz to start!"

            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )

            logger.info(f"Sent automated sleep quiz trigger to {user_id}")

        except Exception as e:
            logger.error(f"Failed to send sleep quiz: {e}", exc_info=True)

    async def load_sleep_quiz_schedules(self) -> None:
        """Load all enabled sleep quiz schedules from database (called on startup)"""
        logger.info("Loading sleep quiz schedules from database...")

        try:
            from src.db.queries import get_all_enabled_sleep_quiz_users

            users = await get_all_enabled_sleep_quiz_users()
            scheduled_count = 0

            for user in users:
                user_id = user["user_id"]
                preferred_time = user["preferred_time"]
                timezone = user["timezone"]
                language_code = user["language_code"]

                await self.schedule_sleep_quiz(
                    user_id=user_id,
                    preferred_time=preferred_time,
                    user_timezone=timezone,
                    language_code=language_code
                )

                scheduled_count += 1

            logger.info(f"Loaded and scheduled {scheduled_count} sleep quizzes")

        except Exception as e:
            logger.error(f"Failed to load sleep quiz schedules: {e}", exc_info=True)

    async def _send_tracking_reminder(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a tracking reminder to user"""
        data = context.job.data
        user_id = data["user_id"]
        category_name = data["category_name"]
        message = data["message"]

        try:
            # Send reminder message
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📊 **Tracking Reminder**\n\n{message}\n\nReply with your {category_name} data!",
                parse_mode="Markdown",
            )

            logger.info(f"Sent tracking reminder to {user_id}: {category_name}")

        except Exception as e:
            logger.error(f"Failed to send tracking reminder: {e}", exc_info=True)

    async def _send_custom_reminder(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a custom reminder to user with completion tracking buttons"""
        data = context.job.data
        user_id = data["user_id"]
        message = data["message"]
        reminder_id = data.get("reminder_id")
        scheduled_time = data.get("scheduled_time", "")
        timezone_str = data.get("timezone", "UTC")
        scheduled_days = data.get("days", list(range(7)))  # Get days filter

        try:
            # Check if today is a scheduled day
            from zoneinfo import ZoneInfo
            from datetime import datetime
            user_tz = ZoneInfo(timezone_str)
            now_user = datetime.now(user_tz)
            current_weekday = now_user.weekday()  # 0=Monday, 6=Sunday

            if current_weekday not in scheduled_days:
                logger.debug(
                    f"Skipping reminder {reminder_id} for {user_id}: "
                    f"Today ({current_weekday}) not in scheduled days {scheduled_days}"
                )
                return  # Don't send reminder today
            # Get reminder from database to check tracking preference
            from src.db.queries import get_reminder_by_id

            enable_tracking = True  # Default
            streak_count = 0

            if reminder_id:
                reminder_data = await get_reminder_by_id(reminder_id)
                if reminder_data:
                    enable_tracking = reminder_data.get("enable_completion_tracking", True)

                    # Calculate current streak if tracking enabled
                    if enable_tracking:
                        from src.db.queries import calculate_current_streak
                        streak_count = await calculate_current_streak(user_id, reminder_id)

            # Build message text
            reminder_text = f"⏰ **Reminder**\n\n{message}"

            # Add streak motivation if enabled and streak exists
            if enable_tracking and streak_count > 0:
                fire_emoji = "🔥" * min(streak_count, 3)  # Max 3 fire emojis
                reminder_text += f"\n\n{fire_emoji} {streak_count}-day streak! Keep it going 💪"

            # Create inline keyboard based on tracking preference
            keyboard = None
            if enable_tracking and reminder_id:
                # Format: action|reminder_id|scheduled_time
                done_data = f"reminder_done|{reminder_id}|{scheduled_time}"
                skip_data = f"reminder_skip|{reminder_id}|{scheduled_time}"
                snooze_data = f"reminder_snooze|{reminder_id}|{scheduled_time}"

                keyboard = [
                    [
                        InlineKeyboardButton("✅ Done", callback_data=done_data),
                        InlineKeyboardButton("❌ Skip", callback_data=skip_data)
                    ],
                    [
                        InlineKeyboardButton("⏰ Snooze 30m", callback_data=snooze_data)
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send with buttons
                await context.bot.send_message(
                    chat_id=user_id,
                    text=reminder_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                # Send without buttons (tracking disabled or no reminder_id)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=reminder_text,
                    parse_mode="Markdown"
                )

            logger.info(f"Sent custom reminder to {user_id} (tracking={enable_tracking}, streak={streak_count})")

        except Exception as e:
            logger.error(f"Failed to send custom reminder: {e}", exc_info=True)

    async def list_user_reminders(self, user_id: str) -> list[dict]:
        """
        Get list of scheduled reminders for a user

        Args:
            user_id: Telegram user ID

        Returns:
            List of reminder info dicts
        """
        reminders = []

        # Get all jobs from queue
        jobs = self.job_queue.jobs()

        for job in jobs:
            if job.data and job.data.get("user_id") == user_id:
                reminders.append(
                    {
                        "name": job.name,
                        "type": "tracking"
                        if "tracking_reminder" in job.name
                        else "custom",
                        "next_run": job.next_t.isoformat() if job.next_t else None,
                        "data": job.data,
                    }
                )

        return reminders
