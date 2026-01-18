"""Reminder completion handlers"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from src.db.queries import save_reminder_completion, get_reminder_by_id
from src.utils.auth import is_authorized
from src.utils.note_templates import get_note_templates
from src.gamification.integrations import handle_reminder_completion_gamification
from src.utils.datetime_helpers import now_utc

logger = logging.getLogger(__name__)


async def _validate_completion(query, user_id: str) -> dict:
    """
    Validate authorization and parse callback data

    Args:
        query: Telegram callback query
        user_id: User's Telegram ID

    Returns:
        dict: {"reminder_id": str, "scheduled_time": str}

    Raises:
        ValueError: If validation fails or data is invalid
    """
    # Check authorization
    if not await is_authorized(user_id):
        await query.answer("Unauthorized", show_alert=True)
        raise ValueError("Unauthorized user")

    # Always answer callback query to remove loading animation
    await query.answer("✅ Marked as done!")

    # Parse callback data: reminder_done|{reminder_id}|{scheduled_time}
    callback_data = query.data
    parts = callback_data.split("|")

    if len(parts) < 3:
        logger.error(f"Invalid callback data format: {callback_data}")
        await query.edit_message_text(
            "❌ Error: Invalid reminder data",
            parse_mode="Markdown"
        )
        raise ValueError(f"Invalid callback data format: {callback_data}")

    return {
        "reminder_id": parts[1],
        "scheduled_time": parts[2]
    }


async def _mark_reminder_complete(
    reminder_id: str,
    user_id: str,
    scheduled_time: str
) -> datetime:
    """
    Save reminder completion to database

    Args:
        reminder_id: UUID of the reminder
        user_id: User's Telegram ID
        scheduled_time: Scheduled time (HH:MM format)

    Returns:
        datetime: Completion timestamp (UTC)
    """
    completed_at = now_utc()

    await save_reminder_completion(
        reminder_id=reminder_id,
        user_id=user_id,
        scheduled_time=scheduled_time,
        notes=None
    )

    return completed_at


async def _apply_completion_rewards(
    user_id: str,
    reminder_id: str,
    completed_at: datetime,
    scheduled_time: str
) -> dict:
    """
    Process gamification rewards (XP, streaks, levels)

    Args:
        user_id: User's Telegram ID
        reminder_id: UUID of the reminder
        completed_at: Completion timestamp
        scheduled_time: Scheduled time (HH:MM format)

    Returns:
        dict: Gamification result with XP, streaks, level info, message
    """
    return await handle_reminder_completion_gamification(
        user_id=user_id,
        reminder_id=reminder_id,
        completed_at=completed_at,
        scheduled_time=scheduled_time
    )


async def _trigger_gamification_events(
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    user_id: str,
    reminder_id: str
) -> None:
    """
    Check for and send achievement unlock notifications

    Args:
        context: Telegram context
        update: Telegram update
        user_id: User's Telegram ID
        reminder_id: UUID of the reminder
    """
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


async def _notify_completion(
    query,
    original_text: str,
    reminder_id: str,
    scheduled_time: str,
    completed_at: datetime,
    gamification_result: dict
) -> None:
    """
    Format and display completion message with gamification info

    Args:
        query: Telegram callback query
        original_text: Original reminder message text
        reminder_id: UUID of the reminder
        scheduled_time: Scheduled time (HH:MM format)
        completed_at: Completion timestamp
        gamification_result: Result from gamification processing
    """
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

        # Build completion message
        completion_message = (
            f"{original_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{time_note}\n"
            f"⏰ Scheduled: {scheduled_hour}\n"
            f"✅ Completed: {actual_time}"
        )

        # Add gamification section if available
        gamification_msg = gamification_result.get('message', '')
        if gamification_msg:
            completion_message += f"\n\n🎯 **PROGRESS**\n{gamification_msg}"

    except Exception as e:
        logger.error(f"Error formatting completion message: {e}", exc_info=True)
        completion_message = f"{original_text}\n\n✅ Marked as completed at {completed_at.strftime('%H:%M')}"

        # Add gamification even on error
        gamification_msg = gamification_result.get('message', '')
        if gamification_msg:
            completion_message += f"\n\n🎯 **PROGRESS**\n{gamification_msg}"

    # Add "Add Note" and "Stats" buttons
    keyboard = [
        [
            InlineKeyboardButton("📝 Add Note", callback_data=f"add_note|{reminder_id}|{scheduled_time}"),
            InlineKeyboardButton("📊 Stats", callback_data=f"view_stats|{reminder_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        completion_message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_reminder_completion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle when user clicks 'Done' on a reminder

    This is the main orchestrator that coordinates the completion flow:
    1. Validate authorization and parse callback data
    2. Save completion to database
    3. Apply gamification rewards (XP, streaks, levels)
    4. Check and notify achievements
    5. Update UI with completion message

    Callback data format: reminder_done|{reminder_id}|{scheduled_time}
    Example: reminder_done|550e8400-e29b-41d4-a716-446655440000|08:00
    """
    query = update.callback_query
    user_id = str(update.effective_user.id)

    try:
        # 1. Validate and extract data
        completion_data = await _validate_completion(query, user_id)

        # 2. Save to database
        completed_at = await _mark_reminder_complete(
            completion_data["reminder_id"],
            user_id,
            completion_data["scheduled_time"]
        )

        # 3. Apply gamification rewards
        gamification_result = await _apply_completion_rewards(
            user_id,
            completion_data["reminder_id"],
            completed_at,
            completion_data["scheduled_time"]
        )

        # 4. Check and notify achievements
        await _trigger_gamification_events(
            context,
            update,
            user_id,
            completion_data["reminder_id"]
        )

        # 5. Update UI with completion info
        await _notify_completion(
            query,
            query.message.text,
            completion_data["reminder_id"],
            completion_data["scheduled_time"],
            completed_at,
            gamification_result
        )

        logger.info(
            f"Reminder completed: user={user_id}, reminder={completion_data['reminder_id']}, "
            f"scheduled={completion_data['scheduled_time']}, completed={completed_at.strftime('%H:%M')}"
        )

    except ValueError as e:
        # Validation error - already handled in validate_completion
        logger.error(f"Validation error: {e}")
    except Exception as e:
        logger.error(f"Error handling reminder completion: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                f"{query.message.text}\n\n❌ Error saving completion. Please try again.",
                parse_mode="Markdown"
            )
        except Exception:
            # If we can't edit the message, log and continue
            logger.error("Failed to send error message to user")


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

        # Schedule snooze job (30 minutes from now in UTC)
        snooze_time = now_utc() + timedelta(minutes=30)

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


