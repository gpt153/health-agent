"""Sentry configuration and helpers"""
import logging
from contextlib import contextmanager
from typing import Any, Optional
from src.config import ENABLE_SENTRY, SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry SDK with FastAPI integration"""
    if not ENABLE_SENTRY:
        logger.info("Sentry monitoring disabled")
        return

    if not SENTRY_DSN:
        logger.warning("Sentry enabled but SENTRY_DSN not configured")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=SENTRY_ENVIRONMENT,
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
            ],
            # Add release info if available
            release=None,  # Can be set via env var in production
            # Enable performance monitoring
            enable_tracing=True,
        )

        logger.info(
            f"Sentry initialized: environment={SENTRY_ENVIRONMENT}, "
            f"sample_rate={SENTRY_TRACES_SAMPLE_RATE}"
        )
    except ImportError:
        logger.error("sentry-sdk not installed. Install with: pip install sentry-sdk[fastapi]")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)


def set_user_context(user_id: str) -> None:
    """Set user context for Sentry events"""
    if not ENABLE_SENTRY:
        return

    try:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id})
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to set user context: {e}")


def set_request_context(request_id: str, operation: str) -> None:
    """Set request context for Sentry events"""
    if not ENABLE_SENTRY:
        return

    try:
        import sentry_sdk
        sentry_sdk.set_tag("request_id", request_id)
        sentry_sdk.set_tag("operation", operation)
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to set request context: {e}")


def capture_exception(exception: Exception, **extra_context: Any) -> None:
    """Capture exception with custom context"""
    if not ENABLE_SENTRY:
        return

    try:
        import sentry_sdk

        # Add extra context as tags
        for key, value in extra_context.items():
            sentry_sdk.set_tag(key, str(value))

        sentry_sdk.capture_exception(exception)
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to capture exception in Sentry: {e}")


def capture_message(message: str, level: str = "info", **extra_context: Any) -> None:
    """Capture informational message"""
    if not ENABLE_SENTRY:
        return

    try:
        import sentry_sdk

        # Add extra context as tags
        for key, value in extra_context.items():
            sentry_sdk.set_tag(key, str(value))

        sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to capture message in Sentry: {e}")


@contextmanager
def sentry_transaction(operation: str, name: str):
    """Context manager for Sentry transaction tracking"""
    if not ENABLE_SENTRY:
        yield None
        return

    try:
        import sentry_sdk

        with sentry_sdk.start_transaction(op=operation, name=name) as transaction:
            yield transaction
    except ImportError:
        yield None
    except Exception as e:
        logger.error(f"Failed to create Sentry transaction: {e}")
        yield None
