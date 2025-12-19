"""Sleep quiz conversation handler with inline keyboards"""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CommandHandler, CallbackQueryHandler, ContextTypes
)
from src.db.queries import save_sleep_entry, get_sleep_entries, log_feature_usage
from src.models.sleep import SleepEntry
from src.utils.auth import is_authorized
from datetime import datetime, time as time_type
from uuid import uuid4

logger = logging.getLogger(__name__)

# Define conversation states
BEDTIME, SLEEP_LATENCY, WAKE_TIME, NIGHT_WAKINGS = range(4)
QUALITY, PHONE, DISRUPTIONS, ALERTNESS = range(4, 8)


async def start_sleep_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for sleep quiz"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return ConversationHandler.END

    # Initialize quiz data storage
    context.user_data['sleep_quiz_data'] = {}

    message = (
        "😴 **Good morning! Let's log your sleep**\n\n"
        "This takes about 60 seconds.\n\n"
        "Ready? Let's start!"
    )

    await update.message.reply_text(message, parse_mode="Markdown")

    # Show first question immediately
    return await show_bedtime_question(update, context)


async def show_bedtime_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show bedtime question with time picker"""
    user_id = str(update.effective_user.id)

    # Default to 10 PM if no prior data
    hour = context.user_data['sleep_quiz_data'].get('bedtime_hour', 22)
    minute = context.user_data['sleep_quiz_data'].get('bedtime_minute', 0)

    keyboard = [
        [
            InlineKeyboardButton("🔼", callback_data="bed_h_up"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔼", callback_data="bed_m_up"),
        ],
        [
            InlineKeyboardButton(f"{hour:02d}", callback_data="noop"),
            InlineKeyboardButton(":", callback_data="noop"),
            InlineKeyboardButton(f"{minute:02d}", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("🔽", callback_data="bed_h_down"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔽", callback_data="bed_m_down"),
        ],
        [InlineKeyboardButton("✅ Confirm", callback_data="bed_confirm")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "**Q1/8: What time did you get into bed?**\n\nUse ⬆️⬇️ to adjust time"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return BEDTIME


async def handle_bedtime_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle bedtime time picker callbacks"""
    query = update.callback_query
    await query.answer()  # CRITICAL: Remove loading spinner

    data = query.data
    hour = context.user_data['sleep_quiz_data'].get('bedtime_hour', 22)
    minute = context.user_data['sleep_quiz_data'].get('bedtime_minute', 0)

    if data == "bed_h_up":
        hour = (hour + 1) % 24
    elif data == "bed_h_down":
        hour = (hour - 1) % 24
    elif data == "bed_m_up":
        minute = (minute + 15) % 60
    elif data == "bed_m_down":
        minute = (minute - 15) % 60
    elif data == "bed_confirm":
        # Save bedtime and move to next question
        context.user_data['sleep_quiz_data']['bedtime'] = f"{hour:02d}:{minute:02d}"
        return await show_sleep_latency_question(update, context)
    elif data == "noop":
        # No-op buttons (display only)
        return BEDTIME

    # Update stored values
    context.user_data['sleep_quiz_data']['bedtime_hour'] = hour
    context.user_data['sleep_quiz_data']['bedtime_minute'] = minute

    # Rebuild picker with new values
    return await show_bedtime_question(update, context)


async def show_sleep_latency_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q2: How long to fall asleep?"""
    keyboard = [
        [InlineKeyboardButton("Less than 15 min", callback_data="latency_0")],
        [InlineKeyboardButton("15-30 min", callback_data="latency_15")],
        [InlineKeyboardButton("30-60 min", callback_data="latency_45")],
        [InlineKeyboardButton("More than 1 hour", callback_data="latency_90")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "**Q2/8: How long did it take you to fall asleep?**"
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return SLEEP_LATENCY


async def handle_sleep_latency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sleep latency selection"""
    query = update.callback_query
    await query.answer()

    # Parse latency from callback_data
    latency_str = query.data.replace("latency_", "")
    latency_minutes = int(latency_str)

    context.user_data['sleep_quiz_data']['sleep_latency_minutes'] = latency_minutes

    # Confirm selection
    await query.edit_message_text(f"✅ Sleep latency: {latency_minutes} minutes")

    return await show_wake_time_question(update, context)


