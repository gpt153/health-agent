"""Sleep quiz settings conversation handler"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CommandHandler, CallbackQueryHandler, ContextTypes
)
from src.db.queries import (
    get_sleep_quiz_settings,
    save_sleep_quiz_settings,
    get_submission_patterns,
)
from src.models.sleep_settings import SleepQuizSettings
from src.utils.auth import is_authorized
from src.i18n.translations import t, get_user_language, get_supported_languages
from datetime import time as time_type
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Conversation states
MAIN_MENU, TIME_PICKER, LANGUAGE_PICKER = range(3)


async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for sleep quiz settings"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return ConversationHandler.END

    # Get or create settings
    settings_dict = await get_sleep_quiz_settings(user_id)

    if not settings_dict:
        # Create default settings
        lang = get_user_language(update.effective_user)
        # Try to get timezone from user profile
        user_tz = "UTC"  # Default fallback
        try:
            from src.db.queries import get_user_profile
            profile = await get_user_profile(user_id)
            if profile and profile.timezone:
                user_tz = profile.timezone
        except Exception as e:
            logger.warning(f"Could not get user timezone: {e}")

        settings = SleepQuizSettings(
            user_id=user_id,
            enabled=True,
            preferred_time=time_type(7, 0),
            timezone=user_tz,
            language_code=lang
        )
        await save_sleep_quiz_settings(settings)
        settings_dict = settings.model_dump()

    # Store in context for easy access
    context.user_data['sleep_settings'] = settings_dict
    context.user_data['settings_lang'] = settings_dict['language_code']

    return await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show main settings menu"""
    settings = context.user_data['sleep_settings']
    lang = context.user_data['settings_lang']

    # Format status
    status = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
    toggle_action = "Disable" if settings['enabled'] else "Enable"
    toggle_icon = "❌" if settings['enabled'] else "✅"

    # Format time
    pref_time = settings['preferred_time']
    if isinstance(pref_time, str):
        # Parse from string if needed
        hour, minute = map(int, pref_time.split(':')[:2])
        pref_time = time_type(hour, minute)

    time_str = pref_time.strftime("%H:%M")
    tz_str = settings['timezone']

    # Build message
    message = f"""{t('settings_title', lang=lang)}

{t('settings_enabled', lang=lang, status=status)}
{t('settings_time', lang=lang, time=time_str, timezone=tz_str)}
{t('settings_language', lang=lang, language=lang.upper())}

{t('settings_prompt', lang=lang)}"""

    # Build keyboard
    keyboard = [
        [InlineKeyboardButton(
            t('btn_toggle_quiz', lang=lang, icon=toggle_icon, action=toggle_action),
            callback_data="toggle_enabled"
        )],
        [InlineKeyboardButton(t('btn_change_time', lang=lang), callback_data="change_time")],
        [InlineKeyboardButton(t('btn_change_language', lang=lang), callback_data="change_language")],
        [InlineKeyboardButton(t('btn_view_patterns', lang=lang), callback_data="view_patterns")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

    return MAIN_MENU


async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu button callbacks"""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "toggle_enabled":
        # Toggle enabled status
        settings = context.user_data['sleep_settings']
        settings['enabled'] = not settings['enabled']

        # Save to database
        settings_model = SleepQuizSettings(**settings)
        await save_sleep_quiz_settings(settings_model)

        # Update scheduler
        try:
            from src.bot import application
            if application and hasattr(application, 'bot_data') and 'reminder_manager' in application.bot_data:
                reminder_manager = application.bot_data['reminder_manager']
                if settings['enabled']:
                    # Schedule quiz
                    await reminder_manager.schedule_sleep_quiz(
                        settings['user_id'],
                        settings['preferred_time'],
                        settings['timezone'],
                        settings['language_code']
                    )
                else:
                    # Cancel quiz job
                    job_name = f"sleep_quiz_{settings['user_id']}"
                    current_jobs = context.job_queue.get_jobs_by_name(job_name)
                    for job in current_jobs:
                        job.schedule_removal()
        except Exception as e:
            logger.error(f"Error updating scheduler: {e}", exc_info=True)

        # Show updated menu
        return await show_main_menu(update, context)

    elif action == "change_time":
        return await show_time_picker(update, context)

    elif action == "change_language":
        return await show_language_picker(update, context)

    elif action == "view_patterns":
        return await show_patterns(update, context)

    return MAIN_MENU


async def show_time_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show time picker for preferred quiz time"""
    settings = context.user_data['sleep_settings']
    lang = context.user_data['settings_lang']

    # Get current time or default
    pref_time = settings.get('preferred_time')
    if isinstance(pref_time, str):
        hour, minute = map(int, pref_time.split(':')[:2])
    elif isinstance(pref_time, time_type):
        hour, minute = pref_time.hour, pref_time.minute
    else:
        hour, minute = 7, 0

    # Store in temp state
    context.user_data['sleep_settings']['preferred_time_hour'] = hour
    context.user_data['sleep_settings']['preferred_time_minute'] = minute

    keyboard = [
        [
            InlineKeyboardButton("🔼", callback_data="time_h_up"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔼", callback_data="time_m_up"),
        ],
        [
            InlineKeyboardButton(f"{hour:02d}", callback_data="noop"),
            InlineKeyboardButton(":", callback_data="noop"),
            InlineKeyboardButton(f"{minute:02d}", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("🔽", callback_data="time_h_down"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔽", callback_data="time_m_down"),
        ],
        [InlineKeyboardButton(t('btn_confirm', lang=lang), callback_data="time_confirm")],
        [InlineKeyboardButton(t('btn_back', lang=lang), callback_data="time_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"**{t('btn_change_time', lang=lang)}**\n\nUse ⬆️⬇️ to adjust time"
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return TIME_PICKER


async def handle_time_picker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time picker callbacks"""
    query = update.callback_query
    await query.answer()

    data = query.data
    settings = context.user_data['sleep_settings']
    hour = settings.get('preferred_time_hour', 7)
    minute = settings.get('preferred_time_minute', 0)

    if data == "time_h_up":
        hour = (hour + 1) % 24
    elif data == "time_h_down":
        hour = (hour - 1) % 24
    elif data == "time_m_up":
        minute = (minute + 15) % 60
    elif data == "time_m_down":
        minute = (minute - 15) % 60
    elif data == "time_confirm":
        # Save new time
        settings['preferred_time'] = time_type(hour, minute)
        settings_model = SleepQuizSettings(**settings)
        await save_sleep_quiz_settings(settings_model)

        # Update scheduler if enabled
        try:
            from src.bot import application
            if application and hasattr(application, 'bot_data') and 'reminder_manager' in application.bot_data:
                reminder_manager = application.bot_data['reminder_manager']
                if settings['enabled']:
                    # Cancel old job
                    job_name = f"sleep_quiz_{settings['user_id']}"
                    current_jobs = context.job_queue.get_jobs_by_name(job_name)
                    for job in current_jobs:
                        job.schedule_removal()
                    # Schedule new job
                    await reminder_manager.schedule_sleep_quiz(
                        settings['user_id'],
                        settings['preferred_time'],
                        settings['timezone'],
                        settings['language_code']
                    )
        except Exception as e:
            logger.error(f"Error updating scheduler: {e}", exc_info=True)

        # Show confirmation and return to menu
        lang = context.user_data['settings_lang']
        await query.edit_message_text(t('settings_updated', lang=lang))
        return await show_main_menu(update, context)

    elif data == "time_cancel":
        return await show_main_menu(update, context)
    elif data == "noop":
        return TIME_PICKER

    # Update stored values
    settings['preferred_time_hour'] = hour
    settings['preferred_time_minute'] = minute

    # Rebuild picker
    return await show_time_picker(update, context)


async def show_language_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show language selection menu"""
    lang = context.user_data['settings_lang']

    # Build keyboard with available languages
    keyboard = []
    for lang_code in get_supported_languages():
        display_name = {'en': 'English', 'sv': 'Svenska', 'es': 'Español'}.get(lang_code, lang_code.upper())
        keyboard.append([InlineKeyboardButton(
            f"{'✅ ' if lang_code == lang else ''}{display_name}",
            callback_data=f"lang_{lang_code}"
        )])
    keyboard.append([InlineKeyboardButton(t('btn_back', lang=lang), callback_data="lang_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"**{t('btn_change_language', lang=lang)}**\n\nSelect your language:"
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return LANGUAGE_PICKER


async def handle_language_picker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("lang_"):
        new_lang = data.replace("lang_", "")

        if new_lang in get_supported_languages():
            # Update language
            settings = context.user_data['sleep_settings']
            settings['language_code'] = new_lang
            context.user_data['settings_lang'] = new_lang

            # Save to database
            settings_model = SleepQuizSettings(**settings)
            await save_sleep_quiz_settings(settings_model)

            # Show confirmation
            await query.edit_message_text(t('settings_updated', lang=new_lang))
            return await show_main_menu(update, context)

    elif data == "lang_cancel":
        return await show_main_menu(update, context)

    return LANGUAGE_PICKER


async def show_patterns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show submission pattern analysis"""
    user_id = str(update.effective_user.id)
    lang = context.user_data['settings_lang']

    # Get submission patterns
    patterns = await get_submission_patterns(user_id, days=30)

    if len(patterns) < 3:
        message = f"📊 **Submission Patterns**\n\nNot enough data yet. Complete at least 3 quizzes to see patterns.\n\nCompleted: {len(patterns)}/3"
    else:
        # Calculate average delay
        delays = [p['response_delay_minutes'] for p in patterns]
        avg_delay = sum(delays) / len(delays)

        # Calculate suggested time
        settings = context.user_data['sleep_settings']
        pref_time = settings.get('preferred_time')
        if isinstance(pref_time, str):
            scheduled_hour, scheduled_minute = map(int, pref_time.split(':')[:2])
        elif isinstance(pref_time, time_type):
            scheduled_hour, scheduled_minute = pref_time.hour, pref_time.minute
        else:
            scheduled_hour, scheduled_minute = 7, 0

        # Suggest new time (scheduled + average delay)
        suggested_minutes = (scheduled_hour * 60 + scheduled_minute + int(avg_delay)) % (24 * 60)
        suggested_hour = suggested_minutes // 60
        suggested_minute = suggested_minutes % 60

        message = f"""📊 **Submission Patterns**

**Data:** {len(patterns)} submissions (last 30 days)
**Average delay:** {int(avg_delay)} minutes

**Current scheduled time:** {scheduled_hour:02d}:{scheduled_minute:02d}
**Average completion time:** {suggested_hour:02d}:{suggested_minute:02d}

💡 **Suggestion:** {"Your current time works well!" if avg_delay < 30 else f"Consider changing to {suggested_hour:02d}:{suggested_minute:02d} for better alignment."}"""

    keyboard = [[InlineKeyboardButton(t('btn_back', lang=lang), callback_data="patterns_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")

    return MAIN_MENU


async def handle_patterns_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle patterns view callback"""
    query = update.callback_query
    await query.answer()

    if query.data == "patterns_back":
        return await show_main_menu(update, context)

    return MAIN_MENU


async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel settings conversation"""
    await update.message.reply_text("Settings cancelled.")
    if 'sleep_settings' in context.user_data:
        del context.user_data['sleep_settings']
    return ConversationHandler.END


# Build conversation handler
sleep_settings_handler = ConversationHandler(
    entry_points=[CommandHandler('sleep_settings', settings_start)],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(handle_main_menu_callback),
            CallbackQueryHandler(handle_patterns_callback, pattern="^patterns_"),
        ],
        TIME_PICKER: [CallbackQueryHandler(handle_time_picker_callback)],
        LANGUAGE_PICKER: [CallbackQueryHandler(handle_language_picker_callback)],
    },
    fallbacks=[CommandHandler('cancel', cancel_settings)],
)
