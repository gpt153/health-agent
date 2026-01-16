"""Telegram bot setup and handlers"""
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import telegram.error
from src.config import TELEGRAM_BOT_TOKEN, DATA_PATH, TELEGRAM_TOPIC_FILTER, ENABLE_SENTRY
from src.utils.auth import is_authorized
from src.db.queries import (
    create_user,
    user_exists,
    save_food_entry,
    save_conversation_message,
    get_conversation_history,
    clear_conversation_history,
    approve_tool,
    reject_tool,
    get_tool_by_name,
    get_pending_approvals,
)
from src.memory.file_manager import memory_manager
from src.memory.mem0_manager import mem0_manager
from src.agent import get_agent_response
from src.agent.dynamic_tools import tool_manager
from src.utils.vision import analyze_food_photo
from src.utils.voice import transcribe_voice
from src.models.food import FoodEntry
from src.scheduler.reminder_manager import ReminderManager
from src.handlers.onboarding import (
    handle_onboarding_start,
    handle_onboarding_message,
    onboarding_path_selection_handler,
    onboarding_language_selection_handler,
    onboarding_focus_selection_handler
)
from src.handlers.sleep_quiz import sleep_quiz_handler
from src.handlers.sleep_settings import sleep_settings_handler
from src.handlers.reminders import (
    reminder_completion_handler,
    reminder_skip_handler,
    skip_reason_handler,
    reminder_snooze_handler,
    add_note_handler,
    note_template_handler,
    note_custom_handler,
    note_skip_handler
)
from src.gamification.integrations import (
    handle_food_entry_gamification,
    handle_sleep_quiz_gamification,
    handle_tracking_entry_gamification
)
from src.handlers.custom_tracking import (
    tracker_creation_handler,
    tracker_logging_handler,
    tracker_viewing_handler,
    my_trackers_command
)

logger = logging.getLogger(__name__)

# Global reminder manager (will be initialized in create_bot_application)
reminder_manager = None


def init_bot_monitoring():
    """Initialize monitoring for Telegram bot"""
    if ENABLE_SENTRY:
        from src.monitoring import init_sentry
        init_sentry()
        logger.info("Sentry monitoring initialized for bot")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in bot"""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    # Capture in Sentry
    if ENABLE_SENTRY:
        from src.monitoring import capture_exception

        # Add context
        extra = {}
        if update and hasattr(update, 'effective_user') and update.effective_user:
            extra['user_id'] = str(update.effective_user.id)
        if update and hasattr(update, 'effective_message') and update.effective_message:
            if hasattr(update.effective_message, 'text'):
                extra['message_text'] = str(update.effective_message.text)[:200]  # Limit length

        capture_exception(context.error, **extra)


def should_process_message(update: Update) -> bool:
    """
    Check if message should be processed based on topic filter configuration.

    IMPORTANT: Always process DMs (direct messages) regardless of filter.
    Only apply filtering to group messages with topics.

    Supports:
    - 'all': Respond to all topics and DMs
    - 'none': Only respond to DMs
    - '10,20,30': Whitelist - only these topics (and DMs)
    - '!10,20': Blacklist - all topics except these (and DMs)

    Args:
        update: Telegram update object

    Returns:
        True if message should be processed, False to ignore
    """
    # Always process if no message (shouldn't happen, but safety check)
    if not update.message:
        return True

    # Check if this is a group/supergroup with a topic (message_thread_id present)
    chat_type = update.message.chat.type
    thread_id = update.message.message_thread_id

    # DMs (private chats) - ALWAYS process regardless of filter
    if chat_type == "private":
        return True

    # Check if blacklist mode (starts with !)
    is_blacklist = TELEGRAM_TOPIC_FILTER.startswith("!")

    # Group/supergroup without topic - process if filter is 'all', 'none', or blacklist mode
    if chat_type in ("group", "supergroup") and not thread_id:
        if TELEGRAM_TOPIC_FILTER in ("all", "none"):
            return True
        if is_blacklist:
            # Blacklist mode - process general chat (it's not blacklisted)
            return True
        # Whitelist mode - ignore general chat
        logger.info(f"Ignoring general chat message (topic whitelist: {TELEGRAM_TOPIC_FILTER})")
        return False

    # Group/supergroup with topic - apply filter
    if chat_type in ("group", "supergroup") and thread_id:
        # 'all' - respond to all topics
        if TELEGRAM_TOPIC_FILTER == "all":
            return True

        # 'none' - ignore all topics (only DMs)
        if TELEGRAM_TOPIC_FILTER == "none":
            logger.info(f"Ignoring message in topic {thread_id} (filter: none)")
            return False

        if is_blacklist:
            # Blacklist mode - parse excluded topics
            excluded_str = TELEGRAM_TOPIC_FILTER[1:]  # Remove '!' prefix
            excluded_topics = [int(t.strip()) for t in excluded_str.split(",") if t.strip()]
            if thread_id in excluded_topics:
                logger.info(f"Ignoring message in topic {thread_id} (blacklisted)")
                return False
            # Not blacklisted, process it
            return True
        else:
            # Whitelist mode - check if this topic is allowed
            allowed_topics = [int(t.strip()) for t in TELEGRAM_TOPIC_FILTER.split(",") if t.strip()]
            if thread_id in allowed_topics:
                return True
            else:
                logger.info(f"Ignoring message in topic {thread_id} (not in whitelist: {TELEGRAM_TOPIC_FILTER})")
                return False

    # Default: process the message
    return True


async def auto_save_user_info(user_id: str, user_message: str, agent_response: str) -> None:
    """
    Automatically analyze user message and save important information to memory.
    This runs after every conversation to ensure nothing is lost.

    Args:
        user_id: Telegram user ID
        user_message: What the user said
        agent_response: What the agent responded (for context)
    """
    logger.info(f"[AUTO-SAVE] Starting analysis for user {user_id}")
    logger.info(f"[AUTO-SAVE] User message: {user_message[:100]}...")

    # Debug: Write flag file to confirm function is called
    try:
        with open("/tmp/autosave_called.txt", "a") as f:
            from datetime import datetime
            f.write(f"{datetime.now()}: User {user_id} - {user_message[:50]}\n")
    except (IOError, OSError) as e:
        logger.debug(f"Failed to write debug file: {e}")

    try:
        from openai import AsyncOpenAI
        from src.config import OPENAI_API_KEY
        import json

        # Use a fast model for extraction
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        extraction_prompt = f"""Analyze this conversation and extract any personal information that should be permanently saved.