async def show_wake_time_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show wake time question with time picker"""
    user_id = str(update.effective_user.id)

    # Default to 7 AM if no prior data
    hour = context.user_data['sleep_quiz_data'].get('wake_hour', 7)
    minute = context.user_data['sleep_quiz_data'].get('wake_minute', 0)

    keyboard = [
        [
            InlineKeyboardButton("🔼", callback_data="wake_h_up"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔼", callback_data="wake_m_up"),
        ],
        [
            InlineKeyboardButton(f"{hour:02d}", callback_data="noop"),
            InlineKeyboardButton(":", callback_data="noop"),
            InlineKeyboardButton(f"{minute:02d}", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("🔽", callback_data="wake_h_down"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔽", callback_data="wake_m_down"),
        ],
        [InlineKeyboardButton("✅ Confirm", callback_data="wake_confirm")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "**Q3/8: What time did you wake up this morning?**\n\nUse ⬆️⬇️ to adjust time"

    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return WAKE_TIME


async def handle_wake_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wake time picker callbacks"""
    query = update.callback_query
    await query.answer()

    data = query.data
    hour = context.user_data['sleep_quiz_data'].get('wake_hour', 7)
    minute = context.user_data['sleep_quiz_data'].get('wake_minute', 0)

    if data == "wake_h_up":
        hour = (hour + 1) % 24
    elif data == "wake_h_down":
        hour = (hour - 1) % 24
    elif data == "wake_m_up":
        minute = (minute + 15) % 60
    elif data == "wake_m_down":
        minute = (minute - 15) % 60
    elif data == "wake_confirm":
        # Save wake time and move to next question
        context.user_data['sleep_quiz_data']['wake_time'] = f"{hour:02d}:{minute:02d}"
        return await show_night_wakings_question(update, context)
    elif data == "noop":
        return WAKE_TIME

    # Update stored values
    context.user_data['sleep_quiz_data']['wake_hour'] = hour
    context.user_data['sleep_quiz_data']['wake_minute'] = minute

    # Rebuild picker with new values
    return await show_wake_time_question(update, context)


async def show_night_wakings_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q4: Night wakings"""
    keyboard = [
        [InlineKeyboardButton("No", callback_data="wakings_0")],
        [InlineKeyboardButton("Yes, 1-2 times", callback_data="wakings_1")],
        [InlineKeyboardButton("Yes, 3+ times", callback_data="wakings_3")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "**Q4/8: Did you wake up during the night?**"
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return NIGHT_WAKINGS


async def handle_night_wakings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle night wakings selection"""
    query = update.callback_query
    await query.answer()

    # Parse wakings from callback_data
    wakings_str = query.data.replace("wakings_", "")
    if wakings_str == "0":
        wakings = 0
    elif wakings_str == "1":
        wakings = 2  # Midpoint of 1-2
    else:  # "3"
        wakings = 4  # Estimate for 3+

    context.user_data['sleep_quiz_data']['night_wakings'] = wakings

    # Confirm selection
    await query.edit_message_text(f"✅ Night wakings: {wakings} times")

    return await show_quality_rating_question(update, context)


