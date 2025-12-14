"""Database connection management"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from src.config import DATABASE_URL

logger = logging.getLogger(__name__)


class Database:
    """Database connection pool manager"""

    def __init__(self, connection_string: str = DATABASE_URL):
        self.connection_string = connection_string
        self._pool: Optional[AsyncConnectionPool] = None

    async def init_pool(self) -> None:
        """Initialize connection pool"""
        logger.info("Initializing database connection pool")
        self._pool = AsyncConnectionPool(
            self.connection_string,
            min_size=2,
            max_size=10,
            open=True
        )

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


# Global database instance
db = Database()
