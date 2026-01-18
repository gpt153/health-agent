"""Fallback strategies for API failures

Provides orchestration for trying multiple strategies in sequence until one succeeds.
Used to implement graceful degradation when primary APIs fail.
"""

import logging
from typing import Any, Callable, List, TypeVar
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class FallbackStrategy:
    """
    Defines a fallback strategy with priority ordering.

    Attributes:
        name: Human-readable name for logging
        handler: Async callable that implements the strategy
        priority: Priority level (lower = higher priority, 1 = primary)
    """
    name: str
    handler: Callable[..., T]
    priority: int


async def execute_with_fallbacks(
    strategies: List[FallbackStrategy],
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Execute strategies in priority order until one succeeds.

    Tries each strategy in turn. If one succeeds, returns immediately.
    If all fail, raises the last exception encountered.

    Args:
        strategies: List of FallbackStrategy to try
        *args, **kwargs: Arguments to pass to each strategy handler

    Returns:
        Result from first successful strategy

    Raises:
        Last exception if all strategies fail

    Example:
        strategies = [
            FallbackStrategy("primary_api", call_primary, priority=1),
            FallbackStrategy("fallback_api", call_fallback, priority=2),
            FallbackStrategy("cache", use_cache, priority=3),
        ]
        result = await execute_with_fallbacks(strategies, query="test")
    """
    # Sort strategies by priority (lower priority number = try first)
    sorted_strategies = sorted(strategies, key=lambda s: s.priority)

    last_exception = None
    primary_api = sorted_strategies[0].name if sorted_strategies else "unknown"

    for strategy in sorted_strategies:
        try:
            logger.info(f"[FALLBACK] Trying strategy: {strategy.name}")

            # Attempt to execute strategy
            result = await strategy.handler(*args, **kwargs)

            # Success!
            logger.info(f"[FALLBACK] Strategy '{strategy.name}' succeeded")

            # Record metrics if not the primary strategy
            if strategy.priority > 1:
                try:
                    from src.resilience.metrics import record_fallback
                    record_fallback(primary_api, strategy.name, success=True)
                except Exception:
                    pass  # Don't fail on metrics errors

            return result

        except Exception as e:
            logger.warning(
                f"[FALLBACK] Strategy '{strategy.name}' failed: "
                f"{type(e).__name__}: {e}"
            )
            last_exception = e

            # Record metrics if not the primary strategy
            if strategy.priority > 1:
                try:
                    from src.resilience.metrics import record_fallback
                    record_fallback(primary_api, strategy.name, success=False)
                except Exception:
                    pass  # Don't fail on metrics errors

            # Continue to next strategy
            continue

    # All strategies failed
    logger.error(
        f"[FALLBACK] All {len(sorted_strategies)} fallback strategies exhausted"
    )

    if last_exception:
        raise last_exception
    raise Exception("All fallback strategies failed")
