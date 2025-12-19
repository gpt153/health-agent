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
from src.i18n.translations import t, get_user_language
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

    # Detect user's language
    lang = get_user_language(update.effective_user)

    # Initialize quiz data storage with language
    context.user_data['sleep_quiz_data'] = {'lang': lang}

    message = t('quiz_welcome', lang=lang)

    await update.message.reply_text(message, parse_mode="Markdown")

    # Show first question immediately
    return await show_bedtime_question(update, context)


async def show_bedtime_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show bedtime question with time picker"""
    user_id = str(update.effective_user.id)
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')

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
        [InlineKeyboardButton(t('btn_confirm', lang=lang), callback_data="bed_confirm")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = t('q1_bedtime', lang=lang)

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
    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
    keyboard = [
        [InlineKeyboardButton(t('latency_less_15', lang=lang), callback_data="latency_0")],
        [InlineKeyboardButton(t('latency_15_30', lang=lang), callback_data="latency_15")],
        [InlineKeyboardButton(t('latency_30_60', lang=lang), callback_data="latency_45")],
        [InlineKeyboardButton(t('latency_60_plus', lang=lang), callback_data="latency_90")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = t('q2_latency', lang=lang)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return SLEEP_LATENCY


async def handle_sleep_latency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sleep latency selection"""
    query = update.callback_query
    await query.answer()

    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')# Parse latency from callback_data
    latency_str = query.data.replace("latency_", "")
    latency_minutes = int(latency_str)

    context.user_data['sleep_quiz_data']['sleep_latency_minutes'] = latency_minutes

    # Confirm selection
    await query.edit_message_text(t('confirmed_latency', lang=lang, minutes=latency_minutes))

    return await show_wake_time_question(update, context)


