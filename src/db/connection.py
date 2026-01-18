"""Database connection management with dynamic pool sizing"""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from src.config import DATABASE_URL, ENABLE_PROMETHEUS
from src.exceptions import ConnectionError as DBConnectionError, wrap_external_exception

logger = logging.getLogger(__name__)


def calculate_pool_size() -> tuple[int, int]:
    """
    Calculate optimal connection pool size based on CPU cores.

    Formula: pool_size = (2 * cpu_cores) + spare_connections

    Returns:
        Tuple of (min_size, max_size)
    """
    cpu_count = os.cpu_count() or 2  # Fallback to 2 if detection fails

    # Formula from PostgreSQL best practices
    min_size = cpu_count
    max_size = (2 * cpu_count) + 5  # 2x cores + 5 spare connections

    logger.info(f"Detected {cpu_count} CPU cores")
    logger.info(f"Calculated pool size: min={min_size}, max={max_size}")

    return min_size, max_size


class Database:
    """Database connection pool manager with dynamic sizing"""

    def __init__(self, connection_string: str = DATABASE_URL):
        self.connection_string = connection_string
        self._pool: Optional[AsyncConnectionPool] = None

    async def init_pool(self) -> None:
        """Initialize connection pool with dynamic sizing"""
        try:
            min_size, max_size = calculate_pool_size()

            logger.info(f"Initializing database connection pool (min={min_size}, max={max_size})")
            self._pool = AsyncConnectionPool(
                self.connection_string,
                min_size=min_size,
                max_size=max_size,
                open=False
            )
            await self._pool.open()
            logger.info("✅ Database connection pool initialized")
        except psycopg.OperationalError as e:
            raise DBConnectionError(
                message=f"Failed to initialize database pool: {str(e)}",
                operation="init_pool",
                cause=e
            )
        except Exception as e:
            raise wrap_external_exception(
                e,
                operation="init_pool"
            )

    async def close_pool(self) -> None:
        """Close connection pool"""
        if self._pool:
            try:
                logger.info("Closing database connection pool")
                await self._pool.close()
            except Exception as e:
                logger.error(f"Error closing database pool: {e}", exc_info=True)
                # Don't raise on close, just log

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[psycopg.AsyncConnection, None]:
        """Get database connection from pool"""
        if not self._pool:
            raise DBConnectionError(
                message="Database pool not initialized. Call init_pool() first.",
                operation="get_connection"
            )

        # Update pool metrics
        if ENABLE_PROMETHEUS:
            try:
                from src.monitoring import update_pool_metrics
                pool_stats = self._pool.get_stats()
                update_pool_metrics(
                    total=pool_stats.get('pool_size', 0),
                    available=pool_stats.get('pool_available', 0)
                )
            except Exception as e:
                logger.debug(f"Failed to update pool metrics: {e}")

        try:
            async with self._pool.connection() as conn:
                conn.row_factory = dict_row
                yield conn
        except psycopg.OperationalError as e:
            raise DBConnectionError(
                message=f"Failed to get database connection: {str(e)}",
                operation="get_connection",
                cause=e
            )
        except Exception as e:
            raise wrap_external_exception(
                e,
                operation="get_connection"
            )

    def get_pool_stats(self) -> dict:
        """
        Get connection pool statistics.

        Returns:
            Dictionary with pool size, available connections, etc.
        """
        if not self._pool:
            return {"error": "Pool not initialized"}

        try:
            return {
                "size": self._pool.size,
                "available": self._pool.available,
                "active": self._pool.size - self._pool.available,
                "min_size": self._pool.min_size,
                "max_size": self._pool.max_size,
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {"error": str(e)}

    def log_pool_stats(self) -> None:
        """Log current pool statistics"""
        stats = self.get_pool_stats()
        if "error" not in stats:
            logger.info(
                f"DB Pool: {stats['active']}/{stats['size']} active "
                f"({stats['available']} available, max={stats['max_size']})"
            )


# Global database instance
db = Database()
