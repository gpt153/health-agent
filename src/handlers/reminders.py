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

        # Check for newly unlocked achievements
        try:
            from src.utils.achievement_checker import check_and_unlock_achievements, format_achievement_unlock

            new_achievements = await check_and_unlock_achievements(
                user_id=user_id,
                reminder_id=reminder_id,
                event_type="completion"
            )

            # Send achievement notifications
            for achievement in new_achievements:
                achievement_message = format_achievement_unlock(achievement)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=achievement_message,
                    parse_mode="Markdown"
                )
                logger.info(f"Achievement unlocked notification sent: {achievement['id']} for user {user_id}")

        except Exception as e:
            logger.error(f"Error checking achievements: {e}", exc_info=True)
            # Don't fail the completion if achievement checking fails

    except Exception as e:
        logger.error(f"Error handling reminder completion: {e}", exc_info=True)
        await query.edit_message_text(
            f"{query.message.text}\n\n❌ Error saving completion. Please try again.",
            parse_mode="Markdown"
        )


async def handle_reminder_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle when user clicks 'Skip' on a reminder

    Callback data format: reminder_skip|{reminder_id}|{scheduled_time}
    """
    query = update.callback_query
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        await query.answer("Unauthorized", show_alert=True)
        return

    try:
        await query.answer("Skipped!")

        # Parse callback data
        callback_data = query.data
        parts = callback_data.split("|")

        if len(parts) < 3:
            logger.error(f"Invalid callback data format: {callback_data}")
            return

        reminder_id = parts[1]
        scheduled_time = parts[2]

        # Show reason selection
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = [
            [InlineKeyboardButton("😷 Not feeling well", callback_data=f"skip_reason|{reminder_id}|{scheduled_time}|sick")],
            [InlineKeyboardButton("📦 Out of stock", callback_data=f"skip_reason|{reminder_id}|{scheduled_time}|out_of_stock")],
            [InlineKeyboardButton("🏥 Doctor's advice", callback_data=f"skip_reason|{reminder_id}|{scheduled_time}|doctor_advice")],
            [InlineKeyboardButton("⏭️ Just skip", callback_data=f"skip_reason|{reminder_id}|{scheduled_time}|other")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Update message
        original_text = query.message.text
        skip_message = (
            f"{original_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"❌ **Skipped**\n\n"
            f"💡 Reason? (optional - helps me understand patterns)"
        )

        await query.edit_message_text(
            skip_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

        logger.info(f"Reminder skip initiated: user={user_id}, reminder={reminder_id}")

    except Exception as e:
        logger.error(f"Error handling reminder skip: {e}", exc_info=True)


async def handle_skip_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle skip reason selection

    Callback data format: skip_reason|{reminder_id}|{scheduled_time}|{reason}
    """
    query = update.callback_query
    user_id = str(update.effective_user.id)

    try:
        await query.answer("Reason saved")

        # Parse callback data
        parts = query.data.split("|")
        if len(parts) < 4:
            return

        reminder_id = parts[1]
        scheduled_time = parts[2]
        reason = parts[3]

        # Save skip to database
        from src.db.queries import save_reminder_skip
        await save_reminder_skip(
            reminder_id=reminder_id,
            user_id=user_id,
            scheduled_time=scheduled_time,
            reason=reason
        )

        # Update message
        reason_text = {
            'sick': 'Not feeling well',
            'out_of_stock': 'Out of stock',
            'doctor_advice': "Doctor's advice",
            'other': 'Other'
        }.get(reason, 'Other')

        final_message = query.message.text.split("━━━━━━━━━━━━━━━━━━")[0]
        final_message += (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"❌ **Skipped**\n"
            f"📝 Reason: {reason_text}\n\n"
            f"That's okay! Tomorrow is a new day 💙"
        )

        await query.edit_message_text(
            final_message,
            parse_mode="Markdown"
        )

        logger.info(f"Skip reason saved: user={user_id}, reminder={reminder_id}, reason={reason}")

    except Exception as e:
        logger.error(f"Error saving skip reason: {e}", exc_info=True)


async def handle_reminder_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle when user clicks 'Snooze' on a reminder

    Callback data format: reminder_snooze|{reminder_id}|{scheduled_time}
    """
    query = update.callback_query
    user_id = str(update.effective_user.id)

    if not await is_authorized(user_id):
        await query.answer("Unauthorized", show_alert=True)
        return

    try:
        await query.answer("Snoozed for 30 minutes!")

        # Parse callback data
        parts = query.data.split("|")
        if len(parts) < 3:
            return

        reminder_id = parts[1]
        scheduled_time = parts[2]

        # Get reminder details
        from src.db.queries import get_reminder_by_id
        reminder_data = await get_reminder_by_id(reminder_id)

        if not reminder_data:
            await query.edit_message_text("❌ Reminder not found")
            return

        message = reminder_data.get('message', '')

        # Schedule snooze job (30 minutes from now)
        from datetime import timedelta
        snooze_time = datetime.now() + timedelta(minutes=30)

        # Use JobQueue to schedule one-time reminder
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        context.application.job_queue.run_once(
            callback=_send_snoozed_reminder,
            when=snooze_time,
            data={
                'user_id': user_id,
                'message': message,
                'reminder_id': reminder_id,
                'scheduled_time': scheduled_time
            },
            name=f"snooze_{reminder_id}_{user_id}"
        )

        # Update message
        original_text = query.message.text.split("━━━━━━━━━━━━━━━━━━")[0] if "━━━━━━" in query.message.text else query.message.text
        snooze_message = (
            f"{original_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏰ **Snoozed for 30 minutes**\n"
            f"I'll remind you again at {snooze_time.strftime('%H:%M')}"
        )

        await query.edit_message_text(
            snooze_message,
            parse_mode="Markdown"
        )

        logger.info(f"Reminder snoozed: user={user_id}, reminder={reminder_id}, until={snooze_time}")

    except Exception as e:
        logger.error(f"Error handling snooze: {e}", exc_info=True)


async def _send_snoozed_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send snoozed reminder with original callback data"""
    data = context.job.data
    user_id = data['user_id']
    message = data['message']
    reminder_id = data['reminder_id']
    scheduled_time = data['scheduled_time']

    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        # Rebuild callback data
        done_data = f"reminder_done|{reminder_id}|{scheduled_time}"
        skip_data = f"reminder_skip|{reminder_id}|{scheduled_time}"

        keyboard = [
            [
                InlineKeyboardButton("✅ Done", callback_data=done_data),
                InlineKeyboardButton("❌ Skip Today", callback_data=skip_data)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"⏰ **Reminder (Snoozed)**\n\n{message}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

        logger.info(f"Sent snoozed reminder to {user_id}")

    except Exception as e:
        logger.error(f"Failed to send snoozed reminder: {e}", exc_info=True)


# Create callback query handlers
reminder_completion_handler = CallbackQueryHandler(
    handle_reminder_completion,
    pattern="^reminder_done\\|"
)

reminder_skip_handler = CallbackQueryHandler(
    handle_reminder_skip,
    pattern="^reminder_skip\\|"
)

skip_reason_handler = CallbackQueryHandler(
    handle_skip_reason,
    pattern="^skip_reason\\|"
)

reminder_snooze_handler = CallbackQueryHandler(
    handle_reminder_snooze,
    pattern="^reminder_snooze\\|"
)
