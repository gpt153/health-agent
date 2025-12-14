"""Main entry point for the health agent bot"""
import logging
import asyncio
from src.config import validate_config, LOG_LEVEL
from src.db.connection import db
from src.bot import create_bot_application

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

        # Create and start bot
        logger.info("Starting Telegram bot...")
        app = create_bot_application()

        # Run the bot
        logger.info("Bot is running. Press Ctrl+C to stop.")
        await app.initialize()
        await app.start()
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
