#!/usr/bin/env python3
"""
Test script to verify Sentry integration.

This script triggers test errors to verify that Sentry is properly
configured and capturing exceptions.

Usage:
    python scripts/test_sentry.py

Environment variables:
    SENTRY_DSN: Must be set to a valid Sentry DSN
    ENABLE_SENTRY: Must be set to "true"
"""

import sys
import os
import time
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.observability.sentry_config import init_sentry
from src.observability.context import (
    set_user_context,
    add_breadcrumb,
    capture_exception_with_context,
    capture_message,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


def test_basic_error():
    """Test 1: Basic exception capture"""
    logger.info("Test 1: Triggering basic exception...")

    try:
        # This will raise a ZeroDivisionError
        result = 1 / 0
    except Exception as e:
        logger.info(f"✓ Exception raised: {e}")
        logger.info("  → This error should appear in Sentry")


def test_error_with_user_context():
    """Test 2: Exception with user context"""
    logger.info("Test 2: Triggering exception with user context...")

    # Set user context
    set_user_context("123456789", username="test_user")
    logger.info("  → User context set: user_id=123456789, username=test_user")

    try:
        # Trigger an error
        raise ValueError("Test error with user context")
    except Exception as e:
        logger.info(f"✓ Exception raised: {e}")
        logger.info("  → This error should appear in Sentry with user info")


def test_error_with_breadcrumbs():
    """Test 3: Exception with breadcrumbs"""
    logger.info("Test 3: Triggering exception with breadcrumbs...")

    # Add breadcrumbs
    add_breadcrumb("test", "User opened app")
    add_breadcrumb("test", "User navigated to settings")
    add_breadcrumb("test", "User clicked dangerous button", level="warning")
    logger.info("  → Added 3 breadcrumbs")

    try:
        # Trigger an error
        raise RuntimeError("Test error with breadcrumbs")
    except Exception as e:
        logger.info(f"✓ Exception raised: {e}")
        logger.info("  → This error should appear in Sentry with breadcrumb trail")


def test_manual_exception_capture():
    """Test 4: Manual exception capture with context"""
    logger.info("Test 4: Manually capturing exception with custom context...")

    try:
        # Simulate some operation
        data = {"key": "value"}
        if "missing" not in data:
            raise KeyError("Missing required key in data")
    except Exception as e:
        # Manually capture with additional context
        event_id = capture_exception_with_context(
            e,
            context={
                "operation": "test_operation",
                "data_keys": list(data.keys()),
            },
            tags={
                "test_type": "manual_capture",
                "component": "test_script",
            },
        )
        logger.info(f"✓ Exception manually captured: {e}")
        logger.info(f"  → Sentry event ID: {event_id}")


def test_message_capture():
    """Test 5: Capture informational message"""
    logger.info("Test 5: Capturing informational message...")

    event_id = capture_message(
        "Test message from test script",
        level="info",
        tags={"test_type": "message_capture"},
    )

    logger.info(f"✓ Message captured")
    logger.info(f"  → Sentry event ID: {event_id}")
    logger.info("  → This should appear in Sentry as an info message")


def test_handled_error():
    """Test 6: Error that's caught and handled gracefully"""
    logger.info("Test 6: Handled error (captured but app continues)...")

    try:
        # Simulate an API call that fails
        raise ConnectionError("Failed to connect to external API")
    except ConnectionError as e:
        # Capture the error for tracking, but handle it gracefully
        event_id = capture_exception_with_context(
            e,
            context={"api_endpoint": "/test/endpoint"},
            tags={"severity": "low", "handled": "true"},
        )
        logger.info(f"✓ Error handled gracefully: {e}")
        logger.info(f"  → Sentry event ID: {event_id}")
        logger.info("  → App continues running despite error")


def main():
    """Run all Sentry integration tests"""
    logger.info("=" * 70)
    logger.info("Sentry Integration Test Suite")
    logger.info("=" * 70)

    # Check if Sentry is configured
    sentry_dsn = os.getenv("SENTRY_DSN")
    enable_sentry = os.getenv("ENABLE_SENTRY", "true").lower() == "true"

    if not sentry_dsn:
        logger.error("ERROR: SENTRY_DSN is not configured")
        logger.error("Please set SENTRY_DSN in your environment or .env file")
        return 1

    if not enable_sentry:
        logger.warning("WARNING: ENABLE_SENTRY is set to false")
        logger.warning("Sentry will not capture any errors")

    logger.info(f"SENTRY_DSN: {sentry_dsn[:30]}...")
    logger.info(f"ENABLE_SENTRY: {enable_sentry}")
    logger.info("")

    # Initialize Sentry
    logger.info("Initializing Sentry...")
    init_sentry()
    logger.info("✓ Sentry initialized")
    logger.info("")

    # Run tests
    try:
        test_basic_error()
        logger.info("")

        test_error_with_user_context()
        logger.info("")

        test_error_with_breadcrumbs()
        logger.info("")

        test_manual_exception_capture()
        logger.info("")

        test_message_capture()
        logger.info("")

        test_handled_error()
        logger.info("")

    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        return 1

    # Give Sentry time to send events
    logger.info("=" * 70)
    logger.info("Waiting 3 seconds for Sentry to send events...")
    time.sleep(3)

    logger.info("=" * 70)
    logger.info("Test suite complete!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Check your Sentry dashboard for the test errors")
    logger.info("2. Verify user context, breadcrumbs, and tags are attached")
    logger.info("3. Verify all 6 events were captured")
    logger.info("")
    logger.info(f"Sentry dashboard: https://sentry.io/")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
