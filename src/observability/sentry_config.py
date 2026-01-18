"""Sentry configuration and initialization for error tracking."""

import logging
import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry SDK for error tracking and performance monitoring.

    Configures Sentry with:
    - FastAPI integration for automatic request tracking
    - Logging integration for breadcrumbs
    - Environment-specific configuration
    - Release tracking
    - Performance monitoring (transactions)

    Environment variables:
        SENTRY_DSN: Sentry project DSN (required)
        SENTRY_ENVIRONMENT: Environment name (development, staging, production)
        SENTRY_TRACES_SAMPLE_RATE: Percentage of transactions to sample (0.0-1.0)
        ENABLE_SENTRY: Feature flag to enable/disable Sentry
        GIT_COMMIT_SHA: Git commit SHA for release tracking (optional)
    """
    from src.config import (
        SENTRY_DSN,
        SENTRY_ENVIRONMENT,
        SENTRY_TRACES_SAMPLE_RATE,
        ENABLE_SENTRY,
    )

    # Check if Sentry is enabled
    if not ENABLE_SENTRY:
        logger.info("Sentry is disabled (ENABLE_SENTRY=false)")
        return

    # Validate DSN is configured
    if not SENTRY_DSN:
        logger.warning("Sentry DSN not configured - error tracking disabled")
        return

    # Get release version from environment (git commit SHA if available)
    release = os.getenv("GIT_COMMIT_SHA")
    if release:
        release = f"health-agent@{release[:7]}"  # Use short SHA
    else:
        release = "health-agent@dev"

    # Configure logging integration for breadcrumbs
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors and above as events
    )

    # Configure FastAPI integration
    fastapi_integration = FastApiIntegration(
        transaction_style="endpoint",  # Group transactions by endpoint path
    )

    # Initialize Sentry SDK
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        release=release,
        # Integrations
        integrations=[
            fastapi_integration,
            logging_integration,
        ],
        # Performance monitoring
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        # Attach stack traces to messages
        attach_stacktrace=True,
        # Send default PII (user IP, cookies, etc.)
        send_default_pii=True,
        # Filter out common non-error exceptions
        before_send=_before_send,
    )

    logger.info(
        f"Sentry initialized: environment={SENTRY_ENVIRONMENT}, "
        f"release={release}, traces_sample_rate={SENTRY_TRACES_SAMPLE_RATE}"
    )


def _before_send(event, hint):
    """
    Filter events before sending to Sentry.

    This function is called before each event is sent to Sentry,
    allowing us to:
    - Filter out non-error HTTP exceptions (404, etc.)
    - Add custom tags or context
    - Modify event data

    Args:
        event: The event dictionary to be sent to Sentry
        hint: Additional information about the event

    Returns:
        The modified event, or None to drop the event
    """
    # Don't send HTTP 404 errors to Sentry
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if exc_type.__name__ == "HTTPException":
            # Only send 5xx errors, not 4xx
            if hasattr(exc_value, "status_code") and exc_value.status_code < 500:
                return None

    return event


def shutdown_sentry() -> None:
    """
    Gracefully shutdown Sentry client.

    Flushes any pending events to Sentry before shutting down.
    Should be called during application shutdown.
    """
    client = sentry_sdk.Hub.current.client
    if client is not None:
        logger.info("Flushing Sentry events before shutdown...")
        client.close(timeout=2.0)  # Wait up to 2 seconds for pending events
        logger.info("Sentry shutdown complete")
