"""Prometheus metrics definitions and helpers"""
import logging
import time
from contextlib import contextmanager
from typing import Optional
from src.config import ENABLE_PROMETHEUS

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """Container for all Prometheus metrics"""

    def __init__(self):
        if not ENABLE_PROMETHEUS:
            logger.info("Prometheus metrics disabled")
            self._enabled = False
            return

        try:
            from prometheus_client import Counter, Histogram, Gauge

            # HTTP Request Metrics
            self.http_requests_total = Counter(
                'http_requests_total',
                'Total HTTP requests',
                ['method', 'endpoint', 'status']
            )

            self.http_request_duration_seconds = Histogram(
                'http_request_duration_seconds',
                'HTTP request latency',
                ['method', 'endpoint'],
                buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
            )

            # Error Metrics
            self.http_errors_total = Counter(
                'http_errors_total',
                'Total HTTP errors',
                ['method', 'endpoint', 'error_type']
            )

            # Database Metrics
            self.db_queries_total = Counter(
                'db_queries_total',
                'Total database queries',
                ['query_type', 'table']
            )

            self.db_query_duration_seconds = Histogram(
                'db_query_duration_seconds',
                'Database query latency',
                ['query_type'],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
            )

            self.db_connection_pool_size = Gauge(
                'db_connection_pool_size',
                'Current database connection pool size'
            )

            self.db_connection_pool_available = Gauge(
                'db_connection_pool_available',
                'Available database connections in pool'
            )

            # Cache Metrics
            self.cache_operations_total = Counter(
                'cache_operations_total',
                'Total cache operations',
                ['operation', 'result']
            )

            self.cache_hit_rate = Gauge(
                'cache_hit_rate',
                'Cache hit rate (0-1)'
            )

            # Agent/AI Metrics
            self.agent_calls_total = Counter(
                'agent_calls_total',
                'Total AI agent calls',
                ['agent_type', 'status']
            )

            self.agent_call_duration_seconds = Histogram(
                'agent_call_duration_seconds',
                'AI agent call latency',
                ['agent_type'],
                buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
            )

            self.agent_tokens_used = Counter(
                'agent_tokens_used_total',
                'Total tokens used by AI agents',
                ['agent_type', 'token_type']
            )

            self._enabled = True
            logger.info("Prometheus metrics initialized")

        except ImportError:
            logger.error("prometheus-client not installed. Install with: pip install prometheus-client")
            self._enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus metrics: {e}", exc_info=True)
            self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if metrics are enabled"""
        return self._enabled


# Global metrics instance
metrics = PrometheusMetrics()


@contextmanager
def track_request(method: str, endpoint: str):
    """Track HTTP request metrics"""
    if not metrics.enabled:
        yield
        return

    start_time = time.time()
    status_code = 500  # Default to error

    try:
        yield
        status_code = 200  # Success if no exception
    except Exception as e:
        # Record error
        metrics.http_errors_total.labels(
            method=method,
            endpoint=endpoint,
            error_type=type(e).__name__
        ).inc()
        raise
    finally:
        # Record request duration and count
        duration = time.time() - start_time
        metrics.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        metrics.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status_code
        ).inc()


@contextmanager
def track_database_query(query_type: str, table: str = ""):
    """Track database query metrics"""
    if not metrics.enabled:
        yield
        return

    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time
        metrics.db_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration)

        metrics.db_queries_total.labels(
            query_type=query_type,
            table=table
        ).inc()


def track_cache_operation(operation: str, hit: bool):
    """Track cache operation"""
    if not metrics.enabled:
        return

    result = "hit" if hit else "miss"
    metrics.cache_operations_total.labels(
        operation=operation,
        result=result
    ).inc()

    # Update hit rate (simplified calculation)
    # In production, you'd want to calculate this over a time window
    try:
        total_ops = metrics.cache_operations_total._metrics
        if total_ops:
            # This is a simplified hit rate calculation
            # For production, consider using a sliding window
            pass
    except Exception as e:
        logger.debug(f"Failed to update cache hit rate: {e}")


@contextmanager
def track_agent_call(agent_type: str):
    """Track agent call metrics"""
    if not metrics.enabled:
        yield
        return

    start_time = time.time()
    status = "error"  # Default to error

    try:
        yield
        status = "success"
    except Exception:
        raise
    finally:
        duration = time.time() - start_time
        metrics.agent_call_duration_seconds.labels(
            agent_type=agent_type
        ).observe(duration)

        metrics.agent_calls_total.labels(
            agent_type=agent_type,
            status=status
        ).inc()


def update_pool_metrics(total: int, available: int):
    """Update database connection pool metrics"""
    if not metrics.enabled:
        return

    try:
        metrics.db_connection_pool_size.set(total)
        metrics.db_connection_pool_available.set(available)
    except Exception as e:
        logger.debug(f"Failed to update pool metrics: {e}")


def track_agent_tokens(agent_type: str, input_tokens: int, output_tokens: int):
    """Track agent token usage"""
    if not metrics.enabled:
        return

    try:
        metrics.agent_tokens_used.labels(
            agent_type=agent_type,
            token_type="input"
        ).inc(input_tokens)

        metrics.agent_tokens_used.labels(
            agent_type=agent_type,
            token_type="output"
        ).inc(output_tokens)
    except Exception as e:
        logger.debug(f"Failed to track agent tokens: {e}")