async def handle_add_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle when user clicks 'Add Note' button

    Callback data format: add_note|{reminder_id}|{scheduled_time}
    """
    query = update.callback_query
    user_id = str(update.effective_user.id)

    if not await is_authorized(user_id):
        await query.answer("Unauthorized", show_alert=True)
        return

    try:
        await query.answer()

        # Parse callback data
        parts = query.data.split("|")
        if len(parts) < 3:
            await query.edit_message_text("❌ Error: Invalid data")
            return

        reminder_id = parts[1]
        scheduled_time = parts[2]

        # Get reminder details for context-specific templates
        reminder = await get_reminder_by_id(reminder_id)
        if not reminder:
            await query.edit_message_text("❌ Reminder not found")
            return

        reminder_message = reminder.get('message', '')

        # Get note templates
        templates = get_note_templates(reminder_message)

        # Build template buttons (max 2 per row)
        keyboard = []
        for i in range(0, len(templates), 2):
            row = []
            row.append(InlineKeyboardButton(
                templates[i],
                callback_data=f"note_template|{reminder_id}|{scheduled_time}|{i}"
            ))
            if i + 1 < len(templates):
                row.append(InlineKeyboardButton(
                    templates[i + 1],
                    callback_data=f"note_template|{reminder_id}|{scheduled_time}|{i+1}"
                ))
            keyboard.append(row)

        # Add custom note and skip options
        keyboard.append([InlineKeyboardButton("✍️ Custom Note", callback_data=f"note_custom|{reminder_id}|{scheduled_time}")])
        keyboard.append([InlineKeyboardButton("⏭️ Skip Note", callback_data=f"note_skip|{reminder_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📝 **Add a note to this completion**\n\n_{reminder_message}_\n\nQuick templates:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

        # Store reminder_id and scheduled_time in context for custom note handler
        context.user_data['pending_note'] = {
            'reminder_id': reminder_id,
            'scheduled_time': scheduled_time,
            'templates': templates
        }

    except Exception as e:
        logger.error(f"Error handling add note: {e}", exc_info=True)


async def handle_note_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when user selects a note template"""
    query = update.callback_query
    user_id = str(update.effective_user.id)

    if not await is_authorized(user_id):
        await query.answer("Unauthorized", show_alert=True)
        return

    try:
        await query.answer("✅ Note saved!")

        # Parse callback data
        parts = query.data.split("|")
        if len(parts) < 4:
            await query.edit_message_text("❌ Error: Invalid data")
            return

        reminder_id = parts[1]
        scheduled_time = parts[2]
        template_index = int(parts[3])

        # Get the template text from stored data
        pending_note = context.user_data.get('pending_note', {})
        templates = pending_note.get('templates', [])

        if template_index >= len(templates):
            await query.edit_message_text("❌ Error: Template not found")
            return

        note_text = templates[template_index]

        # Update the completion with note
        from src.db.queries import update_completion_note
        await update_completion_note(user_id, reminder_id, scheduled_time, note_text)

        await query.edit_message_text(
            f"✅ **Note saved!**\n\n📝 \"{note_text}\"\n\nThis will help track patterns over time.",
            parse_mode="Markdown"
        )

        # Clean up
        context.user_data.pop('pending_note', None)

    except Exception as e:
        logger.error(f"Error saving template note: {e}", exc_info=True)
        await query.edit_message_text("❌ Error saving note. Please try again.")


