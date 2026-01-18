"""Database connection management with dynamic pool sizing"""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from src.config import DATABASE_URL

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

    async def close_pool(self) -> None:
        """Close connection pool"""
        if self._pool:
            logger.info("Closing database connection pool")
            await self._pool.close()

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[psycopg.AsyncConnection, None]:
        """Get database connection from pool"""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")

        async with self._pool.connection() as conn:
            conn.row_factory = dict_row
            yield conn

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
