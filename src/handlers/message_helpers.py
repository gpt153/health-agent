"""Helper functions for message processing"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
import telegram.error

from src.models.message_context import ValidationResult, MessageContext
from src.utils.auth import is_authorized
from src.bot import should_process_message

logger = logging.getLogger(__name__)


async def validate_message_input(
    update: Update,
    user_id: str
) -> ValidationResult:
    """
    Validate message input and check if it should be processed.

    Checks:
    - Topic filter (should_process_message)
    - Authorization (is_authorized)

    Returns:
        ValidationResult with is_valid=True if message should be processed,
        is_valid=False with reason if it should be ignored.
    """
    # Check topic filter
    if not should_process_message(update):
        return ValidationResult(is_valid=False, reason="topic_filter")

    # Check authorization (for active users)
    if not await is_authorized(user_id):
        return ValidationResult(is_valid=False, reason="unauthorized")

    return ValidationResult(is_valid=True)


async def extract_message_context(
    user_id: str,
    context: ContextTypes.DEFAULT_TYPE
) -> MessageContext:
    """
    Extract user context needed for message routing.

    Fetches:
    - Subscription status
    - Onboarding state
    - User conversation state (custom note entry)

    Returns:
        MessageContext with all relevant user state
    """
    from src.db.queries import get_user_subscription_status, get_onboarding_state

    subscription = await get_user_subscription_status(user_id)
    onboarding = await get_onboarding_state(user_id)

    return MessageContext(
        user_id=user_id,
        subscription=subscription,
        onboarding=onboarding,
        awaiting_custom_note=context.user_data.get('awaiting_custom_note', False),
        pending_note=context.user_data.get('pending_note')
    )


async def format_response(
    update: Update,
    response: str,
    user_id: str
) -> None:
    """
    Format and send response with Markdown fallback.

    Attempts to send with Markdown formatting first.
    Falls back to plain text if Markdown parsing fails.

    Args:
        update: Telegram update object
        response: Response text to send
        user_id: User ID for logging
    """
    try:
        await update.message.reply_text(response, parse_mode="Markdown")
        logger.info(f"Sent AI response to {user_id}")
    except telegram.error.BadRequest as e:
        if "can't parse entities" in str(e).lower():
            logger.warning(f"Markdown parse error, sending as plain text: {e}")
            await update.message.reply_text(response)
        else:
            raise
