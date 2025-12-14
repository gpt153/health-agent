"""Reminder scheduler using Telegram JobQueue"""
import logging
from datetime import time, datetime
from zoneinfo import ZoneInfo
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

        # This would load from database in production
        # For now, we'll use tracking categories with schedules
        # TODO: Implement reminder loading from reminders table
        logger.info("Reminder loading complete (stub - to be implemented)")

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
        self, user_id: str, reminder_time: str, message: str, reminder_type: str = "daily", user_timezone: str = "UTC"
    ) -> None:
        """
        Schedule a custom reminder

        Args:
            user_id: Telegram user ID
            reminder_time: Time in "HH:MM" format (user's local time)
            message: Reminder message to send
            reminder_type: "daily", "weekly", or "custom"
            user_timezone: IANA timezone string (e.g., "America/New_York")
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
                    data={"user_id": user_id, "message": message},
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

        try:
            # Send reminder message
            await context.bot.send_message(
                chat_id=user_id, text=f"⏰ **Reminder**\n\n{message}", parse_mode="Markdown"
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