async def show_wake_time_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show wake time question with time picker"""
    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
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
        [InlineKeyboardButton(t('btn_confirm', lang=lang), callback_data="wake_confirm")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = t('q3_wake_time', lang=lang)

    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return WAKE_TIME


async def handle_wake_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wake time picker callbacks"""
    query = update.callback_query
    await query.answer()

    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
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
    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
    keyboard = [
        [InlineKeyboardButton(t('wakings_no', lang=lang), callback_data="wakings_0")],
        [InlineKeyboardButton(t('wakings_1_2', lang=lang), callback_data="wakings_1")],
        [InlineKeyboardButton(t('wakings_3_plus', lang=lang), callback_data="wakings_3")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = t('q4_wakings', lang=lang)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return NIGHT_WAKINGS


async def handle_night_wakings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle night wakings selection"""
    query = update.callback_query
    await query.answer()

    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')# Parse wakings from callback_data
    wakings_str = query.data.replace("wakings_", "")
    if wakings_str == "0":
        wakings = 0
    elif wakings_str == "1":
        wakings = 2  # Midpoint of 1-2
    else:  # "3"
        wakings = 4  # Estimate for 3+

    context.user_data['sleep_quiz_data']['night_wakings'] = wakings

    # Confirm selection
    await query.edit_message_text(t('confirmed_wakings', lang=lang, count=wakings))

    return await show_quality_rating_question(update, context)


async def show_quality_rating_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q5: Quality rating with button grid"""
    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"quality_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"quality_{i}") for i in range(6, 11)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = t('q5_quality', lang=lang)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return QUALITY


async def handle_quality_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quality rating selection"""
    query = update.callback_query
    await query.answer()

    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')# Parse quality from callback_data
    quality = int(query.data.replace("quality_", ""))

    context.user_data['sleep_quiz_data']['sleep_quality_rating'] = quality

    # Confirm selection
    quality_emoji = "😊" if quality >= 8 else "😐" if quality >= 5 else "😫"
    await query.edit_message_text(t('confirmed_quality', lang=lang, emoji=quality_emoji, rating=quality))

    return await show_phone_usage_question(update, context)


async def show_phone_usage_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q6: Phone usage toggle"""
    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
    keyboard = [
        [
            InlineKeyboardButton(t('btn_yes', lang=lang), callback_data="phone_yes"),
            InlineKeyboardButton(t('btn_no', lang=lang), callback_data="phone_no"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = t('q6_phone', lang=lang)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return PHONE


async def handle_phone_usage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone usage - conditional follow-up"""
    query = update.callback_query
    await query.answer()

    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
    if query.data == "phone_yes":
        context.user_data['sleep_quiz_data']['phone_usage'] = True
        # Show follow-up duration question
        keyboard = [
            [InlineKeyboardButton(t('phone_dur_less_15', lang=lang), callback_data="phone_dur_7")],
            [InlineKeyboardButton(t('latency_15_30', lang=lang), callback_data="phone_dur_22")],
            [InlineKeyboardButton(t('latency_30_60', lang=lang), callback_data="phone_dur_45")],
            [InlineKeyboardButton(t('phone_dur_60_plus', lang=lang), callback_data="phone_dur_90")],
        ]
        text = t('q6_duration', lang=lang)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return PHONE
    else:
        context.user_data['sleep_quiz_data']['phone_usage'] = False
        context.user_data['sleep_quiz_data']['phone_duration_minutes'] = 0
        await query.edit_message_text(t('confirmed_phone_no', lang=lang))
        return await show_disruptions_question(update, context)


async def handle_phone_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone duration selection"""
    query = update.callback_query
    await query.answer()

    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')# Parse duration from callback_data
    duration = int(query.data.replace("phone_dur_", ""))

    context.user_data['sleep_quiz_data']['phone_duration_minutes'] = duration

    # Confirm selection
    await query.edit_message_text(t('confirmed_phone_duration', lang=lang, minutes=duration))

    return await show_disruptions_question(update, context)


async def show_disruptions_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Q7: Disruptions multi-select"""
    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')# Initialize selections set if not exists
    if 'disruptions_selected' not in context.user_data['sleep_quiz_data']:
        context.user_data['sleep_quiz_data']['disruptions_selected'] = set()

    selected = context.user_data['sleep_quiz_data']['disruptions_selected']

    keyboard = [
        [InlineKeyboardButton(
            f"{'✅ ' if 'noise' in selected else ''}{t('disruption_noise', lang=lang)}",
            callback_data="disrupt_noise"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'light' in selected else ''}{t('disruption_light', lang=lang)}",
            callback_data="disrupt_light"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'temp' in selected else ''}{t('disruption_temp', lang=lang)}",
            callback_data="disrupt_temp"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'stress' in selected else ''}{t('disruption_stress', lang=lang)}",
            callback_data="disrupt_stress"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'dream' in selected else ''}{t('disruption_dream', lang=lang)}",
            callback_data="disrupt_dream"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'pain' in selected else ''}{t('disruption_pain', lang=lang)}",
            callback_data="disrupt_pain"
        )],
        [InlineKeyboardButton(t('btn_done', lang=lang), callback_data="disrupt_done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = t('q7_disruptions', lang=lang)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return DISRUPTIONS


async def handle_disruptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle disruptions toggle"""
    query = update.callback_query
    await query.answer()

    
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
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
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
    # Get current selection if it exists
    selected = context.user_data['sleep_quiz_data'].get('alertness_rating')

    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"alert_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"alert_{i}") for i in range(6, 11)],
    ]

    # Add submit button if a selection has been made
    if selected:
        keyboard.append([InlineKeyboardButton(t('btn_submit', lang=lang), callback_data="alert_submit")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Use translated text with dynamic content based on selection
    if selected:
        text = t('q8_alertness_selected', lang=lang, rating=selected)
    else:
        text = t('q8_alertness', lang=lang)

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
            lang = quiz_data.get('lang', 'en')

            # Validate that alertness rating was selected
            if 'alertness_rating' not in quiz_data:
                await query.edit_message_text(
                    t('error_select_rating', lang=lang),
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
        lang = quiz_data.get('lang', 'en')
        required_fields = ['bedtime', 'wake_time', 'sleep_latency_minutes',
                          'sleep_quality_rating', 'phone_usage']
        missing_fields = [f for f in required_fields if f not in quiz_data]

        if missing_fields:
            logger.error(f"Missing quiz data fields: {missing_fields}")
            await query.edit_message_text(
                f"{t('error_incomplete', lang=lang)}\n\n"
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
        user_id = str(update.effective_user.id)
        entry = SleepEntry(
            id=str(uuid4()),
            user_id=user_id,
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

        # Track submission for pattern learning
        try:
            # Get scheduled time from bot_data (set by automated quiz trigger)
            scheduled_time = context.bot_data.get(f"sleep_quiz_scheduled_{user_id}")

            if scheduled_time:
                # Calculate delay in minutes
                from src.db.queries import save_sleep_quiz_submission
                from src.models.sleep_settings import SleepQuizSubmission

                submitted_at = datetime.now()
                delay = int((submitted_at - scheduled_time).total_seconds() / 60)

                # Save submission pattern
                submission = SleepQuizSubmission(
                    id=str(uuid4()),
                    user_id=user_id,
                    scheduled_time=scheduled_time,
                    submitted_at=submitted_at,
                    response_delay_minutes=delay
                )
                await save_sleep_quiz_submission(submission)

                # Clear from bot_data
                del context.bot_data[f"sleep_quiz_scheduled_{user_id}"]

                logger.info(f"Tracked submission pattern: {delay}min delay for {user_id}")
        except Exception as e:
            logger.error(f"Failed to track submission pattern: {e}", exc_info=True)

        # Show summary
        hours = int(total_sleep_hours)
        minutes = int((total_sleep_hours % 1) * 60)
        quality_emoji = "😊" if entry.sleep_quality_rating >= 8 else "😐" if entry.sleep_quality_rating >= 5 else "😫"
        phone_usage_text = t('yes', lang=lang) if entry.phone_usage else t('no', lang=lang)

        summary = f"""{t('summary_title', lang=lang)}

{t('summary_bedtime', lang=lang, time=bedtime_str)}
{t('summary_latency', lang=lang, minutes=latency)}
{t('summary_wake', lang=lang, time=wake_str)}
{t('summary_total', lang=lang, hours=hours, minutes=minutes)}

{t('summary_quality', lang=lang, emoji=quality_emoji, rating=entry.sleep_quality_rating)}
{t('summary_phone', lang=lang, usage=phone_usage_text)}
{t('summary_alertness', lang=lang, rating=alertness)}

{t('summary_tip', lang=lang, hours=hours, minutes=minutes)}"""

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
    lang = 'en'  # Default language for cancel message
    await update.message.reply_text(t('quiz_cancelled', lang=lang))
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
