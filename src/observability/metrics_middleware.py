"""
FastAPI middleware for automatic Prometheus metrics collection.

This middleware automatically tracks:
- Request counts by endpoint, method, and status code
- Request latency histograms
- Requests in progress (concurrent requests)
"""

import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
)

logger = logging.getLogger(__name__)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics for HTTP requests.

    Automatically tracks:
    - Total requests (counter) by method, endpoint, status
    - Request duration (histogram) by method, endpoint
    - Requests in progress (gauge) by method, endpoint
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and collect metrics.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain

        Returns:
            The HTTP response
        """
        # Extract method and path
        method = request.method
        path = self._normalize_path(request.url.path)

        # Track request in progress
        http_requests_in_progress.labels(method=method, endpoint=path).inc()

        # Record start time
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            # If an exception occurs, record it as a 500 error
            logger.error(f"Request failed: {e}", exc_info=True)
            status_code = 500
            raise

        finally:
            # Always decrement in-progress counter and record metrics
            http_requests_in_progress.labels(method=method, endpoint=path).dec()

            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=method, endpoint=path, status=status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=method, endpoint=path
            ).observe(duration)

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Normalize request path to reduce cardinality.

        This prevents metrics explosion by grouping similar paths together.
        For example:
        - /api/users/123 -> /api/users/{id}
        - /api/food/456/edit -> /api/food/{id}/edit

        Args:
            path: The raw request path

        Returns:
            Normalized path pattern
        """
        # Special case: metrics endpoint
        if path == "/metrics":
            return "/metrics"

        # Special case: health/status endpoints
        if path in ["/health", "/status", "/"]:
            return path

        # Split path into parts
        parts = path.strip("/").split("/")

        # Normalize path parts
        normalized_parts = []
        for part in parts:
            # If part looks like an ID (all digits or UUID), replace with placeholder
            if part.isdigit():
                normalized_parts.append("{id}")
            elif self._is_uuid(part):
                normalized_parts.append("{uuid}")
            else:
                normalized_parts.append(part)

        # Reconstruct path
        normalized = "/" + "/".join(normalized_parts)

        return normalized

    def _is_uuid(self, value: str) -> bool:
        """
        Check if a string looks like a UUID.

        Args:
            value: String to check

        Returns:
            True if the string matches UUID pattern
        """
        # Simple UUID check (8-4-4-4-12 hex digits)
        parts = value.split("-")
        if len(parts) != 5:
            return False

        try:
            # Check if all parts are hexadecimal
            for part in parts:
                int(part, 16)
            return True
        except ValueError:
            return False


def setup_metrics_middleware(app):
    """
    Add Prometheus metrics middleware to FastAPI application.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> setup_metrics_middleware(app)
    """
    from src.config import ENABLE_METRICS

    if not ENABLE_METRICS:
        logger.info("Metrics collection is disabled (ENABLE_METRICS=false)")
        return

    app.add_middleware(PrometheusMiddleware)
    logger.info("Prometheus metrics middleware added to FastAPI")
