"""
Background metrics collector for gauge metrics.

This module provides a background task that periodically updates gauge metrics
that require database queries or system resource checks.

Metrics updated:
- active_users: Users active in last hour/day/week
- db_connections_active: Active database connections
- db_pool_size: Connection pool statistics
- memory_entries_total: Semantic memory entry counts
- gamification_streaks_active: Active user streaks
"""

import logging
import asyncio
from datetime import datetime, timedelta

from src.observability.metrics import (
    active_users,
    db_connections_active,
    db_pool_size,
    memory_entries_total,
    gamification_streaks_active,
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Background task to collect gauge metrics.

    Runs periodically to update metrics that require database queries
    or system introspection.
    """

    def __init__(self, collection_interval: int = 60):
        """
        Initialize metrics collector.

        Args:
            collection_interval: How often to collect metrics (in seconds)
        """
        self.collection_interval = collection_interval
        self._running = False
        self._task = None

    async def start(self):
        """Start the background metrics collection task."""
        if self._running:
            logger.warning("Metrics collector is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info(
            f"Metrics collector started (interval: {self.collection_interval}s)"
        )

    async def stop(self):
        """Stop the background metrics collection task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Metrics collector stopped")

    async def _collection_loop(self):
        """Main collection loop."""
        while self._running:
            try:
                await self._collect_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}", exc_info=True)

            # Wait for next collection interval
            await asyncio.sleep(self.collection_interval)

    async def _collect_metrics(self):
        """Collect all gauge metrics."""
        try:
            # Collect in parallel for efficiency
            await asyncio.gather(
                self._collect_active_users(),
                self._collect_database_metrics(),
                self._collect_memory_metrics(),
                self._collect_gamification_metrics(),
                return_exceptions=True,  # Don't let one failure stop others
            )
        except Exception as e:
            logger.error(f"Error in metrics collection: {e}", exc_info=True)

    async def _collect_active_users(self):
        """Collect active user metrics."""
        try:
            from src.db.connection import db

            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            one_day_ago = now - timedelta(days=1)
            one_week_ago = now - timedelta(days=7)

            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Users active in last hour
                    await cur.execute(
                        """
                        SELECT COUNT(DISTINCT user_id)
                        FROM conversation_history
                        WHERE timestamp > %s
                        """,
                        (one_hour_ago,),
                    )
                    result = await cur.fetchone()
                    active_users.labels(time_period="last_hour").set(
                        result[0] if result else 0
                    )

                    # Users active in last day
                    await cur.execute(
                        """
                        SELECT COUNT(DISTINCT user_id)
                        FROM conversation_history
                        WHERE timestamp > %s
                        """,
                        (one_day_ago,),
                    )
                    result = await cur.fetchone()
                    active_users.labels(time_period="last_day").set(
                        result[0] if result else 0
                    )

                    # Users active in last week
                    await cur.execute(
                        """
                        SELECT COUNT(DISTINCT user_id)
                        FROM conversation_history
                        WHERE timestamp > %s
                        """,
                        (one_week_ago,),
                    )
                    result = await cur.fetchone()
                    active_users.labels(time_period="last_week").set(
                        result[0] if result else 0
                    )

        except Exception as e:
            logger.error(f"Error collecting active user metrics: {e}")

    async def _collect_database_metrics(self):
        """Collect database connection pool metrics."""
        try:
            from src.db.connection import db

            if not db.pool:
                return

            # Get pool statistics
            pool_stats = db.pool.get_stats()

            # Total connections
            total = pool_stats.get("pool_size", 0)
            db_pool_size.labels(state="total").set(total)

            # Available connections
            available = pool_stats.get("pool_available", 0)
            db_pool_size.labels(state="available").set(available)

            # In-use connections
            in_use = total - available
            db_pool_size.labels(state="in_use").set(in_use)

            # Active connections (same as in_use for now)
            db_connections_active.set(in_use)

        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")

    async def _collect_memory_metrics(self):
        """Collect semantic memory metrics."""
        try:
            from src.db.connection import db

            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Count memory entries (if table exists)
                    await cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.tables
                        WHERE table_name = 'memories'
                        """
                    )
                    result = await cur.fetchone()

                    if result and result[0] > 0:
                        # Table exists, count entries
                        await cur.execute("SELECT COUNT(*) FROM memories")
                        result = await cur.fetchone()
                        memory_entries_total.labels(
                            memory_type="total"
                        ).set(result[0] if result else 0)

        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")

    async def _collect_gamification_metrics(self):
        """Collect gamification metrics."""
        try:
            from src.db.connection import db

            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Check if gamification tables exist
                    await cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.tables
                        WHERE table_name IN ('user_streaks', 'user_xp')
                        """
                    )
                    result = await cur.fetchone()

                    if result and result[0] >= 1:
                        # Count active streaks by type
                        await cur.execute(
                            """
                            SELECT streak_type, COUNT(*)
                            FROM user_streaks
                            WHERE current_streak > 0
                            GROUP BY streak_type
                            """
                        )
                        results = await cur.fetchall()

                        for streak_type, count in results:
                            gamification_streaks_active.labels(
                                streak_type=streak_type
                            ).set(count)

        except Exception as e:
            logger.error(f"Error collecting gamification metrics: {e}")


# Global metrics collector instance
_metrics_collector = None


async def start_metrics_collector(interval: int = 60):
    """
    Start the global metrics collector.

    Args:
        interval: Collection interval in seconds (default: 60)

    Example:
        >>> await start_metrics_collector(interval=30)
    """
    global _metrics_collector

    from src.config import ENABLE_METRICS

    if not ENABLE_METRICS:
        logger.info("Metrics collection is disabled (ENABLE_METRICS=false)")
        return

    if _metrics_collector is not None:
        logger.warning("Metrics collector already started")
        return

    _metrics_collector = MetricsCollector(collection_interval=interval)
    await _metrics_collector.start()


async def stop_metrics_collector():
    """
    Stop the global metrics collector.

    Example:
        >>> await stop_metrics_collector()
    """
    global _metrics_collector

    if _metrics_collector is None:
        return

    await _metrics_collector.stop()
    _metrics_collector = None
