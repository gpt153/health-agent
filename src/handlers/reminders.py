"""Reminder completion handlers"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from src.db.queries import save_reminder_completion
from src.utils.auth import is_authorized

logger = logging.getLogger(__name__)


async def handle_reminder_completion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle when user clicks 'Done' on a reminder

    Callback data format: reminder_done|{reminder_id}|{scheduled_time}
    Example: reminder_done|550e8400-e29b-41d4-a716-446655440000|08:00
    """
    query = update.callback_query
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        await query.answer("Unauthorized", show_alert=True)
        return

    try:
        # Always answer callback query to remove loading animation
        await query.answer("✅ Marked as done!")

        # Parse callback data
        # Format: reminder_done|{reminder_id}|{scheduled_time}
        callback_data = query.data
        parts = callback_data.split("|")

        if len(parts) < 3:
            logger.error(f"Invalid callback data format: {callback_data}")
            await query.edit_message_text(
                "❌ Error: Invalid reminder data",
                parse_mode="Markdown"
            )
            return

        reminder_id = parts[1]
        scheduled_time = parts[2]

        # Get actual completion time (now)
        completed_at = datetime.now()

        # Save completion to database
        await save_reminder_completion(
            reminder_id=reminder_id,
            user_id=user_id,
            scheduled_time=scheduled_time,
            notes=None
        )

        # Update message to show completion
        original_text = query.message.text

        # Format completion message with time difference
        try:
            # Parse scheduled time
            hour, minute = map(int, scheduled_time.split(":"))
            scheduled_hour = f"{hour:02d}:{minute:02d}"
            actual_time = completed_at.strftime("%H:%M")

            # Calculate time difference
            scheduled_minutes = hour * 60 + minute
            actual_minutes = completed_at.hour * 60 + completed_at.minute
            diff_minutes = actual_minutes - scheduled_minutes

            # Create time difference string
            if diff_minutes == 0:
                time_note = "✅ Completed on time!"
            elif diff_minutes > 0:
                hours = diff_minutes // 60
                mins = diff_minutes % 60
                if hours > 0:
                    time_note = f"✅ Completed {hours}h {mins}m after scheduled time"
                else:
                    time_note = f"✅ Completed {mins}m after scheduled time"
            else:
                time_note = "✅ Completed early!"

            # Update message
            completion_message = (
                f"{original_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{time_note}\n"
                f"⏰ Scheduled: {scheduled_hour}\n"
                f"✅ Completed: {actual_time}"
            )

        except Exception as e:
            logger.error(f"Error formatting completion message: {e}", exc_info=True)
            completion_message = f"{original_text}\n\n✅ Marked as completed at {completed_at.strftime('%H:%M')}"

        await query.edit_message_text(
            completion_message,
            parse_mode="Markdown"
        )

        logger.info(
            f"Reminder completed: user={user_id}, reminder={reminder_id}, "
            f"scheduled={scheduled_time}, completed={completed_at.strftime('%H:%M')}"
        )

    except Exception as e:
        logger.error(f"Error handling reminder completion: {e}", exc_info=True)
        await query.edit_message_text(
            f"{query.message.text}\n\n❌ Error saving completion. Please try again.",
            parse_mode="Markdown"
        )


# Create callback query handler
reminder_completion_handler = CallbackQueryHandler(
    handle_reminder_completion,
    pattern="^reminder_done\\|"
)
