"""API middleware for rate limiting and CORS"""
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
import os

from src.config import RATE_LIMIT_STORAGE_URL

logger = logging.getLogger(__name__)

# Initialize rate limiter with configurable storage
# For production, set RATE_LIMIT_STORAGE_URL=redis://localhost:6379
limiter = Limiter(key_func=get_remote_address, storage_uri=RATE_LIMIT_STORAGE_URL)


def setup_cors(app):
    """Configure CORS middleware"""
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"CORS configured for origins: {cors_origins}")


def setup_rate_limiting(app):
    """Configure rate limiting"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    storage_type = "Redis" if "redis" in RATE_LIMIT_STORAGE_URL else "Memory"
    logger.info(f"Rate limiting configured with {storage_type} storage")