async def handle_note_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when user wants to write a custom note"""
    query = update.callback_query
    user_id = str(update.effective_user.id)

    if not await is_authorized(user_id):
        await query.answer("Unauthorized", show_alert=True)
        return

    try:
        await query.answer()

        # Parse callback data
        parts = query.data.split("|")
        if len(parts) < 3:
            await query.edit_message_text("❌ Error: Invalid data")
            return

        reminder_id = parts[1]
        scheduled_time = parts[2]

        # Set flag for message handler
        context.user_data['awaiting_custom_note'] = True
        context.user_data['pending_note'] = {
            'reminder_id': reminder_id,
            'scheduled_time': scheduled_time
        }

        await query.edit_message_text(
            "✍️ **Type your note below**\n\n_(Max 200 characters)_\n\nOr send /cancel to skip.",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error handling custom note: {e}", exc_info=True)


async def handle_note_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when user skips adding a note"""
    query = update.callback_query
    user_id = str(update.effective_user.id)

    if not await is_authorized(user_id):
        await query.answer("Unauthorized", show_alert=True)
        return

    try:
        await query.answer("Note skipped")

        await query.edit_message_text(
            "✅ Completion recorded without note.",
            parse_mode="Markdown"
        )

        # Clean up
        context.user_data.pop('pending_note', None)
        context.user_data.pop('awaiting_custom_note', None)

    except Exception as e:
        logger.error(f"Error skipping note: {e}", exc_info=True)


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

add_note_handler = CallbackQueryHandler(
    handle_add_note,
    pattern="^add_note\\|"
)

note_template_handler = CallbackQueryHandler(
    handle_note_template,
    pattern="^note_template\\|"
)

note_custom_handler = CallbackQueryHandler(
    handle_note_custom,
    pattern="^note_custom\\|"
)

note_skip_handler = CallbackQueryHandler(
    handle_note_skip,
    pattern="^note_skip\\|"
)
