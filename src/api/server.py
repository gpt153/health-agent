"""FastAPI application setup"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.api.routes import router
from src.api.middleware import setup_cors, setup_rate_limiting
from src.db.connection import db
from src.config import LOG_LEVEL

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application"""
    # Startup
    logger.info("Starting API server...")
    await db.init_pool()
    logger.info("Database pool initialized")

    # Load dynamic tools
    from src.agent.dynamic_tools import tool_manager
    loaded_tools = await tool_manager.load_all_tools()
    logger.info(f"Loaded {len(loaded_tools)} dynamic tools")

    yield

    # Shutdown
    logger.info("Shutting down API server...")
    await db.close_pool()
    logger.info("Database pool closed")


def create_api_application() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Health Agent API",
        description="REST API for AI Health Coach",
        version="1.0.0",
        lifespan=lifespan
    )

    # Setup middleware
    setup_cors(app)
    setup_rate_limiting(app)

    # Include routes
    app.include_router(router)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)}
        )

    logger.info("FastAPI application created")

    return app
