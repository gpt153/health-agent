"""Retry logic with exponential backoff and jitter

Implements smart retry logic that:
1. Only retries transient errors (timeouts, rate limits, 5xx errors)
2. Uses exponential backoff with jitter to prevent thundering herd
3. Gives up after max retries to avoid infinite loops
"""

import asyncio
import random
import logging
from typing import Callable, Any, TypeVar
from functools import wraps
import httpx

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 30.0  # seconds
JITTER = 0.1  # 10% random jitter


def is_retryable_error(exc: Exception) -> bool:
    """
    Determine if error is transient and should be retried.

    Retryable errors:
    - Network timeouts
    - HTTP 429 (rate limit)
    - HTTP 500/502/503/504 (server errors)
    - API-specific timeout/rate limit errors

    Non-retryable errors:
    - HTTP 400/401/403/404 (client errors)
    - Invalid API keys
    - Malformed requests

    Args:
        exc: The exception to check

    Returns:
        True if error should be retried, False otherwise
    """
    # HTTPX errors
    if isinstance(exc, httpx.HTTPStatusError):
        # Retry on rate limits and server errors
        status_code = exc.response.status_code
        return status_code in [429, 500, 502, 503, 504]

    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout)):
        return True

    # OpenAI-specific errors (check by class name to avoid import)
    exc_class_name = exc.__class__.__name__
    if exc_class_name in ['RateLimitError', 'APITimeoutError', 'InternalServerError']:
        return True

    # Anthropic-specific errors
    if exc_class_name in ['RateLimitError', 'APITimeoutError', 'InternalServerError']:
        return True

    # Default: don't retry unknown errors
    return False


def calculate_backoff(attempt: int) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Formula: delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY) + jitter
    Jitter is random value between -10% and +10% of delay

    Args:
        attempt: The retry attempt number (0-indexed)

    Returns:
        Delay in seconds

    Example:
        Attempt 0: ~1s
        Attempt 1: ~2s
        Attempt 2: ~4s
        Attempt 3: ~8s
    """
    # Exponential backoff
    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)

    # Add jitter to prevent thundering herd
    jitter_amount = random.uniform(-JITTER * delay, JITTER * delay)
    final_delay = delay + jitter_amount

    return max(final_delay, 0.0)  # Ensure non-negative


async def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = MAX_RETRIES,
    **kwargs: Any
) -> T:
    """
    Retry async function with exponential backoff.

    Only retries transient errors. Gives up after max_retries attempts.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts (default: 3)
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result from func

    Raises:
        Last exception if all retries exhausted or non-retryable error

    Example:
        result = await retry_with_backoff(api_call, arg1, arg2, max_retries=3)
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            # Attempt to call the function
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # If this was the last attempt, give up
            if attempt == max_retries:
                logger.error(
                    f"[RETRY] All {max_retries} retries exhausted for {func.__name__}"
                )
                raise

            # Check if error is retryable
            if not is_retryable_error(e):
                logger.warning(
                    f"[RETRY] Non-retryable error for {func.__name__}: "
                    f"{type(e).__name__}: {e}"
                )
                raise

            # Calculate backoff delay
            backoff = calculate_backoff(attempt)

            # Record retry attempt
            try:
                from src.resilience.metrics import record_retry
                # Extract API name from function name or use generic
                api_name = func.__name__.replace('_call_', '').replace('_protected', '')
                record_retry(api_name)
            except Exception:
                pass  # Don't fail on metrics errors

            logger.info(
                f"[RETRY] Attempt {attempt + 1}/{max_retries} for {func.__name__} "
                f"after {backoff:.2f}s (error: {type(e).__name__})"
            )

            # Wait before retrying
            await asyncio.sleep(backoff)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise Exception("Retry logic failed unexpectedly")


def with_retry(max_retries: int = MAX_RETRIES) -> Callable:
    """
    Decorator to add retry logic to async functions.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        Decorator function

    Example:
        @with_retry(max_retries=3)
        async def call_api():
            # API call here
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_with_backoff(func, *args, max_retries=max_retries, **kwargs)
        return wrapper
    return decorator
