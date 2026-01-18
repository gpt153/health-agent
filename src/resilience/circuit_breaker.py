"""Circuit breaker implementation for external APIs

Implements the Circuit Breaker pattern to prevent cascading failures when
external APIs (OpenAI, Anthropic, USDA) experience outages or timeouts.

State Machine:
    CLOSED (normal) → OPEN (failing fast) → HALF_OPEN (testing) → CLOSED/OPEN
"""

import pybreaker
import logging
from typing import Callable, Any, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Listener to log circuit breaker state changes and emit metrics"""

    def state_change(self, cb: pybreaker.CircuitBreaker, old_state: Any, new_state: Any) -> None:
        """Called when circuit breaker changes state"""
        logger.warning(
            f"[CIRCUIT_BREAKER] {cb.name}: {old_state.name} → {new_state.name}"
        )

        # Emit metrics
        try:
            from src.resilience.metrics import record_circuit_breaker_state
            state_name = new_state.name.lower()
            record_circuit_breaker_state(cb.name, state_name)
        except Exception as e:
            logger.error(f"Failed to record circuit breaker state: {e}")

    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception) -> None:
        """Called when circuit breaker records a failure"""
        logger.error(
            f"[CIRCUIT_BREAKER] {cb.name} recorded failure: {type(exc).__name__}: {exc}"
        )

        # Emit metrics
        try:
            from src.resilience.metrics import record_api_failure
            record_api_failure(cb.name, type(exc).__name__)
        except Exception as e:
            logger.error(f"Failed to record API failure: {e}")

    def success(self, cb: pybreaker.CircuitBreaker) -> None:
        """Called when circuit breaker records a success"""
        logger.debug(f"[CIRCUIT_BREAKER] {cb.name} recorded success")


# Create circuit breakers for each external API
# Configuration: 5 failures triggers OPEN, 60s timeout before HALF_OPEN

OPENAI_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="openai_api",
    listeners=[CircuitBreakerListener()]
)

ANTHROPIC_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="anthropic_api",
    listeners=[CircuitBreakerListener()]
)

USDA_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="usda_api",
    listeners=[CircuitBreakerListener()]
)


def with_circuit_breaker(breaker: pybreaker.CircuitBreaker) -> Callable:
    """
    Decorator to wrap async functions with circuit breaker protection.

    When the circuit is OPEN, calls will fail immediately with CircuitBreakerError
    instead of attempting to call the underlying function.

    Args:
        breaker: The circuit breaker instance to use

    Returns:
        Decorator function

    Example:
        @with_circuit_breaker(OPENAI_BREAKER)
        async def call_openai_api():
            # API call here
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                # Call the function through the circuit breaker
                return await breaker.call_async(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError as e:
                logger.warning(
                    f"[CIRCUIT_BREAKER] {breaker.name} is OPEN - failing fast"
                )
                raise
        return wrapper
    return decorator
