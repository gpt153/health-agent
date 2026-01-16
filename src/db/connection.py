"""Database connection management"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from src.config import DATABASE_URL
from src.exceptions import ConnectionError as DBConnectionError, wrap_external_exception

logger = logging.getLogger(__name__)


class Database:
    """Database connection pool manager"""

    def __init__(self, connection_string: str = DATABASE_URL):
        self.connection_string = connection_string
        self._pool: Optional[AsyncConnectionPool] = None

    async def init_pool(self) -> None:
        """Initialize connection pool"""
        try:
            logger.info("Initializing database connection pool")
            self._pool = AsyncConnectionPool(
                self.connection_string,
                min_size=2,
                max_size=10,
                open=False
            )
            await self._pool.open()
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


# Global database instance
db = Database()
