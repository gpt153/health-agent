"""Telegram bot setup and handlers"""
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import telegram.error
from src.config import TELEGRAM_BOT_TOKEN, DATA_PATH, TELEGRAM_TOPIC_FILTER
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
from src.handlers.onboarding import handle_onboarding_start, handle_onboarding_message
from src.handlers.sleep_quiz import sleep_quiz_handler
from src.handlers.reminders import reminder_completion_handler

logger = logging.getLogger(__name__)

# Global reminder manager (will be initialized in create_bot_application)
reminder_manager = None


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
    except:
        pass

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
- 📊 Track custom metrics (sleep, workouts, etc.)
- 🎯 Personalize my responses to your preferences
- 📝 Remember your goals and patterns

**Commands:**
/start - Reset and start over
/transparency - See what data I have about you
/settings - View and change your preferences
/clear - Clear conversation history (fresh start)
/help - Show this help message

**Tips:**
- Send a food photo to log meals automatically
- Ask me to track anything: "Track my sleep quality"
- Change preferences: "Be more brief" or "Use casual tone"
- Ask questions: "What did I eat yesterday?"

**Privacy:**
All your data is stored locally in markdown files. You have full control and can delete anything anytime."""

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
    """Handle text messages"""
    user_id = str(update.effective_user.id)

    # Check topic filter
    if not should_process_message(update):
        return

    text = update.message.text
    logger.info(f"Message from {user_id}: {text[:50]}...")

    # Check if user is pending activation
    from src.db.queries import get_user_subscription_status, get_onboarding_state
    subscription = await get_user_subscription_status(user_id)

    if subscription and subscription['status'] == 'pending':
        # User is pending, check if message looks like an invite code
        # Invite codes are typically uppercase alphanumeric, 6-20 chars
        message_clean = text.strip().upper()
        if len(message_clean) >= 4 and len(message_clean) <= 50 and message_clean.replace(' ', '').isalnum():
            # Looks like a code, try to activate
            await activate(update, context)
            return
        else:
            # Not a code, remind user to activate
            await update.message.reply_text(
                "⚠️ **Please activate your account first**\n\n"
                "Send your invite code to start using the bot.\n\n"
                "Example: `HEALTH2024`\n\n"
                "Don't have a code? Use /start to get more information."
            )
            return

    # Check if user is in onboarding
    # DISABLED: Onboarding check commented out for debugging
    # onboarding = await get_onboarding_state(user_id)
    # if onboarding and not onboarding.get('completed_at'):
    #     # Route to onboarding handler
    #     await handle_onboarding_message(update, context)
    #     return

    # Check authorization (for active users)
    if not await is_authorized(user_id):
        return

    # DISABLED: Timezone check commented out for debugging
    # Check if user has timezone set (first-time setup)
    # from src.utils.timezone_helper import get_timezone_from_profile, suggest_timezones_for_language, update_timezone_in_profile, normalize_timezone
    #
    # user_timezone = get_timezone_from_profile(user_id)
    # if not user_timezone:
    #     # Check if message looks like a timezone string (e.g., "America/New_York")
    #     if '/' in text and len(text.split()) == 1:
    #         # Normalize timezone (handles case-insensitive input)
    #         normalized_tz = normalize_timezone(text.strip())
    #         if normalized_tz:
    #             # Valid timezone - set it
    #             if update_timezone_in_profile(user_id, normalized_tz):
    #                 await update.message.reply_text(
    #                     f"✅ Great! Your timezone is now set to **{normalized_tz}**.\n\n"
    #                     f"You can start using the bot normally now!",
    #                     parse_mode="Markdown"
    #                 )
    #                 return
    #         else:
    #             # Invalid timezone - show error
    #             await update.message.reply_text(
    #                 f"❌ Invalid timezone. Try \"America/New_York\" or share your location.",
    #                 parse_mode="Markdown"
    #             )
    #             return
    #
    #     # New user - ask for timezone with smart suggestions
    #     language_code = update.effective_user.language_code or 'en'
    #     suggested_timezones = suggest_timezones_for_language(language_code)
    #
    #     timezone_list = "\n".join([f"• {tz}" for tz in suggested_timezones[:3]])
    #
    #     await update.message.reply_text(
    #         f"👋 **Welcome! Let's set up your timezone first.**\n\n"
    #         f"Based on your language ({language_code}), I suggest:\n{timezone_list}\n\n"
    #         f"**Two ways to set your timezone:**\n"
    #         f"1️⃣ Share your location (📎 → Location) - I'll detect it automatically\n"
    #         f"2️⃣ Reply with your timezone (e.g., \"Europe/Stockholm\", \"America/New_York\")\n\n"
    #         f"This helps me give you accurate time-based responses!",
    #         parse_mode="Markdown"
    #     )
    #     return

    # Get AI response using PydanticAI agent
    try:
        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Load conversation history from database (auto-filters unhelpful "I don't know" responses)
        message_history = await get_conversation_history(user_id, limit=20)

        # Get agent response with conversation history
        # Pass context.application for approval notifications
        response = await get_agent_response(
            user_id, text, memory_manager, reminder_manager, message_history,
            bot_application=context.application
        )

        # Save user message and assistant response to database
        await save_conversation_message(user_id, "user", text, message_type="text")
        await save_conversation_message(user_id, "assistant", response, message_type="text")

        # Add to Mem0 for semantic memory and automatic fact extraction
        mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
        mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})

        # Auto-save: Extract and save any personal information from the conversation
        logger.info(f"[DEBUG-FLOW] BEFORE auto_save_user_info for user {user_id}")
        logger.info(f"[DEBUG-FLOW] User message: {text[:100]}")
        logger.info(f"[DEBUG-FLOW] Agent response: {response[:100]}")
        await auto_save_user_info(user_id, text, response)
        logger.info(f"[DEBUG-FLOW] AFTER auto_save_user_info completed successfully")

        # Send response - try with Markdown first, fallback to plain text if parsing fails
        try:
            await update.message.reply_text(response, parse_mode="Markdown")
            logger.info(f"Sent AI response to {user_id}")
        except telegram.error.BadRequest as e:
            if "can't parse entities" in str(e).lower():
                # Markdown parsing failed, send as plain text
                logger.warning(f"Markdown parse error, sending as plain text: {e}")
                await update.message.reply_text(response)
            else:
                raise

    except Exception as e:
        logger.error(f"Error in handle_message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error. Please try again!"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle food photos"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return

    # Check topic filter
    if not should_process_message(update):
        return

    logger.info(f"Photo received from {user_id}")

    try:
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

        # Load user's visual patterns for better recognition
        user_memory = await memory_manager.load_user_memory(user_id)
        visual_patterns = user_memory.get("visual_patterns", "")

        # Analyze with vision AI (with caption and visual patterns)
        analysis = await analyze_food_photo(
            str(photo_path),
            caption=caption,
            user_id=user_id,
            visual_patterns=visual_patterns
        )

        # Build response message
        response_lines = ["🍽️ **Food Analysis:**"]
        if caption:
            response_lines.append(f"_Based on your description: \"{caption}\"_\n")
        else:
            response_lines.append("")

        for food in analysis.foods:
            response_lines.append(f"• {food.name} ({food.quantity})")
            response_lines.append(
                f"  └ {food.calories} cal | P: {food.macros.protein}g | C: {food.macros.carbs}g | F: {food.macros.fat}g"
            )

        # Calculate totals
        total_calories = sum(f.calories for f in analysis.foods)
        total_protein = sum(f.macros.protein for f in analysis.foods)
        total_carbs = sum(f.macros.carbs for f in analysis.foods)
        total_fat = sum(f.macros.fat for f in analysis.foods)

        response_lines.append(f"\n**Total:** {total_calories} cal | P: {total_protein}g | C: {total_carbs}g | F: {total_fat}g")
        response_lines.append(f"\n_Confidence: {analysis.confidence}_")

        # Add clarifying questions if any
        if analysis.clarifying_questions:
            response_lines.append("\n**Questions to improve accuracy:**")
            for q in analysis.clarifying_questions:
                response_lines.append(f"• {q}")

        # Save to database
        from src.models.food import FoodMacros

        total_macros = FoodMacros(
            protein=total_protein,
            carbs=total_carbs,
            fat=total_fat
        )

        # Use extracted timestamp from caption if available, otherwise current time
        entry_timestamp = analysis.timestamp if analysis.timestamp else datetime.now()

        entry = FoodEntry(
            user_id=user_id,
            timestamp=entry_timestamp,
            photo_path=str(photo_path),
            foods=analysis.foods,
            total_calories=total_calories,
            total_macros=total_macros,
            meal_type=None,  # Can be inferred from time later
            notes=update.message.caption or None
        )

        await save_food_entry(entry)
        logger.info(f"Saved food entry for {user_id}")

        # Log feature usage
        from src.db.queries import log_feature_usage
        await log_feature_usage(user_id, "food_tracking")

        # Send response
        response = "\n".join(response_lines)
        await update.message.reply_text(response, parse_mode="Markdown")

        # Save to conversation history database with metadata
        photo_description = f"User sent a food photo. Analysis: {', '.join([f.name for f in analysis.foods])}"
        photo_metadata = {
            "foods": [{"name": f.name, "quantity": f.quantity} for f in analysis.foods],
            "total_calories": total_calories,
            "confidence": analysis.confidence
        }

        await save_conversation_message(
            user_id, "user", photo_description, message_type="photo", metadata=photo_metadata
        )
        await save_conversation_message(
            user_id, "assistant", response, message_type="photo_response"
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
        await update.message.chat.send_action("typing")

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

        # Auto-save: Extract and save any personal information
        await auto_save_user_info(user_id, transcribed_text, response)

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

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Initialize reminder manager
    reminder_manager = ReminderManager(app)
    logger.info("ReminderManager initialized")

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
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

    # Add callback query handlers
    app.add_handler(reminder_completion_handler)
    logger.info("Reminder completion handler registered")

    # Add message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    logger.info("Bot application created")
    return app
