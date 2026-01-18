"""Message routing logic for handle_message"""
import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.models.message_context import MessageContext
from src.handlers.onboarding import handle_onboarding_message
from src.handlers.message_helpers import format_response
from src.db.queries import (
    save_conversation_message,
    get_conversation_history,
    update_completion_note
)
from src.memory.file_manager import memory_manager
from src.memory.mem0_manager import mem0_manager
from src.agent import get_agent_response

logger = logging.getLogger(__name__)


async def route_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    msg_context: MessageContext,
    text: str
) -> None:
    """
    Route message to the appropriate handler based on user state.

    Routing priority:
    1. Pending activation → check for invite code or prompt
    2. Onboarding incomplete → onboarding handler
    3. Custom note entry → note handler
    4. Normal message → AI agent

    Args:
        update: Telegram update object
        context: Telegram context
        msg_context: User message context
        text: Message text
    """
    # Route 1: Pending activation
    if msg_context.is_pending_activation:
        await _handle_pending_activation(update, context, text)
        return

    # Route 2: Onboarding incomplete
    if msg_context.is_in_onboarding:
        await handle_onboarding_message(update, context)
        return

    # Route 3: Custom note entry
    if msg_context.is_in_note_entry:
        await _handle_custom_note_entry(
            update, context, text, msg_context.pending_note
        )
        return

    # Route 4: Normal AI agent processing
    await _handle_ai_message(update, context, msg_context.user_id, text)


async def _handle_pending_activation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str
) -> None:
    """Handle message from user pending activation"""
    # Import here to avoid circular import
    from src.bot import activate

    message_clean = text.strip().upper()
    if len(message_clean) >= 4 and len(message_clean) <= 50 and message_clean.replace(' ', '').isalnum():
        await activate(update, context)
    else:
        await update.message.reply_text(
            "⚠️ **Please activate your account first**\n\n"
            "Send your invite code to start using the bot.\n\n"
            "Example: `HEALTH2024`\n\n"
            "Don't have a code? Use /start to get more information."
        )


async def _handle_custom_note_entry(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    pending_note: Optional[dict]
) -> None:
    """Handle custom note entry flow"""
    # Handle cancel command
    if text.strip().lower() == '/cancel':
        context.user_data.pop('awaiting_custom_note', None)
        context.user_data.pop('pending_note', None)
        await update.message.reply_text("✅ Note entry cancelled.")
        return

    # Validate pending note data
    if not pending_note:
        await update.message.reply_text("❌ Error: Missing note context. Please try again.")
        context.user_data.pop('awaiting_custom_note', None)
        return

    reminder_id = pending_note.get('reminder_id')
    scheduled_time = pending_note.get('scheduled_time')

    if not reminder_id or not scheduled_time:
        await update.message.reply_text("❌ Error: Missing note context. Please try again.")
        context.user_data.pop('awaiting_custom_note', None)
        context.user_data.pop('pending_note', None)
        return

    # Save the note
    note_text = text.strip()[:200]

    try:
        await update_completion_note(
            str(update.effective_user.id),
            reminder_id,
            scheduled_time,
            note_text
        )
        await update.message.reply_text(
            f"✅ **Note saved!**\n\n📝 \"{note_text}\"\n\nThis will help track patterns over time.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error saving custom note: {e}", exc_info=True)
        await update.message.reply_text("❌ Error saving note. Please try again.")

    # Clean up
    context.user_data.pop('awaiting_custom_note', None)
    context.user_data.pop('pending_note', None)


async def _handle_ai_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: str,
    text: str
) -> None:
    """Handle normal AI agent message processing"""
    # Import here to avoid circular import
    from src.bot import auto_save_user_info

    try:
        from src.utils.typing_indicator import PersistentTypingIndicator

        async with PersistentTypingIndicator(update.message.chat):
            # Load conversation history
            message_history = await get_conversation_history(user_id, limit=20)

            # Route query to appropriate model
            from src.utils.query_router import query_router
            model_choice, routing_reason = query_router.route_query(text)

            model_override = None
            if model_choice == "haiku":
                model_override = "anthropic:claude-3-5-haiku-latest"
                logger.info(f"[ROUTER] Using Haiku for fast response: {routing_reason}")

            # Get reminder_manager from bot context
            reminder_manager = context.bot_data.get('reminder_manager')

            # Get agent response
            response = await get_agent_response(
                user_id, text, memory_manager, reminder_manager, message_history,
                bot_application=context.application,
                model_override=model_override
            )

        # Save conversation
        await save_conversation_message(user_id, "user", text, message_type="text")
        await save_conversation_message(user_id, "assistant", response, message_type="text")

        # Background memory tasks
        async def background_memory_tasks():
            mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
            mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})

            # auto_save_user_info is defined in src/bot.py
            logger.info(f"[DEBUG-FLOW] BEFORE auto_save_user_info for user {user_id}")
            logger.info(f"[DEBUG-FLOW] User message: {text[:100]}")
            logger.info(f"[DEBUG-FLOW] Agent response: {response[:100]}")
            await auto_save_user_info(user_id, text, response)
            logger.info(f"[DEBUG-FLOW] AFTER auto_save_user_info completed successfully")

        import asyncio
        asyncio.create_task(background_memory_tasks())

        # Send response with formatting
        await format_response(update, response, user_id)

    except Exception as e:
        logger.error(f"Error in AI message handling: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error. Please try again!"
        )
