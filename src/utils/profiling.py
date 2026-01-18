"""
Performance profiling utilities for the health agent bot.

This module provides decorators and context managers for profiling:
- CPU usage
- Memory usage
- Function execution time
- Database query timing
"""

import functools
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional
import asyncio

logger = logging.getLogger(__name__)

# Try to import optional profiling libraries
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - system metrics will be limited")

try:
    from memory_profiler import profile as memory_profile
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    logger.warning("memory_profiler not available - memory profiling disabled")


class PerformanceTimer:
    """Context manager for timing code blocks with high precision"""

    def __init__(self, name: str, log_threshold_ms: Optional[float] = None):
        """
        Initialize performance timer.

        Args:
            name: Descriptive name for the timed operation
            log_threshold_ms: Only log if duration exceeds this threshold (ms)
        """
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.log_threshold_ms = log_threshold_ms

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        # Only log if threshold not set or exceeded
        if self.log_threshold_ms is None or self.duration_ms >= self.log_threshold_ms:
            logger.info(
                f"⏱️  [{self.name}] took {self.duration_ms:.2f}ms ({self.duration_ms/1000:.2f}s)"
            )


def profile_function(name: Optional[str] = None, log_threshold_ms: Optional[float] = None):
    """
    Decorator to profile function execution time.

    Args:
        name: Optional custom name (defaults to function name)
        log_threshold_ms: Only log if duration exceeds threshold

    Example:
        @profile_function()
        async def my_function():
            await asyncio.sleep(1)
    """
    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with PerformanceTimer(func_name, log_threshold_ms):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with PerformanceTimer(func_name, log_threshold_ms):
                    return func(*args, **kwargs)
            return sync_wrapper

    return decorator


@asynccontextmanager
async def profile_query(query_name: str, threshold_ms: float = 100.0):
    """
    Async context manager for profiling database queries.

    Args:
        query_name: Descriptive name for the query
        threshold_ms: Log warning if query exceeds this duration

    Example:
        async with profile_query("get_user_preferences", threshold_ms=50):
            results = await db.execute(query)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000

        if duration_ms > threshold_ms:
            logger.warning(
                f"🐌 Slow query '{query_name}': {duration_ms:.2f}ms "
                f"(threshold: {threshold_ms:.2f}ms)"
            )
        else:
            logger.debug(f"Query '{query_name}': {duration_ms:.2f}ms")


class SystemMetrics:
    """Collect system-level performance metrics"""

    @staticmethod
    def get_memory_usage_mb() -> float:
        """Get current process memory usage in MB"""
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return 0.0

    @staticmethod
    def get_cpu_percent(interval: float = 0.1) -> float:
        """Get CPU usage percentage"""
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            return psutil.cpu_percent(interval=interval)
        except Exception as e:
            logger.error(f"Failed to get CPU usage: {e}")
            return 0.0

    @staticmethod
    def get_cpu_count() -> int:
        """Get number of CPU cores"""
        if not PSUTIL_AVAILABLE:
            import os
            return os.cpu_count() or 2

        try:
            return psutil.cpu_count(logical=True) or 2
        except Exception as e:
            logger.error(f"Failed to get CPU count: {e}")
            import os
            return os.cpu_count() or 2

    @staticmethod
    def get_snapshot() -> dict[str, Any]:
        """Get comprehensive system metrics snapshot"""
        return {
            "memory_mb": SystemMetrics.get_memory_usage_mb(),
            "cpu_percent": SystemMetrics.get_cpu_percent(),
            "cpu_count": SystemMetrics.get_cpu_count(),
            "timestamp": time.time(),
        }


class PerformanceMonitor:
    """
    Monitor performance metrics over time.

    Useful for tracking trends during load testing.
    """

    def __init__(self, name: str):
        self.name = name
        self.samples: list[dict[str, Any]] = []
        self.start_time = time.time()

    def record_sample(self, **metrics: Any):
        """Record a performance sample with arbitrary metrics"""
        sample = {
            "timestamp": time.time() - self.start_time,
            **metrics
        }
        self.samples.append(sample)

    def get_average(self, metric: str) -> Optional[float]:
        """Calculate average value for a metric"""
        values = [s[metric] for s in self.samples if metric in s]
        if not values:
            return None
        return sum(values) / len(values)

    def get_percentile(self, metric: str, percentile: float) -> Optional[float]:
        """
        Calculate percentile for a metric.

        Args:
            metric: Metric name
            percentile: Percentile to calculate (0-100)
        """
        values = sorted([s[metric] for s in self.samples if metric in s])
        if not values:
            return None

        index = int(len(values) * (percentile / 100))
        index = min(index, len(values) - 1)
        return values[index]

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics for all metrics"""
        if not self.samples:
            return {}

        # Extract all unique metric names
        metric_names = set()
        for sample in self.samples:
            metric_names.update(k for k in sample.keys() if k != "timestamp")

        summary = {
            "name": self.name,
            "sample_count": len(self.samples),
            "duration_seconds": time.time() - self.start_time,
            "metrics": {}
        }

        for metric in metric_names:
            values = [s[metric] for s in self.samples if metric in s]
            if values and all(isinstance(v, (int, float)) for v in values):
                summary["metrics"][metric] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p50": self.get_percentile(metric, 50),
                    "p95": self.get_percentile(metric, 95),
                    "p99": self.get_percentile(metric, 99),
                }

        return summary


def log_slow_operation(threshold_seconds: float = 2.0):
    """
    Decorator to log operations that exceed a time threshold.

    Args:
        threshold_seconds: Log warning if operation exceeds this duration

    Example:
        @log_slow_operation(threshold_seconds=1.0)
        async def process_image(image_data):
            ...
    """
    def decorator(func: Callable) -> Callable:
        func_name = func.__name__
        threshold_ms = threshold_seconds * 1000

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.perf_counter() - start) * 1000
                    if duration_ms > threshold_ms:
                        logger.warning(
                            f"⚠️  Slow operation '{func_name}': {duration_ms:.2f}ms "
                            f"(threshold: {threshold_ms:.2f}ms)"
                        )
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.perf_counter() - start) * 1000
                    if duration_ms > threshold_ms:
                        logger.warning(
                            f"⚠️  Slow operation '{func_name}': {duration_ms:.2f}ms "
                            f"(threshold: {threshold_ms:.2f}ms)"
                        )
            return sync_wrapper

    return decorator