USER MESSAGE: "{user_message}"
AGENT RESPONSE: "{agent_response}"

Extract information in these categories if present:
- Medical: medications, supplements, injections, dosages, conditions, allergies
- Training: exercise routines, training days, workout details
- Sleep: sleep schedule, sleep quality, wake times
- Nutrition: meal timing, eating windows, dietary preferences
- Goals: fitness goals, target weights, timelines
- Lifestyle: work schedule, stress, energy levels
- Health Events: injuries, illnesses, symptoms
- Psychology: motivations, challenges, emotional state
- Schedule: recurring events, routines
- Data Corrections: when user corrects previously stated information or says "that's wrong, it should be X"
- Explicit Memory Requests: when user explicitly says "remember X" or "save this"

Return JSON with this structure:
{{
  "has_info": true/false,
  "extractions": [
    {{"category": "Category Name", "information": "detailed information"}},
    ...
  ]
}}

If there's no personal information worth saving permanently, return {{"has_info": false, "extractions": []}}.

IMPORTANT:
- Only extract information ABOUT THE USER (not general advice)
- Be specific and detailed
- Include context (days, times, amounts)
- ALWAYS extract corrections when user says something is wrong
- ALWAYS extract explicit memory requests when user says "remember"
- Respond in the same language as user input
- Return valid JSON only"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.3,
            max_tokens=500
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)

        logger.info(f"[AUTO-SAVE] Extraction result: has_info={result.get('has_info')}, extractions={len(result.get('extractions', []))}")

        if result.get("has_info") and result.get("extractions"):
            for extraction in result["extractions"]:
                category = extraction.get("category", "General Information")
                info = extraction.get("information", "")

                if info:
                    # Save directly to memory
                    await memory_manager.save_observation(user_id, category, info)
                    logger.info(f"[AUTO-SAVE] Saved to '{category}': {info[:50]}...")

    except Exception as e:
        logger.error(f"Auto-save failed: {e}", exc_info=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - now with onboarding"""
    user_id = str(update.effective_user.id)

    # Check topic filter
    if not should_process_message(update):
        return

    # Create user in database if doesn't exist (with pending status)
    if not await user_exists(user_id):
        await create_user(user_id)
        await memory_manager.create_user_files(user_id)

        # Auto-detect and set timezone for new users
        from src.utils.timezone_helper import suggest_timezones_for_language
        language_code = update.effective_user.language_code or "en"
        suggested_timezones = suggest_timezones_for_language(language_code)
        detected_timezone = suggested_timezones[0] if suggested_timezones else "UTC"
        await memory_manager.update_preferences(user_id, "timezone", detected_timezone)
        logger.info(f"Set timezone for new user {user_id}: {detected_timezone}")

    # Check if user is activated
    from src.db.queries import get_user_subscription_status, get_onboarding_state
    subscription = await get_user_subscription_status(user_id)

    if not subscription or subscription['status'] == 'pending':
        # User needs to activate with invite code
        pending_message = """👋 Welcome to AI Health Coach!

⚠️ **Activation Required**

To use this bot, you need an invite code.
Send your invite code to activate your account.

Example: `HEALTH2024`

Don't have a code? Contact the admin to request one."""
        await update.message.reply_text(pending_message)
        return

    # User is activated, check onboarding status
    onboarding = await get_onboarding_state(user_id)

    if not onboarding or not onboarding.get('completed_at'):
        # Start onboarding flow
        await handle_onboarding_start(update, context)
    else:
        # Already completed onboarding, show standard welcome
        welcome_message = f"""👋 Welcome back to your AI Health Coach!

✅ **Account Status:** {subscription['status'].title()} ({subscription['tier']})

Send me a food photo, ask me anything, or type /help for commands!"""

        await update.message.reply_text(welcome_message)


async def onboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /onboard command - restart or resume onboarding"""
    user_id = str(update.effective_user.id)

    # Check topic filter
    if not should_process_message(update):
        return

    # Check if user is authorized
    if not await is_authorized(user_id):
        await update.message.reply_text(
            "⚠️ Please activate your account first using /start"
        )
        return

    # Reset onboarding state to start fresh
    from src.db.queries import get_onboarding_state
    onboarding = await get_onboarding_state(user_id)

    if onboarding:
        # Clear existing onboarding state
        from src.db.queries import db
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM user_onboarding_state WHERE user_id = %s",
                    (user_id,)
                )
                await conn.commit()
        logger.info(f"Cleared onboarding state for user {user_id}")

    # Start fresh onboarding
    await update.message.reply_text(
        "🔄 **Restarting onboarding...**\n\n"
        "Let's go through the setup again!"
    )
    await handle_onboarding_start(update, context)


async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /activate command or direct code input"""
    user_id = str(update.effective_user.id)

    # Check topic filter
    if not should_process_message(update):
        return

    # Ensure user exists in database
    if not await user_exists(user_id):
        await create_user(user_id)
        await memory_manager.create_user_files(user_id)

    # Get the invite code from command args or message text
    message_text = update.message.text.strip()
    code = None

    if message_text.startswith('/activate '):
        # Command format: /activate CODE
        code = message_text.split(' ', 1)[1].strip() if len(message_text.split(' ')) > 1 else None
    else:
        # Direct code input (handled by handle_message)
        code = message_text

    if not code:
        await update.message.reply_text(
            "⚠️ Please provide an invite code.\n\n"
            "Usage: `/activate YOUR_CODE` or just send the code directly."
        )
        return

    # Validate and use the invite code
    from src.db.queries import validate_invite_code, use_invite_code

    code_details = await validate_invite_code(code)

    if not code_details:
        await update.message.reply_text(
            "❌ **Invalid invite code**\n\n"
            "This code is either:\n"
            "• Not valid\n"
            "• Already used up\n"
            "• Expired\n\n"
            "Please check your code or contact the admin for a new one."
        )
        return

    # Use the code to activate user
    success = await use_invite_code(code, user_id)

    if not success:
        await update.message.reply_text(
            "❌ **Activation failed**\n\n"
            "There was a problem activating your account. Please contact support."
        )
        return

    # Success! User is now activated
    tier = code_details['tier']
    trial_days = code_details['trial_days']

    if trial_days > 0:
        success_message = f"""✅ **Account Activated!**

🎉 Welcome to AI Health Coach!

**Your Subscription:**
• Tier: {tier.title()}
• Status: Trial
• Duration: {trial_days} days

You now have full access to all features:
🍽️ Track food with photo analysis
📊 Monitor your progress
💪 Get personalized coaching

**Get Started:**
Send me a food photo or chat with me about your health goals!

/help - See all commands
/settings - Adjust your preferences"""
    else:
        success_message = f"""✅ **Account Activated!**

🎉 Welcome to AI Health Coach!

**Your Subscription:**
• Tier: {tier.title()}
• Status: Active

You now have full access to all features:
🍽️ Track food with photo analysis
📊 Monitor your progress
💪 Get personalized coaching

**Get Started:**
Send me a food photo or chat with me about your health goals!

/help - See all commands
/settings - Adjust your preferences"""

    await update.message.reply_text(success_message)
    logger.info(f"User {user_id} successfully activated with code {code}")


async def transparency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show what the bot knows about the user"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return

    try:
        # Load user memory
        user_memory = await memory_manager.load_user_memory(user_id)

        # Build transparency report
        response_lines = ["🔍 **Transparency Report**\n"]
        response_lines.append("Here's what I know about you:\n")

        # Profile section
        response_lines.append("**📋 Profile:**")
        profile_content = user_memory.get("profile", "")
        if profile_content and len(profile_content) > 50:
            response_lines.append(f"```\n{profile_content[:500]}\n```")
        else:
            response_lines.append("_No profile data yet_")

        # Preferences section
        response_lines.append("\n**⚙️ Preferences:**")
        prefs_content = user_memory.get("preferences", "")
        if prefs_content and len(prefs_content) > 50:
            response_lines.append(f"```\n{prefs_content[:500]}\n```")
        else:
            response_lines.append("_Using default preferences_")

        # Patterns section
        response_lines.append("\n**📊 Patterns I've noticed:**")
        patterns_content = user_memory.get("patterns", "")
        if patterns_content and len(patterns_content) > 50:
            response_lines.append(f"```\n{patterns_content[:500]}\n```")
        else:
            response_lines.append("_No patterns identified yet_")

        response_lines.append(
            "\n_All your data is stored locally in markdown files. You can ask me to update or delete anything!_"
        )

        response = "\n".join(response_lines)
        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in transparency command: {e}", exc_info=True)
        await update.message.reply_text("Sorry, I had trouble loading your data.")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current user settings"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return

    try:
        # Load preferences
        user_memory = await memory_manager.load_user_memory(user_id)
        prefs_content = user_memory.get("preferences", "")

        response_lines = ["⚙️ **Your Settings**\n"]

        if prefs_content and len(prefs_content) > 50:
            response_lines.append(prefs_content)
            response_lines.append(
                "\n_You can change these by chatting naturally! For example: 'Be more brief' or 'Use a casual tone'_"
            )
        else:
            response_lines.append("_Using default settings_")
            response_lines.append(
                "\n**Available preferences:**"
            )
            response_lines.append("- Brevity: brief, medium, detailed")
            response_lines.append("- Tone: friendly, formal, casual")
            response_lines.append("- Coaching style: supportive, analytical, tough_love")
            response_lines.append(
                "\nJust tell me what you prefer and I'll update it!"
            )

        response = "\n".join(response_lines)
        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in settings command: {e}", exc_info=True)
        await update.message.reply_text("Sorry, I had trouble loading your settings.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return

    help_text = """🤖 **AI Health Coach Help**

**What I can do:**
- 📸 Analyze food photos for calories & macros
- 💬 Chat naturally about your health goals
- 📊 Track custom metrics (period, energy, mood, etc.)
- 🎯 Personalize my responses to your preferences
- 📝 Remember your goals and patterns
- 🔍 Analyze patterns in your tracked data

**Core Commands:**
/start - Reset and start over
/transparency - See what data I have about you
/settings - View and change your preferences
/clear - Clear conversation history (fresh start)
/help - Show this help message

**Custom Tracking Commands:**
/create_tracker - Create a new health tracker
/log_tracker - Log an entry to a tracker
/view_tracker - View your tracked data
/my_trackers - List all your trackers

**Tips:**
- Send a food photo to log meals automatically
- Create custom trackers for anything: period cycles, symptoms, energy, medications
- Ask me about your data: "How has my energy been this week?"
- Change preferences: "Be more brief" or "Use casual tone"

**Privacy:**
All your data is stored securely. You have full control and can delete anything anytime."""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear conversation history"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return

    try:
        await clear_conversation_history(user_id)
        await update.message.reply_text(
            "🧹 Conversation history cleared! Starting fresh.\n\n"
            "I'll still remember your profile, preferences, and data - "
            "just not our recent chat messages."
        )
        logger.info(f"Cleared conversation history for {user_id}")
    except Exception as e:
        logger.error(f"Error clearing history: {e}", exc_info=True)
        await update.message.reply_text("Sorry, I had trouble clearing the history.")


async def approve_tool_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve a pending dynamic tool creation"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return

    # Check if user is admin (first user in allowed list)
    from src.config import ALLOWED_TELEGRAM_IDS
    if not ALLOWED_TELEGRAM_IDS or user_id != ALLOWED_TELEGRAM_IDS[0]:
        await update.message.reply_text("⛔ Only admins can approve tools")
        return

    # Get approval_id from command args
    if not context.args or len(context.args) == 0:
        await update.message.reply_text("Usage: /approve_tool <approval_id>")
        return

    approval_id = context.args[0]

    try:
        await approve_tool(approval_id, user_id)

        # Reload tools to make newly approved tool available
        await tool_manager.load_all_tools()

        await update.message.reply_text(
            f"✅ Tool approved and loaded\n\n"
            f"Approval ID: {approval_id}\n"
            f"The tool is now available for use."
        )
        logger.info(f"Admin {user_id} approved tool {approval_id}")

    except Exception as e:
        logger.error(f"Error approving tool: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {str(e)}")


async def reject_tool_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reject a pending dynamic tool creation"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return

    # Check if user is admin (first user in allowed list)
    from src.config import ALLOWED_TELEGRAM_IDS
    if not ALLOWED_TELEGRAM_IDS or user_id != ALLOWED_TELEGRAM_IDS[0]:
        await update.message.reply_text("⛔ Only admins can reject tools")
        return

    # Get approval_id from command args
    if not context.args or len(context.args) == 0:
        await update.message.reply_text("Usage: /reject_tool <approval_id>")
        return

    approval_id = context.args[0]

    try:
        await reject_tool(approval_id, user_id)

        await update.message.reply_text(
            f"❌ Tool rejected\n\n"
            f"Approval ID: {approval_id}\n"
            f"The tool will not be created."
        )
        logger.info(f"Admin {user_id} rejected tool {approval_id}")

    except Exception as e:
        logger.error(f"Error rejecting tool: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {str(e)}")


async def pending_approvals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show pending tool approval requests"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return

    # Check if user is admin (first user in allowed list)
    from src.config import ALLOWED_TELEGRAM_IDS
    if not ALLOWED_TELEGRAM_IDS or user_id != ALLOWED_TELEGRAM_IDS[0]:
        await update.message.reply_text("⛔ Only admins can view pending approvals")
        return

    try:
        pending = await get_pending_approvals()

        if not pending:
            await update.message.reply_text("✅ No pending approvals")
            return

        response_lines = ["📋 **Pending Tool Approvals**\n"]

        for i, approval in enumerate(pending, 1):
            response_lines.append(f"**{i}. {approval['tool_name']}**")
            response_lines.append(f"   Type: {approval['tool_type']}")
            response_lines.append(f"   Description: {approval['description']}")
            response_lines.append(f"   Requested by: {approval['requested_by']}")
            response_lines.append(f"   Approval ID: `{approval['approval_id']}`")
            response_lines.append(f"   Commands:")
            response_lines.append(f"   - `/approve_tool {approval['approval_id']}`")
            response_lines.append(f"   - `/reject_tool {approval['approval_id']}`")
            response_lines.append("")

        response = "\n".join(response_lines)
        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {str(e)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages - main entry point for message processing.

    This function orchestrates message handling by:
    1. Validating input and authorization
    2. Extracting user context
    3. Routing to appropriate handler

    The actual processing is delegated to specialized handlers.
    """
    from src.handlers.message_helpers import validate_message_input, extract_message_context
    from src.handlers.message_routing import route_message

    user_id = str(update.effective_user.id)
    text = update.message.text

    logger.info(f"Message from {user_id}: {text[:50]}...")

    # Step 1: Validate input
    validation = await validate_message_input(update, user_id)
    if not validation.is_valid:
        logger.debug(f"Message ignored: {validation.reason}")
        return

    # Step 2: Extract context
    msg_context = await extract_message_context(user_id, context)

    # Step 3: Route to handler
    await route_message(update, context, msg_context, text)


async def _validate_photo_input(update: Update) -> tuple[bool, str]:
    """
    Validate photo input (authorization and topic filter).

    Returns:
        tuple[bool, str]: (is_valid, user_id)
    """
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return False, user_id

    # Check topic filter
    if not should_process_message(update):
        return False, user_id

    logger.info(f"Photo received from {user_id}")
    return True, user_id


async def _download_and_save_photo(update: Update, user_id: str) -> tuple[Path, str | None]:
    """
    Download photo and save to user's directory.

    Args:
        update: Telegram update object
        user_id: User ID

    Returns:
        tuple[Path, str | None]: (photo_path, caption)
    """
    # Send processing indicator
    await update.message.reply_text("📸 Analyzing your food photo...")
    await update.message.chat.send_action("typing")

    # Download photo
    photo = update.message.photo[-1]  # Get highest resolution
    file = await photo.get_file()

    # Save photo to user's data directory
    photos_dir = DATA_PATH / user_id / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_path = photos_dir / f"{timestamp}.jpg"
    await file.download_to_drive(photo_path)

    logger.info(f"Photo saved to {photo_path}")

    # Get caption if provided
    caption = update.message.caption
    if caption:
        logger.info(f"Photo caption received: {caption}")
    else:
        logger.info("No caption provided with photo")

    return photo_path, caption


async def _gather_context_for_analysis(user_id: str, caption: str | None) -> tuple[str, str, str, str]:
    """
    Gather all context needed for photo analysis.

    Args:
        user_id: User ID
        caption: Photo caption (optional)

    Returns:
        tuple[str, str, str, str]: (visual_patterns, mem0_context, food_history_context, habit_context)
    """
    # Load user's visual patterns for better recognition
    user_memory = await memory_manager.load_user_memory(user_id)
    visual_patterns = user_memory.get("visual_patterns", "")

    # Task 4.1: Add Mem0 semantic search for relevant food context
    from src.memory.mem0_manager import mem0_manager
    mem0_context = ""
    try:
        food_memories = mem0_manager.search(
            user_id,
            query=f"food photo {caption if caption else 'meal'}",
            limit=5
        )
        # Handle Mem0 returning dict with 'results' key or direct list
        if isinstance(food_memories, dict):
            food_memories = food_memories.get('results', [])

        if food_memories:
            mem0_context = "\n\n**Relevant context from past conversations:**\n"
            for mem in food_memories:
                if isinstance(mem, dict):
                    memory_text = mem.get('memory', mem.get('text', str(mem)))
                elif isinstance(mem, str):
                    memory_text = mem
                else:
                    memory_text = str(mem)
                mem0_context += f"- {memory_text}\n"
            logger.info(f"[PHOTO] Added {len(food_memories)} Mem0 memories to context")
    except Exception as e:
        logger.warning(f"[PHOTO] Failed to load Mem0 context: {e}")

    # Task 4.2: Include recent food history (last 7 days)
    from datetime import timedelta
    from src.db.queries import get_food_entries_by_date
    food_history_context = ""
    try:
        recent_foods = await get_food_entries_by_date(
            user_id,
            start_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d')
        )

        if recent_foods:
            # Summarize recent patterns
            food_counts = {}
            for entry in recent_foods:
                foods_data = entry.get('foods', [])
                if isinstance(foods_data, str):
                    import json
                    foods_data = json.loads(foods_data)

                for food in foods_data:
                    food_name = food.get('food_name', food.get('name', 'unknown'))
                    food_counts[food_name] = food_counts.get(food_name, 0) + 1

            # Top 5 most logged foods
            top_foods = sorted(food_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            if top_foods:
                food_history_context = "\n\n**Your recent eating patterns (last 7 days):**\n"
                for food_name, count in top_foods:
                    food_history_context += f"- {food_name} (logged {count}x this week)\n"
                logger.info(f"[PHOTO] Added food history context with {len(top_foods)} items")
    except Exception as e:
        logger.warning(f"[PHOTO] Failed to load food history: {e}")

    # Task 4.3: Apply food habits
    from src.memory.habit_extractor import habit_extractor
    habit_context = ""
    try:
        habits = await habit_extractor.get_user_habits(
            user_id,
            habit_type="food_prep",
            min_confidence=0.6
        )

        if habits:
            habit_context = "\n\n**User's food preparation habits:**\n"
            for habit in habits:
                habit_data = habit['habit_data']
                food = habit_data.get('food', habit['habit_key'])
                ratio = habit_data.get('ratio', '')
                liquid = habit_data.get('liquid', '').replace('_', ' ')

                habit_context += f"- {food}: Always prepared with {liquid}"
                if ratio:
                    habit_context += f" ({ratio} ratio)"
                habit_context += f" (confidence: {habit['confidence']:.0%})\n"
            logger.info(f"[PHOTO] Added {len(habits)} food habits to context")
    except Exception as e:
        logger.warning(f"[PHOTO] Failed to load habits: {e}")

    return visual_patterns, mem0_context, food_history_context, habit_context


async def _analyze_and_validate_nutrition(
    photo_path: Path,
    caption: str | None,
    user_id: str,
    visual_patterns: str,
    mem0_context: str,
    food_history_context: str,
    habit_context: str
):
    """
    Analyze photo with vision AI and validate nutrition data.

    Returns:
        tuple: (validated_analysis, validation_warnings, verified_foods)
    """
    # Analyze with vision AI (with all enhanced context)
    analysis = await analyze_food_photo(
        str(photo_path),
        caption=caption,
        user_id=user_id,
        visual_patterns=visual_patterns,
        semantic_context=mem0_context,
        food_history=food_history_context,
        food_habits=habit_context
    )

    # Verify nutrition data with USDA database
    from src.utils.nutrition_search import verify_food_items
    verified_foods = await verify_food_items(analysis.foods)

    # Phase 1: Multi-Agent Validation
    from src.agent.nutrition_validator import get_validator
    validator = get_validator()

    validated_analysis, validation_warnings = await validator.validate(
        vision_result=analysis,
        photo_path=str(photo_path),
        caption=caption,
        visual_patterns=visual_patterns,
        usda_verified_items=verified_foods,
        enable_cross_validation=True  # Enable multi-model cross-checking
    )

    # Use validated results
    verified_foods = validated_analysis.foods

    return validated_analysis, validation_warnings, verified_foods


def _build_response_message(
    caption: str | None,
    verified_foods: list,
    validated_analysis,
    validation_warnings: list
) -> tuple[str, dict]:
    """
    Build the response message with food analysis results.

    Args:
        caption: Photo caption
        verified_foods: List of verified food items
        validated_analysis: Validated analysis result
        validation_warnings: List of validation warnings

    Returns:
        tuple[str, dict]: (response_message, totals_dict)
    """
    response_lines = ["🍽️ **Food Analysis:**"]
    if caption:
        response_lines.append(f"_Based on your description: \"{caption}\"_\n")
    else:
        response_lines.append("")

    for food in verified_foods:
        # Add verification badge
        badge = ""
        if food.verification_source == "usda":
            badge = " ✓"  # Verified badge
        elif food.verification_source == "ai_estimate":
            badge = " ~"  # Estimate badge

        response_lines.append(f"• {food.name}{badge} ({food.quantity})")

        # Build macro line
        macro_line = f"  └ {food.calories} cal | P: {food.macros.protein}g | C: {food.macros.carbs}g | F: {food.macros.fat}g"

        # Add fiber and sodium if available
        if food.macros.micronutrients:
            micros = food.macros.micronutrients
            if micros.fiber is not None:
                macro_line += f" | Fiber: {micros.fiber}g"
            if micros.sodium is not None:
                macro_line += f" | Sodium: {micros.sodium}mg"

        response_lines.append(macro_line)

    # Calculate totals from verified data
    total_calories = sum(f.calories for f in verified_foods)
    total_protein = sum(f.macros.protein for f in verified_foods)
    total_carbs = sum(f.macros.carbs for f in verified_foods)
    total_fat = sum(f.macros.fat for f in verified_foods)

    response_lines.append(f"\n**Total:** {total_calories} cal | P: {total_protein}g | C: {total_carbs}g | F: {total_fat}g")
    response_lines.append(f"\n_Confidence: {validated_analysis.confidence}_")

    # Add validation warnings if any
    if validation_warnings:
        response_lines.append("\n**⚠️ Validation Alerts:**")
        for warning in validation_warnings:
            response_lines.append(f"{warning}")

    # Add clarifying questions if any
    if validated_analysis.clarifying_questions:
        response_lines.append("\n**Questions to improve accuracy:**")
        for q in validated_analysis.clarifying_questions:
            response_lines.append(f"• {q}")

    totals = {
        "calories": total_calories,
        "protein": total_protein,
        "carbs": total_carbs,
        "fat": total_fat
    }

    return "\n".join(response_lines), totals


async def _save_food_entry_with_habits(
    user_id: str,
    photo_path: Path,
    verified_foods: list,
    totals: dict,
    validated_analysis,
    caption: str | None
) -> FoodEntry:
    """
    Save food entry to database and trigger habit detection.

    Args:
        user_id: User ID
        photo_path: Path to saved photo
        verified_foods: List of verified food items
        totals: Dictionary with total macros
        validated_analysis: Validated analysis result
        caption: Photo caption

    Returns:
        FoodEntry: Saved food entry object
    """
    from src.models.food import FoodMacros

    total_macros = FoodMacros(
        protein=totals["protein"],
        carbs=totals["carbs"],
        fat=totals["fat"]
    )

    # Use extracted timestamp from caption if available, otherwise current time
    entry_timestamp = validated_analysis.timestamp if validated_analysis.timestamp else datetime.now()

    entry = FoodEntry(
        user_id=user_id,
        timestamp=entry_timestamp,
        photo_path=str(photo_path),
        foods=verified_foods,  # Use verified data instead of AI estimates
        total_calories=totals["calories"],
        total_macros=total_macros,
        meal_type=None,  # Can be inferred from time later
        notes=caption or None
    )

    await save_food_entry(entry)
    logger.info(f"Saved food entry for {user_id}")

    # Trigger habit detection for food patterns
    from src.memory.habit_extractor import habit_extractor
    try:
        for food_item in entry.foods:
            parsed_components = {
                "food": food_item.food_name,
                "quantity": f"{food_item.quantity} {food_item.unit}",
                "preparation": food_item.food_name  # Could be enhanced
            }
            await habit_extractor.detect_food_prep_habit(
                user_id,
                food_item.food_name,
                parsed_components
            )
    except Exception as e:
        logger.warning(f"[HABITS] Failed to detect habits: {e}")
        # Continue - habit detection shouldn't block food logging

    return entry


async def _process_gamification(user_id: str, entry: FoodEntry) -> str:
    """
    Process gamification (XP, streaks, achievements) and log feature usage.

    Args:
        user_id: User ID
        entry: Food entry object

    Returns:
        str: Gamification message to append to response
    """
    # Process gamification (XP, streaks, achievements)
    meal_type = entry.meal_type or "snack"  # Default if not set
    gamification_result = await handle_food_entry_gamification(
        user_id=user_id,
        food_entry_id=entry.id,
        logged_at=entry.timestamp,
        meal_type=meal_type
    )

    # Log feature usage
    from src.db.queries import log_feature_usage
    await log_feature_usage(user_id, "food_tracking")

    # Return gamification message if available
    gamification_msg = gamification_result.get('message', '')
    if gamification_msg:
        return f"\n🎯 **PROGRESS**\n{gamification_msg}"
    return ""


async def _send_response_and_log(
    update: Update,
    user_id: str,
    response_message: str,
    verified_foods: list,
    totals: dict,
    validated_analysis,
    validation_warnings: list
) -> None:
    """
    Send response to user and save to conversation history.

    Args:
        update: Telegram update object
        user_id: User ID
        response_message: Formatted response message
        verified_foods: List of verified food items
        totals: Dictionary with total macros
        validated_analysis: Validated analysis result
        validation_warnings: List of validation warnings
    """
    # Send response
    await update.message.reply_text(response_message, parse_mode="Markdown")

    # Save to conversation history database with metadata
    photo_description = f"User sent a food photo. Analysis: {', '.join([f.name for f in verified_foods])}"
    photo_metadata = {
        "foods": [{"name": f.name, "quantity": f.quantity, "verification_source": f.verification_source} for f in verified_foods],
        "total_calories": totals["calories"],
        "confidence": validated_analysis.confidence,
        "validation_warnings": validation_warnings if validation_warnings else None
    }

    await save_conversation_message(
        user_id, "user", photo_description, message_type="photo", metadata=photo_metadata
    )
    await save_conversation_message(
        user_id, "assistant", response_message, message_type="photo_response"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle food photos - orchestrates the complete photo analysis workflow.

    This function follows Single Responsibility Principle by delegating to specialized helpers:
    - Validation: _validate_photo_input()
    - Download: _download_and_save_photo()
    - Context: _gather_context_for_analysis()
    - Analysis: _analyze_and_validate_nutrition()
    - Response: _build_response_message()
    - Storage: _save_food_entry_with_habits()
    - Gamification: _process_gamification()
    - Notification: _send_response_and_log()
    """
    # Step 1: Validate input
    is_valid, user_id = await _validate_photo_input(update)
    if not is_valid:
        return

    try:
        # Step 2: Download and save photo
        photo_path, caption = await _download_and_save_photo(update, user_id)

        # Step 3: Gather context for analysis
        visual_patterns, mem0_context, food_history, habit_context = await _gather_context_for_analysis(
            user_id, caption
        )

        # Step 4: Analyze and validate nutrition
        validated_analysis, validation_warnings, verified_foods = await _analyze_and_validate_nutrition(
            photo_path, caption, user_id, visual_patterns, mem0_context, food_history, habit_context
        )

        # Step 5: Build response message
        response_message, totals = _build_response_message(
            caption, verified_foods, validated_analysis, validation_warnings
        )

        # Step 6: Save food entry with habit detection
        entry = await _save_food_entry_with_habits(
            user_id, photo_path, verified_foods, totals, validated_analysis, caption
        )

        # Step 7: Process gamification
        gamification_msg = await _process_gamification(user_id, entry)
        if gamification_msg:
            response_message += gamification_msg

        # Step 8: Send response and log to conversation history
        await _send_response_and_log(
            update, user_id, response_message, verified_foods, totals, validated_analysis, validation_warnings
        )

    except Exception as e:
        logger.error(f"Error in handle_photo: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I had trouble analyzing this photo. Please try again or describe what you ate!"
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice notes by transcribing and processing as text"""
    user_id = str(update.effective_user.id)

    # Check topic filter
    if not should_process_message(update):
        return

    # Check if user is pending activation
    from src.db.queries import get_user_subscription_status
    subscription = await get_user_subscription_status(user_id)

    if subscription and subscription['status'] == 'pending':
        await update.message.reply_text(
            "⚠️ **Please activate your account first**\n\n"
            "Send your invite code to start using the bot."
        )
        return

    # Check authorization
    if not await is_authorized(user_id):
        return

    logger.info(f"Voice note received from {user_id}")

    try:
        # Send processing indicator
        await update.message.reply_text("🎤 Transcribing your voice note...")

        from src.utils.typing_indicator import PersistentTypingIndicator

        async with PersistentTypingIndicator(update.message.chat):
            # Download voice file
            voice = update.message.voice
            file = await voice.get_file()

            # Save voice to temp directory
            voice_dir = DATA_PATH / user_id / "voice"
            voice_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            voice_path = voice_dir / f"{timestamp}.ogg"
            await file.download_to_drive(voice_path)

            logger.info(f"Voice note saved to {voice_path}")

            # Transcribe voice to text
            transcribed_text = await transcribe_voice(str(voice_path))
            logger.info(f"Transcribed: {transcribed_text[:100]}...")

            # Log feature usage
            from src.db.queries import log_feature_usage
            await log_feature_usage(user_id, "voice_notes")

            # Load conversation history (auto-filters unhelpful "I don't know" responses)
            message_history = await get_conversation_history(user_id, limit=20)

            # Get AI response using the transcribed text
            response = await get_agent_response(
                user_id, transcribed_text, memory_manager, reminder_manager, message_history,
                bot_application=context.application
            )

        # Save voice message and response to database
        voice_metadata = {
            "transcription": transcribed_text,
            "duration_seconds": voice.duration
        }
        await save_conversation_message(
            user_id, "user", transcribed_text, message_type="voice", metadata=voice_metadata
        )
        await save_conversation_message(user_id, "assistant", response, message_type="text")

        # Move auto-save to background task (don't block response)
        async def background_voice_memory_tasks():
            """Run memory operations in background after response is sent"""
            await auto_save_user_info(user_id, transcribed_text, response)

        # Schedule background task (fire and forget)
        import asyncio
        asyncio.create_task(background_voice_memory_tasks())

        # Send transcription and response
        await update.message.reply_text(
            f"📝 _You said: \"{transcribed_text}\"_\n\n{response}",
            parse_mode="Markdown"
        )
        logger.info(f"Sent voice response to {user_id}")

    except Exception as e:
        logger.error(f"Error in handle_voice: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I had trouble processing your voice note. Please try again or send a text message!"
        )


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle location sharing to auto-detect timezone"""
    user_id = str(update.effective_user.id)

    try:
        location = update.message.location
        latitude = location.latitude
        longitude = location.longitude

        logger.info(f"Received location from {user_id}: ({latitude}, {longitude})")

        # Detect timezone from coordinates
        from src.utils.timezone_helper import get_timezone_from_coordinates, update_timezone_in_profile

        detected_timezone = get_timezone_from_coordinates(latitude, longitude)

        # Update user's profile
        success = update_timezone_in_profile(user_id, detected_timezone)

        if success:
            await update.message.reply_text(
                f"✅ Thanks! I've detected your timezone as **{detected_timezone}**.\n\n"
                f"I'll now use this for all time-based responses. You can update it anytime by sharing your location again!",
                parse_mode="Markdown"
            )
            logger.info(f"Updated timezone for {user_id} to {detected_timezone}")
        else:
            await update.message.reply_text(
                "❌ Sorry, I had trouble updating your timezone. Please try again!"
            )

    except Exception as e:
        logger.error(f"Error in handle_location: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I had trouble processing your location. Please try again!"
        )


def create_bot_application() -> Application:
    """Create and configure the bot application"""
    global reminder_manager

    # Initialize monitoring
    init_bot_monitoring()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Initialize reminder manager
    reminder_manager = ReminderManager(app)
    logger.info("ReminderManager initialized")

    # Store reminder_manager in bot_data for access from handlers
    app.bot_data['reminder_manager'] = reminder_manager

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("onboard", onboard))
    app.add_handler(CommandHandler("activate", activate))
    app.add_handler(CommandHandler("transparency", transparency))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("approve_tool", approve_tool_command))
    app.add_handler(CommandHandler("reject_tool", reject_tool_command))
    app.add_handler(CommandHandler("pending_approvals", pending_approvals_command))

    # Add conversation handlers (MUST be before message handlers)
    app.add_handler(sleep_quiz_handler)
    logger.info("Sleep quiz handler registered")

    app.add_handler(sleep_settings_handler)
    logger.info("Sleep settings handler registered")

    # Epic 006: Custom tracker handlers
    app.add_handler(tracker_creation_handler)
    app.add_handler(tracker_logging_handler)
    app.add_handler(tracker_viewing_handler)
    app.add_handler(CommandHandler("my_trackers", my_trackers_command))
    logger.info("Custom tracking handlers registered (create, log, view, list)")

    # Add callback query handlers
    app.add_handler(reminder_completion_handler)
    app.add_handler(reminder_skip_handler)
    app.add_handler(skip_reason_handler)
    app.add_handler(reminder_snooze_handler)
    logger.info("Reminder handlers registered (completion, skip, skip_reason, snooze)")

    # Add note handlers
    app.add_handler(add_note_handler)
    app.add_handler(note_template_handler)
    app.add_handler(note_custom_handler)
    app.add_handler(note_skip_handler)
    logger.info("Note handlers registered (add_note, template, custom, skip)")

    # Add onboarding callback handlers
    app.add_handler(onboarding_path_selection_handler)
    app.add_handler(onboarding_language_selection_handler)
    app.add_handler(onboarding_focus_selection_handler)
    logger.info("Onboarding callback handlers registered (path_selection, language, focus)")

    # Add message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # Add error handler
    app.add_error_handler(error_handler)
    logger.info("Error handler registered")

    logger.info("Bot application created")
    return app
