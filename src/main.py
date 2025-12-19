"""Main entry point for the health agent bot"""
import logging
import asyncio
from src.config import validate_config, LOG_LEVEL
from src.db.connection import db
from src.bot import create_bot_application
from src.agent.dynamic_tools import tool_manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main application entry point"""
    app = None
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()

        # Initialize database
        logger.info("Initializing database connection pool...")
        await db.init_pool()

        # Load dynamic tools from database
        logger.info("Loading dynamic tools...")
        loaded_tools = await tool_manager.load_all_tools()
        logger.info(f"Loaded {len(loaded_tools)} dynamic tools: {', '.join(loaded_tools) if loaded_tools else 'none'}")

        # Create and start bot
        logger.info("Starting Telegram bot...")
        app = create_bot_application()

        # Run the bot
        logger.info("Bot is running. Press Ctrl+C to stop.")
        await app.initialize()
        await app.start()

        # Load reminders from database (after bot is started)
        from src.bot import reminder_manager
        if reminder_manager:
            logger.info("Loading reminders from database...")
            await reminder_manager.load_reminders()

            # Load sleep quiz schedules
            logger.info("Loading sleep quiz schedules...")
            await reminder_manager.load_sleep_quiz_schedules()

        await app.updater.start_polling()

        # Keep running until interrupted
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        if app:
            logger.info("Stopping bot...")
            await app.stop()
            await app.shutdown()

        logger.info("Closing database connection...")
        await db.close_pool()

        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
