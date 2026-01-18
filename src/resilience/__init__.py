"""Resilience patterns for external API calls

This module provides circuit breakers, retry logic, fallback strategies,
and metrics collection for protecting against cascading failures.
"""

from src.resilience.circuit_breaker import (
    OPENAI_BREAKER,
    ANTHROPIC_BREAKER,
    USDA_BREAKER,
    with_circuit_breaker,
)
from src.resilience.retry import retry_with_backoff, with_retry
from src.resilience.fallback import execute_with_fallbacks, FallbackStrategy
from src.resilience.metrics import (
    record_circuit_breaker_state,
    record_api_call,
    record_api_failure,
    record_retry,
    record_fallback,
)

__all__ = [
    # Circuit Breakers
    "OPENAI_BREAKER",
    "ANTHROPIC_BREAKER",
    "USDA_BREAKER",
    "with_circuit_breaker",
    # Retry
    "retry_with_backoff",
    "with_retry",
    # Fallback
    "execute_with_fallbacks",
    "FallbackStrategy",
    # Metrics
    "record_circuit_breaker_state",
    "record_api_call",
    "record_api_failure",
    "record_retry",
    "record_fallback",
]