async def show_quality_rating_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q5: Quality rating with button grid"""
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"quality_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"quality_{i}") for i in range(6, 11)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "**Q5/8: How would you rate your sleep quality?**\n\n"
        "😫 1-2 = Terrible\n"
        "😐 5-6 = Okay\n"
        "😊 9-10 = Excellent"
    )
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return QUALITY


async def handle_quality_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quality rating selection"""
    query = update.callback_query
    await query.answer()

    # Parse quality from callback_data
    quality = int(query.data.replace("quality_", ""))

    context.user_data['sleep_quiz_data']['sleep_quality_rating'] = quality

    # Confirm selection
    quality_emoji = "😊" if quality >= 8 else "😐" if quality >= 5 else "😫"
    await query.edit_message_text(f"✅ Quality rating: {quality_emoji} {quality}/10")

    return await show_phone_usage_question(update, context)


async def show_phone_usage_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q6: Phone usage toggle"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="phone_yes"),
            InlineKeyboardButton("❌ No", callback_data="phone_no"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "**Q6/8: Did you use your phone/screen while in bed?**"
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return PHONE


async def handle_phone_usage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone usage - conditional follow-up"""
    query = update.callback_query
    await query.answer()

    if query.data == "phone_yes":
        context.user_data['sleep_quiz_data']['phone_usage'] = True
        # Show follow-up duration question
        keyboard = [
            [InlineKeyboardButton("< 15 min", callback_data="phone_dur_7")],
            [InlineKeyboardButton("15-30 min", callback_data="phone_dur_22")],
            [InlineKeyboardButton("30-60 min", callback_data="phone_dur_45")],
            [InlineKeyboardButton("1+ hour", callback_data="phone_dur_90")],
        ]
        text = "**For how long?**"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return PHONE
    else:
        context.user_data['sleep_quiz_data']['phone_usage'] = False
        context.user_data['sleep_quiz_data']['phone_duration_minutes'] = 0
        await query.edit_message_text("✅ Noted: No phone usage")
        return await show_disruptions_question(update, context)


async def handle_phone_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone duration selection"""
    query = update.callback_query
    await query.answer()

    # Parse duration from callback_data
    duration = int(query.data.replace("phone_dur_", ""))

    context.user_data['sleep_quiz_data']['phone_duration_minutes'] = duration

    # Confirm selection
    await query.edit_message_text(f"✅ Phone usage: {duration} minutes")

    return await show_disruptions_question(update, context)


async def show_disruptions_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q7: Disruptions multi-select"""
    # Initialize selections set if not exists
    if 'disruptions_selected' not in context.user_data['sleep_quiz_data']:
        context.user_data['sleep_quiz_data']['disruptions_selected'] = set()

    selected = context.user_data['sleep_quiz_data']['disruptions_selected']

    keyboard = [
        [InlineKeyboardButton(
            f"{'✅ ' if 'noise' in selected else ''}🔊 Noise",
            callback_data="disrupt_noise"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'light' in selected else ''}💡 Light",
            callback_data="disrupt_light"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'temp' in selected else ''}🌡️ Temperature",
            callback_data="disrupt_temp"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'stress' in selected else ''}😰 Stress/worry",
            callback_data="disrupt_stress"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'dream' in selected else ''}😱 Bad dream",
            callback_data="disrupt_dream"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'pain' in selected else ''}🤕 Pain",
            callback_data="disrupt_pain"
        )],
        [InlineKeyboardButton("✅ Done", callback_data="disrupt_done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "**Q7/8: What disrupted your sleep?** (Select all that apply)"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return DISRUPTIONS


async def handle_disruptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle disruptions toggle"""
    query = update.callback_query
    await query.answer()

    if query.data == "disrupt_done":
        # Save disruptions list and advance
        selected = context.user_data['sleep_quiz_data']['disruptions_selected']
        context.user_data['sleep_quiz_data']['disruptions'] = list(selected)
        return await show_alertness_question(update, context)
    else:
        # Toggle selection
        disruption = query.data.replace("disrupt_", "")
        selected = context.user_data['sleep_quiz_data']['disruptions_selected']

        if disruption in selected:
            selected.remove(disruption)
        else:
            selected.add(disruption)

        # Rebuild keyboard with updated checkmarks
        return await show_disruptions_question(update, context)


async def show_alertness_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q8: Alertness rating - final question"""
    # Get current selection if it exists
    selected = context.user_data['sleep_quiz_data'].get('alertness_rating')

    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"alert_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"alert_{i}") for i in range(6, 11)],
    ]

    # Add submit button if a selection has been made
    if selected:
        keyboard.append([InlineKeyboardButton("✅ Submit", callback_data="alert_submit")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if selected:
        text = (
            "**Q8/8: How tired/alert do you feel RIGHT NOW?**\n\n"
            "😴 1-2 = Exhausted\n"
            "😐 5-6 = Normal\n"
            "⚡ 9-10 = Wide awake\n\n"
            f"**Selected:** {selected}/10\n"
            "👉 _Click submit to complete, or select a different rating_"
        )
    else:
        text = (
            "**Q8/8: How tired/alert do you feel RIGHT NOW?**\n\n"
            "😴 1-2 = Exhausted\n"
            "😐 5-6 = Normal\n"
            "⚡ 9-10 = Wide awake\n\n"
            "👉 _Select a number below_"
        )

    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return ALERTNESS


async def handle_alertness_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle alertness - save all data and complete quiz"""
    query = update.callback_query
    await query.answer()

    try:
        # Check if this is a number selection or submit button
        if query.data == "alert_submit":
            # User clicked submit - finalize the quiz
            quiz_data = context.user_data.get('sleep_quiz_data', {})

            # Validate that alertness rating was selected
            if 'alertness_rating' not in quiz_data:
                await query.edit_message_text(
                    "❌ Error: Please select a rating before submitting.",
                    parse_mode="Markdown"
                )
                return await show_alertness_question(update, context)

            alertness = quiz_data['alertness_rating']
        else:
            # User clicked a number - save selection and show submit button
            alertness = int(query.data.replace("alert_", ""))
            context.user_data['sleep_quiz_data']['alertness_rating'] = alertness

            # Rebuild question with submit button
            return await show_alertness_question(update, context)

        # Validate required fields
        quiz_data = context.user_data.get('sleep_quiz_data', {})
        required_fields = ['bedtime', 'wake_time', 'sleep_latency_minutes',
                          'sleep_quality_rating', 'phone_usage']
        missing_fields = [f for f in required_fields if f not in quiz_data]

        if missing_fields:
            logger.error(f"Missing quiz data fields: {missing_fields}")
            await query.edit_message_text(
                "❌ **Error:** Quiz data incomplete. Please start over with /sleep_quiz\n\n"
                f"Missing data: {', '.join(missing_fields)}",
                parse_mode="Markdown"
            )
            if 'sleep_quiz_data' in context.user_data:
                del context.user_data['sleep_quiz_data']
            return ConversationHandler.END

        # Calculate total sleep duration
        bedtime_str = quiz_data['bedtime']  # "22:00"
        wake_str = quiz_data['wake_time']  # "07:00"
        latency = quiz_data['sleep_latency_minutes']

        # Parse times
        bed_hour, bed_min = map(int, bedtime_str.split(':'))
        wake_hour, wake_min = map(int, wake_str.split(':'))

        # Calculate duration (handle overnight)
        bed_total_min = bed_hour * 60 + bed_min
        wake_total_min = wake_hour * 60 + wake_min
        if wake_total_min < bed_total_min:
            wake_total_min += 24 * 60  # Add 24 hours

        sleep_minutes = wake_total_min - bed_total_min - latency
        total_sleep_hours = sleep_minutes / 60.0

        # Create SleepEntry
        entry = SleepEntry(
            id=str(uuid4()),
            user_id=str(update.effective_user.id),
            logged_at=datetime.now(),
            bedtime=time_type(bed_hour, bed_min),
            sleep_latency_minutes=latency,
            wake_time=time_type(wake_hour, wake_min),
            total_sleep_hours=round(total_sleep_hours, 2),
            night_wakings=quiz_data.get('night_wakings', 0),
            sleep_quality_rating=quiz_data['sleep_quality_rating'],
            disruptions=quiz_data.get('disruptions', []),
            phone_usage=quiz_data['phone_usage'],
            phone_duration_minutes=quiz_data.get('phone_duration_minutes'),
            alertness_rating=alertness
        )

        # Save to database
        await save_sleep_entry(entry)

        # Log feature usage
        await log_feature_usage(entry.user_id, "sleep_tracking")

        # Show summary
        hours = int(total_sleep_hours)
        minutes = int((total_sleep_hours % 1) * 60)
        quality_emoji = "😊" if entry.sleep_quality_rating >= 8 else "😐" if entry.sleep_quality_rating >= 5 else "😫"

        summary = f"""✅ **Sleep Logged!**

🛏️ **Bedtime:** {bedtime_str}
😴 **Fell asleep:** {latency} min
⏰ **Woke up:** {wake_str}
⏱️ **Total sleep:** {hours}h {minutes}m

🌙 **Quality:** {quality_emoji} {entry.sleep_quality_rating}/10
📱 **Phone usage:** {"Yes" if entry.phone_usage else "No"}
😌 **Alertness:** {alertness}/10

💡 **Tip:** You got {hours}h {minutes}m of sleep. Aim for 8-10h for optimal health!"""

        await query.edit_message_text(summary, parse_mode="Markdown")

        # Clean up quiz data
        del context.user_data['sleep_quiz_data']

        logger.info(f"Sleep quiz completed for user {entry.user_id}")

        return ConversationHandler.END

    except KeyError as e:
        logger.error(f"Missing quiz data key: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ **Error:** Quiz data incomplete. Please start over with /sleep_quiz",
            parse_mode="Markdown"
        )
        if 'sleep_quiz_data' in context.user_data:
            del context.user_data['sleep_quiz_data']
        return ConversationHandler.END

    except ValueError as e:
        logger.error(f"Invalid quiz data format: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ **Error:** Invalid data format. Please start over with /sleep_quiz",
            parse_mode="Markdown"
        )
        if 'sleep_quiz_data' in context.user_data:
            del context.user_data['sleep_quiz_data']
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error completing sleep quiz: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ **Error:** Failed to save sleep data. Please try again later.\n\n"
            "If the problem persists, contact support.",
            parse_mode="Markdown"
        )
        if 'sleep_quiz_data' in context.user_data:
            del context.user_data['sleep_quiz_data']
        return ConversationHandler.END


