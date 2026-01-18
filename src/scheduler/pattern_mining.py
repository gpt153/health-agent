"""
Pattern Mining Background Job Scheduler
Epic 009 - Phase 6: Pattern Detection Engine

This module schedules and executes nightly pattern mining jobs for all users.
Jobs run at 3 AM user local time to analyze the last 90 days of health events
and discover new patterns.

Key Features:
- Nightly job scheduling at 3 AM user local time
- Pattern discovery workflow (all 5 algorithms)
- Pattern confidence updates for existing patterns
- Pattern archival for invalidated patterns
- Job status logging and error handling
"""

import logging
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
from telegram.ext import Application, ContextTypes

from src.services.pattern_detection import (
    detect_temporal_correlations,
    detect_multifactor_patterns,
    detect_behavioral_sequences,
    detect_cyclical_patterns,
    EventFilter,
    calculate_impact_score,
    generate_actionable_insight,
    save_pattern_to_database,
    get_user_patterns,
    evaluate_pattern_against_new_events,
    update_pattern_confidence
)
from src.services.health_events import get_health_events
from src.db.connection import db

logger = logging.getLogger(__name__)

# Pattern mining configuration
ANALYSIS_PERIOD_DAYS = 90  # Analyze last 90 days
MIN_PATTERN_OCCURRENCES = 10  # Minimum occurrences for pattern validity
PATTERN_CONFIDENCE_THRESHOLD = 0.50  # Archive patterns below this confidence


class PatternMiningScheduler:
    """
    Manages nightly pattern mining job scheduling and execution.
    """

    def __init__(self, application: Application):
        self.application = application
        self.job_queue = application.job_queue

    async def schedule_pattern_mining(self) -> None:
        """
        Schedule daily pattern mining jobs for all users at 3 AM their local time.

        This is called once during application startup.
        """
        logger.info("Scheduling pattern mining jobs for all users...")

        try:
            # Get all active users with their timezones
            users = await self._get_all_active_users()

            scheduled_count = 0
            for user in users:
                user_id = user["telegram_id"]
                user_timezone = user.get("timezone", "UTC")

                try:
                    # Schedule daily job at 3 AM user local time
                    tz = ZoneInfo(user_timezone)
                    scheduled_time = time(hour=3, minute=0, tzinfo=tz)

                    self.job_queue.run_daily(
                        callback=self._run_nightly_pattern_mining,
                        time=scheduled_time,
                        data={"user_id": user_id},
                        name=f"pattern_mining_{user_id}"
                    )

                    scheduled_count += 1
                    logger.debug(f"Scheduled pattern mining for user {user_id} at 3 AM {user_timezone}")

                except Exception as e:
                    logger.error(f"Failed to schedule pattern mining for user {user_id}: {e}")
                    continue

            logger.info(f"Successfully scheduled pattern mining for {scheduled_count} users")

        except Exception as e:
            logger.error(f"Failed to schedule pattern mining jobs: {e}", exc_info=True)

    async def _get_all_active_users(self) -> List[Dict[str, Any]]:
        """
        Get all active users from the database.

        Returns:
            List of user dictionaries with telegram_id and timezone
        """
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT telegram_id, timezone
                    FROM users
                    WHERE is_active = TRUE
                    ORDER BY telegram_id
                    """
                )
                rows = await cur.fetchall()
                return [dict(row) for row in rows]

    async def _run_nightly_pattern_mining(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Nightly pattern mining job callback.

        Workflow:
        1. Fetch health_events from last 90 days
        2. Run all 5 pattern detection algorithms
        3. Save new patterns to discovered_patterns table
        4. Update confidence of existing patterns
        5. Archive patterns that no longer hold
        6. Log summary statistics

        Args:
            context: Telegram job context with user_id in context.job.data
        """
        user_id = context.job.data["user_id"]
        start_time = datetime.now()

        logger.info(f"Starting pattern mining for user {user_id}")

        try:
            # Calculate date range (last 90 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=ANALYSIS_PERIOD_DAYS)

            # Fetch health events
            events = await get_health_events(user_id, start_date, end_date)

            if len(events) < 50:
                logger.info(f"User {user_id} has only {len(events)} events, skipping pattern mining")
                return

            logger.info(f"Mining patterns from {len(events)} events for user {user_id}")

            # ================================================================
            # Phase 1: Discover New Patterns
            # ================================================================

            new_patterns_discovered = []

            # Algorithm 1: Temporal Correlations (food → symptom)
            temporal_patterns = await detect_temporal_correlations(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                trigger_event_type="meal",
                outcome_event_type="symptom",
                time_window_hours=(1, 48),
                min_occurrences=MIN_PATTERN_OCCURRENCES
            )
            new_patterns_discovered.extend(temporal_patterns)

            # Also check exercise → sleep correlations
            exercise_sleep_patterns = await detect_temporal_correlations(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                trigger_event_type="exercise",
                outcome_event_type="sleep",
                time_window_hours=(4, 12),
                min_occurrences=MIN_PATTERN_OCCURRENCES
            )
            new_patterns_discovered.extend(exercise_sleep_patterns)

            # Algorithm 3: Behavioral Sequences
            sequence_patterns = await detect_behavioral_sequences(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                min_sequence_length=2,
                max_sequence_length=4,
                max_hours_between_events=24,
                min_occurrences=5
            )
            new_patterns_discovered.extend(sequence_patterns)

            # Algorithm 4: Cyclical Patterns
            cyclical_patterns = await detect_cyclical_patterns(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                cycle_types=["weekly"],
                min_occurrences=4
            )
            new_patterns_discovered.extend(cyclical_patterns)

            # Save new patterns to database
            saved_count = 0
            for pattern in new_patterns_discovered:
                try:
                    # Calculate impact score
                    impact_score = calculate_impact_score(pattern)

                    # Generate actionable insight
                    insight = generate_actionable_insight(pattern, impact_score)

                    # Save to database
                    pattern_id = await save_pattern_to_database(
                        pattern=pattern,
                        user_id=user_id,
                        impact_score=impact_score,
                        actionable_insight=insight
                    )

                    saved_count += 1
                    logger.debug(f"Saved new pattern {pattern_id} for user {user_id}")

                except Exception as e:
                    logger.error(f"Failed to save pattern for user {user_id}: {e}")
                    continue

            # ================================================================
            # Phase 2: Update Existing Pattern Confidence
            # ================================================================

            # Get existing patterns for this user
            existing_patterns = await get_user_patterns(
                user_id=user_id,
                min_confidence=0.30,  # Include patterns close to archival threshold
                include_archived=False
            )

            updated_count = 0
            archived_count = 0

            # Get recent events (last 7 days) for evidence evaluation
            recent_events = await get_health_events(
                user_id=user_id,
                start_date=end_date - timedelta(days=7),
                end_date=end_date
            )

            for pattern in existing_patterns:
                try:
                    pattern_id = pattern["id"]

                    # Evaluate pattern against recent events
                    evidence_list = await evaluate_pattern_against_new_events(
                        pattern_id=pattern_id,
                        new_events=recent_events
                    )

                    # Update confidence based on evidence
                    for evidence in evidence_list:
                        update_result = await update_pattern_confidence(
                            pattern_id=pattern_id,
                            new_evidence=evidence
                        )

                        updated_count += 1

                        # Check if pattern was archived
                        if update_result["new_confidence"] < PATTERN_CONFIDENCE_THRESHOLD:
                            archived_count += 1

                except Exception as e:
                    logger.error(f"Failed to update pattern {pattern.get('id')} for user {user_id}: {e}")
                    continue

            # ================================================================
            # Job Summary
            # ================================================================

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Pattern mining completed for user {user_id} in {duration:.1f}s - "
                f"New patterns: {saved_count}, Updated: {updated_count}, Archived: {archived_count}"
            )

        except Exception as e:
            logger.error(f"Pattern mining failed for user {user_id}: {e}", exc_info=True)


