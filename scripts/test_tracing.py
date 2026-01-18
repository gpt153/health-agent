#!/usr/bin/env python3
"""
Test script to verify OpenTelemetry tracing integration.

Usage:
    python scripts/test_tracing.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import logging

# Disable Sentry for this test
os.environ["ENABLE_SENTRY"] = "false"
os.environ["ENABLE_TRACING"] = "true"
os.environ["OTEL_SERVICE_NAME"] = "health-agent-test"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


def test_tracing_initialization():
    """Test 1: Tracing initialization"""
    logger.info("Test 1: Initializing tracing...")

    from src.observability.tracing import init_tracing, get_tracer

    init_tracing()
    tracer = get_tracer()

    assert tracer is not None
    logger.info("✓ Tracing initialized successfully")


def test_manual_spans():
    """Test 2: Manual span creation"""
    logger.info("Test 2: Creating manual spans...")

    from src.observability.tracing import trace_span

    with trace_span("test_operation", {"test_attr": "value"}):
        # Simulate some work
        import time

        time.sleep(0.1)

    logger.info("✓ Manual span created successfully")


def test_nested_spans():
    """Test 3: Nested spans"""
    logger.info("Test 3: Creating nested spans...")

    from src.observability.tracing import trace_span

    with trace_span("parent_operation"):
        with trace_span("child_operation_1"):
            pass

        with trace_span("child_operation_2"):
            pass

    logger.info("✓ Nested spans created successfully")


def test_decorator():
    """Test 4: Function decorator"""
    logger.info("Test 4: Testing trace decorator...")

    from src.observability.tracing import trace_function

    @trace_function(span_name="test.decorated_function")
    def my_function(x, y):
        return x + y

    result = my_function(2, 3)
    assert result == 5

    logger.info("✓ Function decorator works correctly")


def test_span_attributes():
    """Test 5: Adding span attributes"""
    logger.info("Test 5: Adding span attributes...")

    from src.observability.tracing import trace_span, add_span_attributes

    with trace_span("operation_with_attrs") as span:
        add_span_attributes(
            span, user_id="123", message_type="text", message_length=50
        )

    logger.info("✓ Span attributes added successfully")


def test_span_events():
    """Test 6: Adding span events"""
    logger.info("Test 6: Adding span events...")

    from src.observability.tracing import trace_span, add_span_event

    with trace_span("operation_with_events") as span:
        add_span_event(span, "processing_started")
        # Simulate work
        import time

        time.sleep(0.05)
        add_span_event(span, "processing_complete", {"items_processed": 10})

    logger.info("✓ Span events added successfully")


def test_error_handling():
    """Test 7: Error handling in spans"""
    logger.info("Test 7: Testing error handling...")

    from src.observability.tracing import trace_span

    try:
        with trace_span("operation_with_error"):
            raise ValueError("Test error")
    except ValueError:
        pass  # Expected

    logger.info("✓ Error handling works correctly")


def main():
    """Run all tracing tests"""
    logger.info("=" * 70)
    logger.info("OpenTelemetry Tracing Test Suite")
    logger.info("=" * 70)
    logger.info("")

    # Check if OTLP endpoint is accessible
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    logger.info(f"OTLP Endpoint: {endpoint}")
    logger.info("Note: Traces will be exported to this endpoint")
    logger.info("")

    try:
        test_tracing_initialization()
        logger.info("")

        test_manual_spans()
        logger.info("")

        test_nested_spans()
        logger.info("")

        test_decorator()
        logger.info("")

        test_span_attributes()
        logger.info("")

        test_span_events()
        logger.info("")

        test_error_handling()
        logger.info("")

    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        return 1

    logger.info("=" * 70)
    logger.info("All tests passed!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Start Jaeger: docker run -d -p 16686:16686 -p 4318:4318 jaegertracing/all-in-one:latest")
    logger.info("2. Run the application: RUN_MODE=api python -m src.main")
    logger.info("3. View traces at: http://localhost:16686")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