async def cancel_sleep_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the sleep quiz"""
    await update.message.reply_text("Sleep quiz cancelled. You can start again with /sleep_quiz")
    if 'sleep_quiz_data' in context.user_data:
        del context.user_data['sleep_quiz_data']
    return ConversationHandler.END


# Build conversation handler
sleep_quiz_handler = ConversationHandler(
    entry_points=[CommandHandler('sleep_quiz', start_sleep_quiz)],
    states={
        BEDTIME: [CallbackQueryHandler(handle_bedtime_callback)],
        SLEEP_LATENCY: [CallbackQueryHandler(handle_sleep_latency_callback)],
        WAKE_TIME: [CallbackQueryHandler(handle_wake_time_callback)],
        NIGHT_WAKINGS: [CallbackQueryHandler(handle_night_wakings_callback)],
        QUALITY: [CallbackQueryHandler(handle_quality_rating_callback)],
        PHONE: [
            CallbackQueryHandler(handle_phone_usage_callback, pattern="^phone_(yes|no)$"),
            CallbackQueryHandler(handle_phone_duration_callback, pattern="^phone_dur_")
        ],
        DISRUPTIONS: [CallbackQueryHandler(handle_disruptions_callback)],
        ALERTNESS: [CallbackQueryHandler(handle_alertness_callback)],
    },
    fallbacks=[CommandHandler('cancel', cancel_sleep_quiz)],
)
