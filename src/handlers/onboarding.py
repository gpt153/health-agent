"""Onboarding handlers for dual-path progressive onboarding"""
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from src.db.queries import (
    get_onboarding_state,
    start_onboarding,
    update_onboarding_step,
    complete_onboarding,
    log_feature_discovery,
    get_user_subscription_status
)
from src.models.onboarding import ONBOARDING_PATHS, TRACKABLE_FEATURES
from src.memory.file_manager import memory_manager
from src.utils.auth import is_authorized

logger = logging.getLogger(__name__)


async def handle_onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show path selection screen after activation
    Called from refactored /start command
    """
    user_id = str(update.effective_user.id)

    # Check if already has onboarding state
    state = await get_onboarding_state(user_id)

    if state and state.get('completed_at'):
        # Already completed onboarding, show regular welcome
        await update.message.reply_text(
            "👋 Welcome back! How can I help you today?\n\n"
            "Send a food photo, ask me anything, or type /help for commands."
        )
        return

    # Show path selection with inline keyboard
    message = (
        "✅ You're all set! Let's get you started.\n\n"
        "I'm your AI health coach - I track food, workouts, sleep, "
        "give pep talks, and learn your habits over time.\n\n"
        "**How should we start?**"
    )

    # Create keyboard with three options (with time estimates)
    keyboard = [
        ["Quick Start 🚀 (30 sec)"],
        ["Show Me Around 🎬 (2 min)"],
        ["Just Chat 💬 (start now)"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup)

    # Initialize onboarding state
    await start_onboarding(user_id, "pending")  # Will be set when user picks path

    logger.info(f"Showed path selection to user {user_id}")


async def handle_path_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle user's path selection (Quick Start, Full Tour, Just Chat)
    """
    user_id = str(update.effective_user.id)
    text = update.message.text.lower()

    # Determine selected path
    if "quick" in text or "🚀" in text:
        path = "quick"
    elif "show" in text or "tour" in text or "around" in text or "🎬" in text:
        path = "full"
    elif "chat" in text or "💬" in text:
        path = "chat"
    else:
        # Invalid selection, show options again
        await update.message.reply_text(
            "Please choose one of the three options:",
            reply_markup=ReplyKeyboardMarkup(
                [["Quick Start 🚀 (30 sec)"], ["Show Me Around 🎬 (2 min)"], ["Just Chat 💬 (start now)"]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return

    # Update state with selected path
    await start_onboarding(user_id, path)

    # Route to appropriate first step
    if path == "quick":
        await quick_start_timezone(update, context)
    elif path == "full":
        await full_tour_timezone(update, context)
    elif path == "chat":
        await just_chat_start(update, context)

    logger.info(f"User {user_id} selected path: {path}")


# Timezone to language mapping
TIMEZONE_LANGUAGE_MAP = {
    'Europe/Stockholm': ('sv', 'Vill du att vi talar svenska från nu?', '🇸🇪'),
    'Europe/Helsinki': ('fi', 'Haluatko, että puhumme suomea tästä lähtien?', '🇫🇮'),
    'Europe/Oslo': ('no', 'Vil du at vi snakker norsk fra nå av?', '🇳🇴'),
    'Europe/Copenhagen': ('da', 'Vil du have, at vi taler dansk fra nu af?', '🇩🇰'),
    'Europe/Berlin': ('de', 'Möchten Sie, dass wir ab jetzt Deutsch sprechen?', '🇩🇪'),
    'Europe/Paris': ('fr', 'Voulez-vous que nous parlions français désormais?', '🇫🇷'),
    'Europe/Madrid': ('es', '¿Quieres que hablemos español a partir de ahora?', '🇪🇸'),
    'Europe/Rome': ('it', 'Vuoi che parliamo italiano da ora in poi?', '🇮🇹'),
    'Europe/Amsterdam': ('nl', 'Wil je dat we vanaf nu Nederlands spreken?', '🇳🇱'),
    'Europe/Lisbon': ('pt', 'Quer que falemos português a partir de agora?', '🇵🇹'),
    'Europe/Warsaw': ('pl', 'Czy chcesz, żebyśmy mówili po polsku od teraz?', '🇵🇱'),
    'Europe/Moscow': ('ru', 'Хотите, чтобы мы говорили по-русски с этого момента?', '🇷🇺'),
    'Asia/Tokyo': ('ja', 'これから日本語で話しましょうか？', '🇯🇵'),
    'Asia/Shanghai': ('zh', '您希望我们从现在开始说中文吗？', '🇨🇳'),
    'Asia/Seoul': ('ko', '지금부터 한국어로 대화하시겠습니까?', '🇰🇷'),
}


async def ask_language_preference(update: Update, context: ContextTypes.DEFAULT_TYPE, timezone: str) -> None:
    """Ask if user wants to use their local language based on timezone"""
    user_id = str(update.effective_user.id)
    state = await get_onboarding_state(user_id)
    path = state.get('onboarding_path')

    # Check if timezone maps to a non-English language
    if timezone in TIMEZONE_LANGUAGE_MAP:
        lang_code, question, flag = TIMEZONE_LANGUAGE_MAP[timezone]

        keyboard = [
            [f"Yes / Ja {flag}"],
            ["No, English is fine 🇬🇧"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

        message = f"{flag} {question}\n\n(I can speak {lang_code.upper()} or continue in English)"

        await update.message.reply_text(message, reply_markup=reply_markup)
        await update_onboarding_step(user_id, "language_selection", mark_complete="timezone_setup")
    else:
        # English timezone, skip language question
        if path == "quick":
            await quick_start_focus_selection(update, context)
        elif path == "full":
            await full_tour_profile_setup(update, context)


async def quick_start_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Start Step 1: Set timezone"""
    user_id = str(update.effective_user.id)

    # Check if user already has timezone
    from src.utils.timezone_helper import get_timezone_from_profile
    existing_tz = get_timezone_from_profile(user_id)

    if existing_tz:
        # Already has timezone, go to language question
        await ask_language_preference(update, context, existing_tz)
        return

    # Show timezone setup
    message = (
        "🌍 What's your timezone?\n\n"
        "Two ways to set it:\n"
        "📍 Share your location (tap 📎 → Location)\n"
        "⌨️ Or type it: 'America/New_York', 'Europe/London', etc.\n\n"
        "Why? So reminders hit at the right time!"
    )

    # Create keyboard with location button
    keyboard = [[KeyboardButton("📍 Share Location", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup)
    await update_onboarding_step(user_id, "timezone_setup")


async def quick_start_focus_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Start Step 2: Pick main focus"""
    user_id = str(update.effective_user.id)

    message = (
        "🎯 **What's your main goal right now?**\n\n"
        "Pick what matters most to you:"
    )

    keyboard = [
        ["🍽️ Track nutrition"],
        ["💪 Build workout habit"],
        ["😴 Improve sleep"],
        ["🏃 General health coaching"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup)
    await update_onboarding_step(user_id, "focus_selection", mark_complete="timezone_setup")


async def quick_start_feature_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Start Step 3: Demo the selected feature"""
    user_id = str(update.effective_user.id)
    text = update.message.text.lower()

    # Determine selected focus and show appropriate demo
    if "nutrition" in text or "food" in text or "🍽️" in text:
        focus = "nutrition"
        message = (
            "🍽️ **Perfect! Let's try it right now.**\n\n"
            "Send me a photo of your last meal or snack.\n"
            "I'll analyze it and show you calories + macros instantly.\n\n"
            "📸 **Try it →** (send any food photo)"
        )
        await log_feature_discovery(user_id, "food_tracking", "onboarding")

    elif "workout" in text or "exercise" in text or "💪" in text:
        focus = "workout"
        message = (
            "💪 **Nice! Let's log your first workout.**\n\n"
            "Tell me what you did today. Examples:\n"
            "• 'Just did 30 min cardio'\n"
            "• 'Leg day: squats, deadlifts, lunges'\n"
            "• 'Rest day'\n\n"
            "I'll remember it and can remind you tomorrow!"
        )
        await log_feature_discovery(user_id, "custom_tracking", "onboarding")

    elif "sleep" in text or "😴" in text:
        focus = "sleep"
        message = (
            "😴 **Great choice! Sleep is crucial.**\n\n"
            "Rate your sleep quality last night (1-10).\n\n"
            "I'll track this and help you spot patterns!"
        )
        await log_feature_discovery(user_id, "custom_tracking", "onboarding")

    else:
        focus = "general"
        message = (
            "🏃 **Awesome! I'm here to help with everything.**\n\n"
            "Let's start simple: Tell me about your health goals.\n"
            "Just chat naturally - I'll suggest features as you need them!"
        )

    # Save focus to step_data
    state = await get_onboarding_state(user_id)
    step_data = state.get('step_data', {}) if state else {}
    step_data['focus'] = focus

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    await update_onboarding_step(user_id, "feature_demo", step_data=step_data, mark_complete="focus_selection")


async def quick_start_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Start Step 4: Complete onboarding"""
    user_id = str(update.effective_user.id)

    message = (
        "🎉 **Great! That's the core flow.**\n\n"
        "⚡ **Quick tips:**\n"
        "• Send photos anytime → I'll analyze food\n"
        "• Voice notes work too (I transcribe them)\n"
        "• Just chat normally - I'll suggest features as you need them\n\n"
        "Want to see everything I can do? Type \"show features\" or just start chatting!"
    )

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    await complete_onboarding(user_id)

    logger.info(f"User {user_id} completed Quick Start onboarding")


async def full_tour_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 1: Set timezone (same as quick start)"""
    await quick_start_timezone(update, context)


async def full_tour_profile_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 2: Collect profile information"""
    user_id = str(update.effective_user.id)

    message = (
        "👤 **Tell me about yourself** (optional, but helps me personalize):\n\n"
        "• What's your name?\n"
        "• Your age?\n"
        "• Current goal? (lose weight, build muscle, maintain health)\n\n"
        "You can skip any question - just say \"skip\" or \"next\""
    )

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    await update_onboarding_step(user_id, "profile_setup", mark_complete="timezone_setup")


async def full_tour_food_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 3: Interactive food tracking demo"""
    user_id = str(update.effective_user.id)

    message = (
        "🎬 **Here's what I can do. Let's try them!**\n\n"
        "**1️⃣ 📸 FOOD TRACKING**\n"
        "Send me ANY food photo → instant calories + macros\n"
        "No logging, no searching databases - just snap and send.\n\n"
        "→ **Try it now:** Send me a photo from your gallery!"
    )

    await update.message.reply_text(message)
    await update_onboarding_step(user_id, "food_demo", mark_complete="profile_setup")
    await log_feature_discovery(user_id, "food_tracking", "onboarding")


async def full_tour_voice_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 4: Voice notes demo"""
    user_id = str(update.effective_user.id)

    message = (
        "**2️⃣ 🎤 VOICE NOTES**\n"
        "Too lazy to type? Just speak to me!\n"
        "I transcribe everything and understand context.\n\n"
        "Examples:\n"
        "• \"I had chicken and rice for lunch\"\n"
        "• \"Remind me to drink water in 2 hours\"\n"
        "• \"How many calories should I eat today?\"\n\n"
        "→ **Try it:** Tap 🎤 and say anything!"
    )

    await update.message.reply_text(message)
    await update_onboarding_step(user_id, "voice_demo", mark_complete="food_demo")
    await log_feature_discovery(user_id, "voice_notes", "onboarding")


async def full_tour_tracking_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 5: Custom tracking demo"""
    user_id = str(update.effective_user.id)

    message = (
        "**3️⃣ 📊 TRACK ANYTHING**\n"
        "Food, workouts, sleep, mood, water, steps - I track it all.\n"
        "Just tell me naturally:\n\n"
        "• \"I slept 7 hours last night\"\n"
        "• \"Drank 2 liters of water today\"\n"
        "• \"Did 30 min cardio\"\n\n"
        "I'll spot patterns and remind you when needed.\n\n"
        "→ **Skip or tell me something you track**"
    )

    keyboard = [["Skip for now →"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup)
    await update_onboarding_step(user_id, "tracking_demo", mark_complete="voice_demo")


async def full_tour_reminders_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 6: Reminders demo"""
    user_id = str(update.effective_user.id)

    message = (
        "**4️⃣ ⏰ SMART REMINDERS**\n"
        "I remember things so you don't have to:\n\n"
        "• \"Remind me to log dinner at 7pm\"\n"
        "• \"Ask me about my workout tomorrow morning\"\n"
        "• \"Daily reminder to drink water at 10am\"\n\n"
        "I learn your patterns and suggest reminders automatically.\n\n"
        "→ **Skip or set a test reminder**"
    )

    keyboard = [["Skip for now →"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup)
    await update_onboarding_step(user_id, "reminders_demo", mark_complete="tracking_demo")
    await log_feature_discovery(user_id, "reminders", "onboarding")


async def full_tour_personality_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 7: Personality customization demo"""
    user_id = str(update.effective_user.id)

    message = (
        "**5️⃣ 🎭 CUSTOMIZABLE PERSONALITY**\n"
        "I adapt to how you want me to communicate:\n\n"
        "• Supportive coach 💪\n"
        "• Tough drill sergeant 🎯\n"
        "• Scientific advisor 🔬\n"
        "• Casual friend 😊\n\n"
        "Change it anytime with /settings\n\n"
        "→ **Continue**"
    )

    keyboard = [["Continue →"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup)
    await update_onboarding_step(user_id, "personality_demo", mark_complete="reminders_demo")


async def full_tour_learning_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 8: Explain learning system"""
    user_id = str(update.effective_user.id)

    message = (
        "**6️⃣ 🧠 I LEARN ABOUT YOU**\n"
        "Everything we discuss, I remember:\n\n"
        "• Your food preferences and allergies\n"
        "• Your workout routine and goals\n"
        "• Your schedule and habits\n"
        "• What motivates you\n\n"
        "Type /transparency anytime to see what I know.\n"
        "You can ask me to forget specific things.\n\n"
        "→ **Ready to start?**"
    )

    keyboard = [["Yes, let's go! 🚀"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup)
    await update_onboarding_step(user_id, "learning_explanation", mark_complete="personality_demo")


async def full_tour_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour: Complete onboarding after all demos"""
    user_id = str(update.effective_user.id)

    message = (
        "🎉 **Tour complete! You're ready.**\n\n"
        "📝 **Quick reference:**\n"
        "/transparency - See what I know about you\n"
        "/settings - Change my personality\n"
        "/help - Full command list\n\n"
        "🚀 **Start by:**\n"
        "• Sending a food photo\n"
        "• Telling me your goal\n"
        "• Or just chat - I'll guide you!\n\n"
        "What would you like to do first?"
    )

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    await complete_onboarding(user_id)

    logger.info(f"User {user_id} completed Full Tour onboarding")


async def just_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Just Chat: Start organic discovery mode"""
    user_id = str(update.effective_user.id)

    message = (
        "💬 **Perfect! I learn best through conversation anyway.**\n\n"
        "Tell me what brings you here - a goal, a question, "
        "or just 'I want to get healthier' works too.\n\n"
        "I'll introduce features naturally as you need them."
    )

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    await complete_onboarding(user_id)  # Mark as complete, but discovery is ongoing

    logger.info(f"User {user_id} selected Just Chat path")


async def handle_onboarding_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main router for onboarding messages
    Called from bot.py handle_message() when user is in onboarding
    """
    user_id = str(update.effective_user.id)
    state = await get_onboarding_state(user_id)

    if not state:
        # No onboarding state, shouldn't be here
        return

    current_step = state.get('current_step')
    path = state.get('onboarding_path')

    # Route to appropriate handler based on current step
    if current_step == "path_selection":
        await handle_path_selection(update, context)

    elif current_step == "timezone_setup":
        # Handle timezone input (either location or text)
        tz = None
        if update.message.location:
            # Location shared
            from src.utils.timezone_helper import get_timezone_from_coordinates, update_timezone_in_profile
            lat = update.message.location.latitude
            lon = update.message.location.longitude
            tz = get_timezone_from_coordinates(lat, lon)
            update_timezone_in_profile(user_id, tz)

            await update.message.reply_text(
                f"✅ Got it! Your timezone is **{tz}**",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            # Text timezone
            from src.utils.timezone_helper import update_timezone_in_profile
            import pytz
            try:
                tz_input = update.message.text.strip()
                pytz.timezone(tz_input)  # Validate
                update_timezone_in_profile(user_id, tz_input)
                await update.message.reply_text(
                    f"✅ Great! Your timezone is now **{tz_input}**",
                    parse_mode="Markdown"
                )
            except:
                await update.message.reply_text(
                    "❌ Invalid timezone. Try \"America/New_York\" or share your location."
                )
                return
            tz = tz_input

        # Save timezone to step_data
        state = await get_onboarding_state(user_id)
        step_data = state.get('step_data', {}) if state else {}
        step_data['timezone'] = tz
        await update_onboarding_step(user_id, None, step_data=step_data)

        # Ask language preference based on timezone
        await ask_language_preference(update, context, tz)

    elif current_step == "language_selection":
        # Handle language preference response
        text = update.message.text.lower()

        # Check if user wants native language (yes/ja/oui/si/etc) or English
        if "no" in text or "english" in text or "🇬🇧" in text:
            language = "en"
            await update.message.reply_text("👍 Alright, we'll continue in English!")
        else:
            # User wants native language - extract from step_data timezone
            state = await get_onboarding_state(user_id)
            step_data = state.get('step_data', {})
            # For now, just acknowledge - actual language switching would need more implementation
            language = "native"
            await update.message.reply_text("👍 Perfect! (Note: Full multilingual support coming soon - for now I'll use English)")

        # Save language preference in step_data
        step_data = state.get('step_data', {}) if state else {}
        step_data['language'] = language
        await update_onboarding_step(user_id, None, step_data=step_data, mark_complete="language_selection")

        # Route to next step based on path
        if path == "quick":
            await quick_start_focus_selection(update, context)
        elif path == "full":
            await full_tour_profile_setup(update, context)

    elif current_step == "focus_selection":
        await quick_start_feature_demo(update, context)

    elif current_step == "feature_demo":
        # User tried the feature, complete quick start
        await quick_start_complete(update, context)

    elif current_step == "profile_setup":
        # Save profile data and advance
        # TODO: Parse name/age/goals from user message and save to memory
        await full_tour_food_demo(update, context)

    elif current_step == "food_demo":
        # User sent food photo or message, advance to voice demo
        await full_tour_voice_demo(update, context)

    elif current_step == "voice_demo":
        # User tried voice or skipped, advance to tracking
        await full_tour_tracking_demo(update, context)

    elif current_step == "tracking_demo":
        # User shared tracking info or skipped, advance to reminders
        await full_tour_reminders_demo(update, context)

    elif current_step == "reminders_demo":
        # User set reminder or skipped, advance to personality
        await full_tour_personality_demo(update, context)

    elif current_step == "personality_demo":
        # User acknowledged, advance to learning explanation
        await full_tour_learning_explanation(update, context)

    elif current_step == "learning_explanation":
        # User ready to start, complete the tour
        await full_tour_complete(update, context)

    # Add more step handlers as needed
