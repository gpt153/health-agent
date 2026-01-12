"""Persistent typing indicator to improve perceived response time"""
import logging
import asyncio
from telegram import Chat
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class PersistentTypingIndicator:
    """
    Keeps the typing indicator alive during long-running operations.

    The Telegram API requires typing indicators to be refreshed every 5 seconds.
    This class manages that automatically using a background task.
    """

    def __init__(self, chat: Chat, interval: float = 4.0):
        """
        Initialize the persistent typing indicator.

        Args:
            chat: Telegram chat object to send typing indicator to
            interval: Seconds between typing indicator refreshes (default: 4s)
        """
        self.chat = chat
        self.interval = interval
        self._task = None
        self._running = False

    async def _typing_loop(self):
        """Background loop that sends typing indicator every N seconds"""
        while self._running:
            try:
                await self.chat.send_action("typing")
                logger.debug(f"Sent typing indicator to chat {self.chat.id}")
            except TelegramError as e:
                logger.warning(f"Failed to send typing indicator: {e}")
                # Don't crash on Telegram errors, just log and continue
            except Exception as e:
                logger.error(f"Unexpected error in typing loop: {e}")

            # Wait before next refresh
            await asyncio.sleep(self.interval)

    async def start(self):
        """Start the persistent typing indicator"""
        if self._running:
            logger.warning("Typing indicator already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._typing_loop())
        logger.debug(f"Started persistent typing indicator for chat {self.chat.id}")

    async def stop(self):
        """Stop the persistent typing indicator"""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # Expected when we cancel the task

            self._task = None

        logger.debug(f"Stopped persistent typing indicator for chat {self.chat.id}")

    async def __aenter__(self):
        """Context manager entry - start typing indicator"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop typing indicator"""
        await self.stop()
        return False  # Don't suppress exceptions
