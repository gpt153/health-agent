"""Prometheus metrics for resilience patterns

Exposes metrics for circuit breakers, API calls, retries, and fallbacks.
Metrics are exposed on HTTP endpoint for scraping by Prometheus.
"""

import logging
from prometheus_client import Counter, Histogram, Gauge, Enum

logger = logging.getLogger(__name__)

# Circuit breaker state gauge
# Values: closed, open, half_open
circuit_breaker_state = Enum(
    'circuit_breaker_state',
    'Current state of circuit breaker',
    ['api'],
    states=['closed', 'open', 'half_open']
)

# Total API calls counter
# Labels: api (openai/anthropic/usda), status (success/failure/circuit_open)
api_calls_total = Counter(
    'api_calls_total',
    'Total number of API calls',
    ['api', 'status']
)

# API call duration histogram
# Labels: api (openai/anthropic/usda)
api_call_duration = Histogram(
    'api_call_duration_seconds',
    'Duration of API calls in seconds',
    ['api'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float('inf'))
)

# API failures counter
# Labels: api (openai/anthropic/usda), error_type (TimeoutException/RateLimitError/etc)
api_failures_total = Counter(
    'api_failures_total',
    'Total number of API failures',
    ['api', 'error_type']
)

# Retry attempts counter
# Labels: api (openai/anthropic/usda)
api_retries_total = Counter(
    'api_retries_total',
    'Total number of retry attempts',
    ['api']
)

# Fallback executions counter
# Labels: primary_api, fallback_strategy, status (success/failure)
fallback_executions_total = Counter(
    'fallback_executions_total',
    'Total number of fallback strategy executions',
    ['primary_api', 'fallback_strategy', 'status']
)


def record_circuit_breaker_state(api: str, state: str) -> None:
    """
    Record circuit breaker state change.

    Args:
        api: API name (openai_api, anthropic_api, usda_api)
        state: New state (closed, open, half_open)
    """
    try:
        circuit_breaker_state.labels(api=api).state(state)
        logger.debug(f"[METRICS] Circuit breaker {api} state: {state}")
    except Exception as e:
        logger.error(f"Failed to record circuit breaker state: {e}")


def record_api_call(api: str, success: bool, duration: float) -> None:
    """
    Record API call metrics.

    Args:
        api: API name (openai, anthropic, usda)
        success: Whether the call succeeded
        duration: Call duration in seconds
    """
    try:
        status = 'success' if success else 'failure'
        api_calls_total.labels(api=api, status=status).inc()
        api_call_duration.labels(api=api).observe(duration)
        logger.debug(f"[METRICS] API call {api}: {status}, duration: {duration:.2f}s")
    except Exception as e:
        logger.error(f"Failed to record API call metrics: {e}")


def record_api_failure(api: str, error_type: str) -> None:
    """
    Record API failure.

    Args:
        api: API name (openai_api, anthropic_api, usda_api)
        error_type: Exception class name (TimeoutException, RateLimitError, etc)
    """
    try:
        api_failures_total.labels(api=api, error_type=error_type).inc()
        logger.debug(f"[METRICS] API failure {api}: {error_type}")
    except Exception as e:
        logger.error(f"Failed to record API failure: {e}")


def record_retry(api: str) -> None:
    """
    Record retry attempt.

    Args:
        api: API name (openai, anthropic, usda)
    """
    try:
        api_retries_total.labels(api=api).inc()
        logger.debug(f"[METRICS] Retry attempt for {api}")
    except Exception as e:
        logger.error(f"Failed to record retry: {e}")


def record_fallback(primary_api: str, fallback_strategy: str, success: bool) -> None:
    """
    Record fallback strategy execution.

    Args:
        primary_api: Primary API that failed (openai, anthropic, usda)
        fallback_strategy: Fallback strategy used (cache, alternative_api, mock)
        success: Whether the fallback succeeded
    """
    try:
        status = 'success' if success else 'failure'
        fallback_executions_total.labels(
            primary_api=primary_api,
            fallback_strategy=fallback_strategy,
            status=status
        ).inc()
        logger.debug(
            f"[METRICS] Fallback {primary_api} → {fallback_strategy}: {status}"
        )
    except Exception as e:
        logger.error(f"Failed to record fallback: {e}")
