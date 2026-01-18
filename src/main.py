"""Main entry point for the health agent bot and API"""
import logging
import asyncio
import os
from src.config import validate_config, LOG_LEVEL, ENABLE_SENTRY
from src.db.connection import db
from src.bot import create_bot_application
from src.agent.dynamic_tools import tool_manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)

logger = logging.getLogger(__name__)

# Initialize Sentry monitoring early (for startup errors)
if ENABLE_SENTRY:
    from src.monitoring import init_sentry
    init_sentry()
    logger.info("Sentry monitoring initialized (early)")


async def run_telegram_bot() -> None:
    """Run Telegram bot"""
    app = None
    try:
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

        # Schedule pattern mining jobs (Epic 009 - Phase 6)
        logger.info("Scheduling pattern mining jobs...")
        from src.scheduler.pattern_mining import PatternMiningScheduler
        pattern_scheduler = PatternMiningScheduler(app)
        await pattern_scheduler.schedule_pattern_mining()

        await app.updater.start_polling()

        # Keep running until interrupted
        await asyncio.Event().wait()

    finally:
        # Cleanup
        if app:
            logger.info("Stopping bot...")
            await app.stop()
            await app.shutdown()


async def run_api_server() -> None:
    """Run REST API server"""
    import uvicorn
    from src.api.server import create_api_application

    # Get API configuration from environment
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8080"))

    logger.info(f"Starting API server on {api_host}:{api_port}...")

    # Create FastAPI app
    app = create_api_application()

    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=api_host,
        port=api_port,
        log_level=LOG_LEVEL.lower()
    )

    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        logger.info("API server stopped")


async def main() -> None:
    """Main application entry point"""
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()

        # Initialize database
        logger.info("Initializing database connection pool...")
        await db.init_pool()

        # Initialize resilience components
        logger.info("Initializing resilience components...")

        # Initialize local nutrition cache (SQLite)
        from src.db.nutrition_cache import init_nutrition_cache
        try:
            init_nutrition_cache()
            logger.info("✓ Nutrition cache initialized with common foods")
        except Exception as e:
            logger.error(f"Failed to initialize nutrition cache: {e}", exc_info=True)

        # Start Prometheus metrics server
        from prometheus_client import start_http_server
        from src.config import METRICS_PORT
        try:
            start_http_server(METRICS_PORT)
            logger.info(f"✓ Prometheus metrics exposed on :{METRICS_PORT}/metrics")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e}")

        # Load dynamic tools from database
        logger.info("Loading dynamic tools...")
        loaded_tools = await tool_manager.load_all_tools()
        logger.info(f"Loaded {len(loaded_tools)} dynamic tools: {', '.join(loaded_tools) if loaded_tools else 'none'}")

        # Determine run mode from environment
        run_mode = os.getenv("RUN_MODE", "bot").lower()

        if run_mode == "both":
            # Run both bot and API in parallel
            logger.info("Running in BOTH mode (Telegram bot + API server)")
            await asyncio.gather(
                run_telegram_bot(),
                run_api_server()
            )
        elif run_mode == "api":
            # Run only API server
            logger.info("Running in API mode (REST API only)")
            await run_api_server()
        elif run_mode == "bot":
            # Run only Telegram bot (default)
            logger.info("Running in BOT mode (Telegram bot only)")
            await run_telegram_bot()
        else:
            logger.error(f"Invalid RUN_MODE: {run_mode}. Must be 'bot', 'api', or 'both'")
            raise ValueError(f"Invalid RUN_MODE: {run_mode}")

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Closing database connection...")
        await db.close_pool()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
