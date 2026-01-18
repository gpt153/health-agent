"""
OpenTelemetry distributed tracing configuration.

This module initializes OpenTelemetry for distributed tracing with:
- OTLP exporter for Jaeger/Tempo/Grafana Cloud
- Auto-instrumentation for FastAPI and PostgreSQL
- Manual span creation utilities
- Trace context propagation
"""

import logging
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
import functools

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode, Span

logger = logging.getLogger(__name__)

# Global tracer instance
_tracer: Optional[trace.Tracer] = None


def init_tracing() -> None:
    """
    Initialize OpenTelemetry distributed tracing.

    Configures:
    - Resource attributes (service name, version, environment)
    - OTLP exporter for trace export
    - Batch span processor for efficient export
    - Global tracer provider

    Environment variables:
        ENABLE_TRACING: Feature flag to enable/disable tracing
        OTEL_SERVICE_NAME: Service name for traces
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint URL
        SENTRY_ENVIRONMENT: Environment name (dev/staging/prod)
        GIT_COMMIT_SHA: Release version
    """
    from src.config import (
        ENABLE_TRACING,
        OTEL_SERVICE_NAME,
        OTEL_EXPORTER_OTLP_ENDPOINT,
        SENTRY_ENVIRONMENT,
    )
    import os

    # Check if tracing is enabled
    if not ENABLE_TRACING:
        logger.info("Distributed tracing is disabled (ENABLE_TRACING=false)")
        return

    # Validate OTLP endpoint is configured
    if not OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.warning(
            "OTLP endpoint not configured - distributed tracing disabled"
        )
        return

    # Get release version
    release = os.getenv("GIT_COMMIT_SHA", "dev")[:7]

    # Create resource with service metadata
    resource = Resource.create(
        {
            SERVICE_NAME: OTEL_SERVICE_NAME,
            "service.version": release,
            "deployment.environment": SENTRY_ENVIRONMENT,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces"
    )

    # Add batch span processor for efficient export
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Initialize global tracer
    global _tracer
    _tracer = trace.get_tracer(__name__)

    logger.info(
        f"OpenTelemetry tracing initialized: service={OTEL_SERVICE_NAME}, "
        f"endpoint={OTEL_EXPORTER_OTLP_ENDPOINT}, environment={SENTRY_ENVIRONMENT}"
    )


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance.

    Returns:
        OpenTelemetry tracer for creating spans

    Example:
        >>> tracer = get_tracer()
        >>> with tracer.start_as_current_span("my_operation"):
        ...     do_work()
    """
    global _tracer
    if _tracer is None:
        # Return no-op tracer if tracing not initialized
        return trace.get_tracer(__name__)
    return _tracer


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    set_status_on_exception: bool = True,
):
    """
    Context manager to create a trace span.

    Args:
        name: Name of the span (e.g., "telegram.handle_message")
        attributes: Optional attributes to attach to span
        set_status_on_exception: Automatically mark span as error on exception

    Yields:
        The created span

    Example:
        >>> with trace_span("process_photo", {"photo_size": 1024}):
        ...     analyze_photo()
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(name) as span:
        # Add attributes
        if attributes:
            for key, value in attributes.items():
                # Convert value to string if it's not a primitive type
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(key, value)
                else:
                    span.set_attribute(key, str(value))

        try:
            yield span
        except Exception as e:
            if set_status_on_exception:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
            raise


def trace_function(
    span_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Decorator to automatically trace a function.

    Args:
        span_name: Name of the span (defaults to function name)
        attributes: Optional static attributes to attach

    Example:
        >>> @trace_function(span_name="agent.generate_response")
        ... async def get_agent_response(user_id: str, message: str):
        ...     return await generate(message)
    """

    def decorator(func: Callable):
        # Determine span name
        name = span_name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_span(name, attributes):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_span(name, attributes):
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if functools.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def add_span_attributes(span: Span, **attributes):
    """
    Add attributes to a span.

    Args:
        span: The span to add attributes to
        **attributes: Key-value pairs to add as attributes

    Example:
        >>> with trace_span("process_message") as span:
        ...     add_span_attributes(span, user_id="123", message_type="text")
    """
    for key, value in attributes.items():
        if isinstance(value, (str, int, float, bool)):
            span.set_attribute(key, value)
        else:
            span.set_attribute(key, str(value))


def add_span_event(span: Span, name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to a span.

    Events are timestamped annotations within a span.

    Args:
        span: The span to add the event to
        name: Event name
        attributes: Optional event attributes

    Example:
        >>> with trace_span("process_photo") as span:
        ...     add_span_event(span, "analysis_started")
        ...     result = analyze()
        ...     add_span_event(span, "analysis_complete", {"confidence": 0.95})
    """
    span.add_event(name, attributes or {})


def set_span_error(span: Span, error: Exception):
    """
    Mark a span as having an error.

    Args:
        span: The span to mark as error
        error: The exception that occurred

    Example:
        >>> with trace_span("api_call") as span:
        ...     try:
        ...         result = external_api()
        ...     except Exception as e:
        ...         set_span_error(span, e)
        ...         raise
    """
    span.set_status(Status(StatusCode.ERROR, str(error)))
    span.record_exception(error)


def get_current_span() -> Optional[Span]:
    """
    Get the currently active span.

    Returns:
        The current span, or None if no span is active

    Example:
        >>> span = get_current_span()
        >>> if span:
        ...     span.set_attribute("custom_attr", "value")
    """
    return trace.get_current_span()


def auto_instrument_fastapi(app):
    """
    Auto-instrument FastAPI application for tracing.

    This adds automatic tracing for all HTTP requests.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> auto_instrument_fastapi(app)
    """
    from src.config import ENABLE_TRACING

    if not ENABLE_TRACING:
        logger.info("FastAPI auto-instrumentation skipped (tracing disabled)")
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI auto-instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to auto-instrument FastAPI: {e}")


def auto_instrument_psycopg():
    """
    Auto-instrument psycopg for database query tracing.

    This adds automatic tracing for all database queries.

    Example:
        >>> auto_instrument_psycopg()
    """
    from src.config import ENABLE_TRACING

    if not ENABLE_TRACING:
        logger.info("PostgreSQL auto-instrumentation skipped (tracing disabled)")
        return

    try:
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

        PsycopgInstrumentor().instrument()
        logger.info("PostgreSQL auto-instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to auto-instrument psycopg: {e}")


def shutdown_tracing():
    """
    Gracefully shutdown tracing.

    Flushes any pending spans before shutting down.
    Should be called during application shutdown.
    """
    provider = trace.get_tracer_provider()
    if provider and hasattr(provider, "shutdown"):
        logger.info("Flushing traces before shutdown...")
        provider.shutdown()
        logger.info("Tracing shutdown complete")
