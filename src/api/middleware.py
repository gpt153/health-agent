"""API middleware for rate limiting and CORS"""
import logging
import uuid
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
from src.config import ENABLE_PROMETHEUS, ENABLE_SENTRY

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


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracking and metrics"""

    async def dispatch(self, request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Set Sentry context
        if ENABLE_SENTRY:
            from src.monitoring import set_request_context
            endpoint = request.url.path
            set_request_context(request_id, f"{request.method} {endpoint}")

        # Track metrics
        if ENABLE_PROMETHEUS:
            from src.monitoring.prometheus_metrics import metrics
            start_time = time.time()

            try:
                response = await call_next(request)

                # Record successful request
                duration = time.time() - start_time
                metrics.http_requests_total.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=response.status_code
                ).inc()

                metrics.http_request_duration_seconds.labels(
                    method=request.method,
                    endpoint=request.url.path
                ).observe(duration)

                return response

            except Exception as e:
                # Record error
                duration = time.time() - start_time
                metrics.http_errors_total.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    error_type=type(e).__name__
                ).inc()

                metrics.http_request_duration_seconds.labels(
                    method=request.method,
                    endpoint=request.url.path
                ).observe(duration)

                raise
        else:
            response = await call_next(request)
            return response


def setup_monitoring(app):
    """Configure monitoring middleware"""
    app.add_middleware(MonitoringMiddleware)
    logger.info("Monitoring middleware configured")
