#!/usr/bin/env python3
"""
Test script to verify Prometheus metrics collection.

This script tests that metrics are properly defined, can be incremented,
and are exposed in the correct Prometheus format.

Usage:
    python scripts/test_metrics.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import logging

# Disable Sentry for this test
os.environ["ENABLE_SENTRY"] = "false"
os.environ["ENABLE_METRICS"] = "true"

from prometheus_client import generate_latest
from src.observability.metrics import (
    # HTTP metrics
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    # Bot metrics
    telegram_messages_total,
    telegram_message_duration_seconds,
    telegram_commands_total,
    # Error metrics
    errors_total,
    # User metrics
    active_users,
    user_registrations_total,
    # Food tracking metrics
    food_photos_analyzed_total,
    food_photo_processing_duration_seconds,
    food_entries_created_total,
    # AI metrics
    agent_response_duration_seconds,
    agent_token_usage_total,
    agent_requests_total,
    # Database metrics
    db_query_duration_seconds,
    db_connections_active,
    db_pool_size,
    db_queries_total,
    # External API metrics
    external_api_calls_total,
    external_api_duration_seconds,
    # Memory metrics
    memory_searches_total,
    # Gamification metrics
    gamification_xp_awarded_total,
    gamification_achievements_unlocked_total,
    # Helper functions
    get_confidence_level,
    get_complexity_level,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


def test_counter_metrics():
    """Test counter metrics can be incremented."""
    logger.info("Test 1: Counter metrics...")

    # HTTP requests
    http_requests_total.labels(method="GET", endpoint="/api/v1/chat", status=200).inc()
    http_requests_total.labels(method="POST", endpoint="/api/v1/chat", status=200).inc(5)

    # Telegram messages
    telegram_messages_total.labels(message_type="text", status="success").inc(10)
    telegram_messages_total.labels(message_type="photo", status="success").inc(3)
    telegram_messages_total.labels(message_type="voice", status="error").inc(1)

    # Commands
    telegram_commands_total.labels(command="/start").inc(5)
    telegram_commands_total.labels(command="/help").inc(2)

    # Errors
    errors_total.labels(error_type="ValueError", component="bot").inc(1)
    errors_total.labels(error_type="ConnectionError", component="api").inc(2)

    # User registrations
    user_registrations_total.inc(3)

    # Food entries
    food_entries_created_total.labels(entry_type="photo").inc(5)
    food_entries_created_total.labels(entry_type="manual").inc(2)

    # Food photos analyzed
    food_photos_analyzed_total.labels(confidence_level="high").inc(4)
    food_photos_analyzed_total.labels(confidence_level="medium").inc(2)
    food_photos_analyzed_total.labels(confidence_level="low").inc(1)

    # AI requests
    agent_requests_total.labels(model="haiku", status="success").inc(10)
    agent_requests_total.labels(model="sonnet", status="success").inc(5)

    # AI tokens
    agent_token_usage_total.labels(
        provider="anthropic", model="haiku", token_type="input"
    ).inc(1000)
    agent_token_usage_total.labels(
        provider="anthropic", model="haiku", token_type="output"
    ).inc(500)

    # Database queries
    db_queries_total.labels(query_type="select", status="success").inc(50)
    db_queries_total.labels(query_type="insert", status="success").inc(10)

    # External API calls
    external_api_calls_total.labels(service="openai", status="success").inc(5)
    external_api_calls_total.labels(service="usda", status="success").inc(3)

    # Memory searches
    memory_searches_total.labels(search_type="conversation", status="success").inc(8)

    # Gamification
    gamification_xp_awarded_total.labels(activity_type="food_entry").inc(50)
    gamification_achievements_unlocked_total.labels(achievement_type="first_meal").inc(1)

    logger.info("✓ Counter metrics incremented successfully")


def test_gauge_metrics():
    """Test gauge metrics can be set."""
    logger.info("Test 2: Gauge metrics...")

    # Active users
    active_users.labels(time_period="last_hour").set(5)
    active_users.labels(time_period="last_day").set(15)
    active_users.labels(time_period="last_week").set(50)

    # Database connections
    db_connections_active.set(3)
    db_pool_size.labels(state="total").set(10)
    db_pool_size.labels(state="available").set(7)
    db_pool_size.labels(state="in_use").set(3)

    # HTTP in progress
    http_requests_in_progress.labels(method="POST", endpoint="/api/v1/chat").set(2)

    logger.info("✓ Gauge metrics set successfully")


def test_histogram_metrics():
    """Test histogram metrics can observe values."""
    logger.info("Test 3: Histogram metrics...")

    # HTTP request duration
    http_request_duration_seconds.labels(method="GET", endpoint="/api/v1/chat").observe(
        0.15
    )
    http_request_duration_seconds.labels(method="POST", endpoint="/api/v1/chat").observe(
        0.5
    )

    # Telegram message duration
    telegram_message_duration_seconds.labels(message_type="text").observe(1.2)
    telegram_message_duration_seconds.labels(message_type="photo").observe(5.3)

    # Food photo processing
    food_photo_processing_duration_seconds.observe(3.5)
    food_photo_processing_duration_seconds.observe(2.1)

    # Agent response time
    agent_response_duration_seconds.labels(model="haiku", complexity="simple").observe(
        1.5
    )
    agent_response_duration_seconds.labels(model="sonnet", complexity="complex").observe(
        10.2
    )

    # Database query duration
    db_query_duration_seconds.labels(query_type="select").observe(0.005)
    db_query_duration_seconds.labels(query_type="insert").observe(0.01)

    # External API duration
    external_api_duration_seconds.labels(service="openai").observe(2.5)
    external_api_duration_seconds.labels(service="usda").observe(0.8)

    logger.info("✓ Histogram metrics observed successfully")


def test_helper_functions():
    """Test helper functions."""
    logger.info("Test 4: Helper functions...")

    # Test confidence level categorization
    assert get_confidence_level(0.95) == "high"
    assert get_confidence_level(0.75) == "medium"
    assert get_confidence_level(0.3) == "low"

    # Test complexity level
    assert get_complexity_level(100) == "simple"
    assert get_complexity_level(1000) == "complex"

    logger.info("✓ Helper functions working correctly")


def test_metrics_export():
    """Test that metrics can be exported in Prometheus format."""
    logger.info("Test 5: Metrics export...")

    # Generate Prometheus format
    output = generate_latest()

    # Check it's bytes
    assert isinstance(output, bytes)

    # Decode and check for some expected metrics
    output_str = output.decode("utf-8")

    # Check for some of our metrics
    assert "http_requests_total" in output_str
    assert "telegram_messages_total" in output_str
    assert "agent_token_usage_total" in output_str
    assert "db_connections_active" in output_str

    logger.info("✓ Metrics exported successfully")
    logger.info(f"  Total output size: {len(output)} bytes")

    # Print first 500 chars as sample
    logger.info("\n--- Sample output (first 500 chars) ---")
    logger.info(output_str[:500])
    logger.info("--- End sample ---\n")


def main():
    """Run all metrics tests."""
    logger.info("=" * 70)
    logger.info("Prometheus Metrics Test Suite")
    logger.info("=" * 70)
    logger.info("")

    try:
        test_counter_metrics()
        logger.info("")

        test_gauge_metrics()
        logger.info("")

        test_histogram_metrics()
        logger.info("")

        test_helper_functions()
        logger.info("")

        test_metrics_export()
        logger.info("")

    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        return 1

    logger.info("=" * 70)
    logger.info("All tests passed!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Start the API server: RUN_MODE=api python -m src.main")
    logger.info("2. Access metrics at: http://localhost:8080/metrics")
    logger.info("3. Verify metrics are updated as you use the API")
    logger.info("")
    logger.info("To integrate with Prometheus:")
    logger.info("1. Install Prometheus")
    logger.info("2. Add scrape config pointing to http://localhost:8080/metrics")
    logger.info("3. View metrics in Prometheus UI")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
