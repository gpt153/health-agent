"""Telegram bot setup and handlers"""
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from src.config import TELEGRAM_BOT_TOKEN, DATA_PATH
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
)
from src.memory.file_manager import memory_manager
from src.agent import get_agent_response
from src.agent.dynamic_tools import tool_manager
from src.utils.vision import analyze_food_photo
from src.models.food import FoodEntry
from src.scheduler.reminder_manager import ReminderManager
from src.utils.timezone_helper import detect_timezone_from_telegram

logger = logging.getLogger(__name__)

# Global reminder manager (will be initialized in create_bot_application)
reminder_manager = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not is_authorized(user_id):
        logger.warning(f"Unauthorized access attempt from {user_id}")
        return

    # Create user in database
    if not await user_exists(user_id):
        await create_user(user_id)
        await memory_manager.create_user_files(user_id)

        # Auto-detect and set timezone for new users
        user_data = {
            "language_code": update.effective_user.language_code or "en"
        }
        detected_timezone = detect_timezone_from_telegram(user_data)
        await memory_manager.update_preferences(user_id, "timezone", detected_timezone)
        logger.info(f"Set timezone for new user {user_id}: {detected_timezone}")

    welcome_message = """👋 Welcome to your AI Health Coach!

I can help you:
🍽️ Track food by sending me photos
📊 Monitor your progress
💪 Stay motivated with personalized coaching

**Commands:**
/transparency - See what I know about you
/settings - View your preferences
/help - Get help

Send me a food photo to get started, or just chat with me about your health goals!"""

    await update.message.reply_text(welcome_message)


async def transparency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show what the bot knows about the user"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not is_authorized(user_id):
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
    if not is_authorized(user_id):
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
    if not is_authorized(user_id):
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
    if not is_authorized(user_id):
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
    if not is_authorized(user_id):
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
    if not is_authorized(user_id):
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not is_authorized(user_id):
        return

    text = update.message.text
    logger.info(f"Message from {user_id}: {text[:50]}...")

    # Get AI response using PydanticAI agent
    try:
        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Load conversation history from database (last 20 messages = 10 turns)
        message_history = await get_conversation_history(user_id, limit=20)

        # Get agent response with conversation history
        response = await get_agent_response(
            user_id, text, memory_manager, reminder_manager, message_history
        )

        # Save user message and assistant response to database
        await save_conversation_message(user_id, "user", text, message_type="text")
        await save_conversation_message(user_id, "assistant", response, message_type="text")

        # Send response
        await update.message.reply_text(response)
        logger.info(f"Sent AI response to {user_id}")

    except Exception as e:
        logger.error(f"Error in handle_message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error. Please try again!"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle food photos"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not is_authorized(user_id):
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

        # Analyze with vision AI
        analysis = await analyze_food_photo(str(photo_path))

        # Build response message
        response_lines = ["🍽️ **Food Analysis:**\n"]

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

        entry = FoodEntry(
            user_id=user_id,
            timestamp=datetime.now(),
            photo_path=str(photo_path),
            foods=analysis.foods,
            total_calories=total_calories,
            total_macros=total_macros,
            meal_type=None,  # Can be inferred from time later
            notes=update.message.caption or None
        )

        await save_food_entry(entry)
        logger.info(f"Saved food entry for {user_id}")

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


def create_bot_application() -> Application:
    """Create and configure the bot application"""
    global reminder_manager

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Initialize reminder manager
    reminder_manager = ReminderManager(app)
    logger.info("ReminderManager initialized")

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("transparency", transparency))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("approve_tool", approve_tool_command))
    app.add_handler(CommandHandler("reject_tool", reject_tool_command))

    # Add message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Bot application created")
    return app
