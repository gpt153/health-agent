"""Reminder scheduler using Telegram JobQueue"""
import logging
from datetime import time, datetime
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes
from src.db.queries import get_active_reminders, get_tracking_categories

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

                # Schedule the reminder with reminder_id
                await self.schedule_custom_reminder(
                    user_id=user_id,
                    reminder_time=reminder_time,
                    message=message,
                    reminder_type=reminder_type,
                    user_timezone=timezone,
                    reminder_id=reminder_id
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
        self, user_id: str, reminder_time: str, message: str, reminder_type: str = "daily", user_timezone: str = "UTC", reminder_id: str = None
    ) -> None:
        """
        Schedule a custom reminder

        Args:
            user_id: Telegram user ID
            reminder_time: Time in "HH:MM" format (user's local time)
            message: Reminder message to send
            reminder_type: "daily", "weekly", or "custom"
            user_timezone: IANA timezone string (e.g., "America/New_York")
            reminder_id: UUID of reminder in database (optional, for completion tracking)
        """
        try:
            # Parse time and apply user's timezone
            hour, minute = map(int, reminder_time.split(":"))

            # Create timezone-aware time
            tz = ZoneInfo(user_timezone)
            scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)

            # Schedule based on type
            if reminder_type == "daily":
                self.job_queue.run_daily(
                    callback=self._send_custom_reminder,
                    time=scheduled_time,
                    data={
                        "user_id": user_id,
                        "message": message,
                        "reminder_id": reminder_id,
                        "scheduled_time": reminder_time,
                        "timezone": user_timezone
                    },
                    name=f"custom_reminder_{user_id}_{hour}{minute}",
                )
            else:
                logger.warning(f"Reminder type {reminder_type} not implemented yet")

            logger.info(
                f"Scheduled {reminder_type} reminder for {user_id} at {reminder_time} {user_timezone}"
            )

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
        """Send a custom reminder to user"""
        data = context.job.data
        user_id = data["user_id"]
        message = data["message"]
        reminder_id = data.get("reminder_id")
        scheduled_time = data.get("scheduled_time", "")

        try:
            # Create inline keyboard with "Done" button
            keyboard = None
            if reminder_id:
                # Include reminder_id and scheduled_time in callback data
                # Format: reminder_done|{reminder_id}|{scheduled_time}
                callback_data = f"reminder_done|{reminder_id}|{scheduled_time}"
                keyboard = [
                    [InlineKeyboardButton("✅ Done", callback_data=callback_data)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send reminder message with button
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ **Reminder**\n\n{message}",
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                # Send without button if no reminder_id (backward compatibility)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ **Reminder**\n\n{message}",
                    parse_mode="Markdown"
                )

            logger.info(f"Sent custom reminder to {user_id}")

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
