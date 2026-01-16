"""FastAPI application setup"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.api.routes import router
from src.api.middleware import setup_cors, setup_rate_limiting
from src.db.connection import db
from src.config import LOG_LEVEL
from src.exceptions import (
    HealthAgentError,
    ValidationError,
    DatabaseError,
    RecordNotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError
)

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

    # Custom exception handlers
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=exc.to_dict()
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=exc.to_dict()
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=exc.to_dict()
        )

    @app.exception_handler(RecordNotFoundError)
    async def not_found_error_handler(request: Request, exc: RecordNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=exc.to_dict()
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(request: Request, exc: DatabaseError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=exc.to_dict()
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(request: Request, exc: ConfigurationError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=exc.to_dict()
        )

    @app.exception_handler(HealthAgentError)
    async def health_agent_error_handler(request: Request, exc: HealthAgentError):
        """Catch-all handler for any HealthAgentError"""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=exc.to_dict()
        )

    # Global exception handler for unexpected errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "user_message": "Something went wrong. Please try again later."
            }
        )

    logger.info("FastAPI application created")

    return app
