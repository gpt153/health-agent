"""API middleware for rate limiting, CORS, and performance monitoring"""
import logging
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Performance tracking
request_count = 0
slow_request_threshold_ms = 3000  # 3 seconds


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware

    Tracks request timing and logs slow requests.
    Integrates with profiling utilities from Phase 1.
    """

    async def dispatch(self, request: Request, call_next):
        global request_count

        # Start timing
        start_time = time.perf_counter()

        # Track request count
        request_count += 1

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        response.headers["X-Request-ID"] = str(request_count)

        # Log slow requests
        if duration_ms > slow_request_threshold_ms:
            logger.warning(
                f"SLOW REQUEST: {request.method} {request.url.path} "
                f"took {duration_ms:.0f}ms (threshold: {slow_request_threshold_ms}ms)"
            )

        # Log all requests (debug level)
        logger.debug(
            f"{request.method} {request.url.path} - "
            f"{response.status_code} - {duration_ms:.2f}ms"
        )

        return response


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
    logger.info("Rate limiting configured: 100/minute per IP")


def setup_performance_monitoring(app):
    """Configure performance monitoring middleware"""
    app.add_middleware(PerformanceMonitoringMiddleware)
    logger.info(
        f"Performance monitoring enabled "
        f"(slow request threshold: {slow_request_threshold_ms}ms)"
    )
