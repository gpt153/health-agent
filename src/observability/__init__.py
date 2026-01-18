"""
Observability module for health-agent application.

This module provides:
- Error tracking with Sentry
- Metrics collection with Prometheus
- Distributed tracing with OpenTelemetry
"""

__all__ = ["sentry_config", "context", "metrics", "tracing"]