# ================================================================
# Manual Pattern Mining Trigger (for testing/debugging)
# ================================================================

async def run_pattern_mining_now(user_id: str) -> Dict[str, Any]:
    """
    Trigger pattern mining immediately for a specific user (for testing).

    Args:
        user_id: User's telegram ID

    Returns:
        Summary dictionary with mining results

    Example:
        >>> result = await run_pattern_mining_now("123456789")
        >>> print(f"Discovered {result['new_patterns']} patterns")
    """
    start_time = datetime.now()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=ANALYSIS_PERIOD_DAYS)

    # Fetch events
    events = await get_health_events(user_id, start_date, end_date)

    # Run discovery
    new_patterns = []

    temporal_patterns = await detect_temporal_correlations(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        trigger_event_type="meal",
        outcome_event_type="symptom",
        time_window_hours=(1, 48),
        min_occurrences=MIN_PATTERN_OCCURRENCES
    )
    new_patterns.extend(temporal_patterns)

    sequence_patterns = await detect_behavioral_sequences(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        min_sequence_length=2,
        max_sequence_length=4,
        max_hours_between_events=24,
        min_occurrences=5
    )
    new_patterns.extend(sequence_patterns)

    cyclical_patterns = await detect_cyclical_patterns(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        cycle_types=["weekly"],
        min_occurrences=4
    )
    new_patterns.extend(cyclical_patterns)

    # Save patterns
    saved_count = 0
    for pattern in new_patterns:
        try:
            impact_score = calculate_impact_score(pattern)
            insight = generate_actionable_insight(pattern, impact_score)
            await save_pattern_to_database(pattern, user_id, impact_score, insight)
            saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save pattern: {e}")

    duration = (datetime.now() - start_time).total_seconds()

    return {
        "user_id": user_id,
        "events_analyzed": len(events),
        "new_patterns": saved_count,
        "duration_seconds": round(duration, 2),
        "analysis_period_days": ANALYSIS_PERIOD_DAYS
    }
