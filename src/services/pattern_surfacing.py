"""
Pattern Surfacing Service
Epic 009 - Phase 7: Integration & Agent Tools

Intelligently surfaces health patterns in agent conversations based on:
- Context awareness (what user is discussing)
- Relevance scoring (how applicable is the pattern right now)
- Timing (when to show insights naturally)
- User preferences (frequency, notification settings)

This ensures patterns feel helpful and natural, not intrusive.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.services.pattern_detection import get_user_patterns
from src.services.health_events import get_health_events
from src.db.connection import db

logger = logging.getLogger(__name__)


@dataclass
class SurfacingContext:
    """Context for pattern surfacing decisions"""
    user_id: str
    current_message: str
    recent_events: List[Dict[str, Any]]  # Last 24h events
    conversation_history: List[str]  # Recent messages
    time_of_day: int  # Hour 0-23
    day_of_week: int  # 0=Monday, 6=Sunday


@dataclass
class SurfacingDecision:
    """Decision whether to surface a pattern"""
    should_surface: bool
    pattern_id: Optional[int]
    relevance_score: float
    timing: str  # "immediate", "deferred", "suppress"
    reason: str


# Surfacing rules by pattern type
SURFACING_RULES = {
    "temporal_correlation": {
        "triggers": [
            "user_asks_why",           # "Why am I tired?"
            "symptom_mentioned",        # "I have a headache"
            "trigger_event_logged",     # User just logged pasta meal
            "user_asks_prediction"      # "Will I feel good?"
        ],
        "timing": "immediate",
        "max_frequency_days": 1,  # Max once per day
        "min_relevance": 60.0
    },
    "multifactor_pattern": {
        "triggers": [
            "all_factors_present",      # All pattern factors occurred today
            "user_asks_prediction",     # "Will I feel good today?"
            "user_asks_advice"          # "What should I do?"
        ],
        "timing": "deferred",           # Wait for natural break
        "max_frequency_days": 3,  # Max twice per week
        "min_relevance": 65.0
    },
    "behavioral_sequence": {
        "triggers": [
            "sequence_in_progress",     # User is in middle of sequence
            "user_asks_advice",         # "What should I do?"
            "pattern_completing"        # Sequence about to complete
        ],
        "timing": "immediate",
        "max_frequency_days": 2,  # Max 3x per week
        "min_relevance": 70.0
    },
    "cyclical_pattern": {
        "triggers": [
            "cycle_phase_match",        # Current day matches cycle
            "user_asks_prediction"      # "What's coming?"
        ],
        "timing": "deferred",
        "max_frequency_days": 7,  # Max once per week
        "min_relevance": 65.0
    }
}


class PatternSurfacingService:
    """
    Service for intelligently surfacing patterns in conversations

    Features:
    - Context-aware triggering (only show when relevant)
    - Relevance scoring (prioritize most applicable patterns)
    - Frequency limiting (avoid pattern fatigue)
    - Timing optimization (immediate vs deferred)
    """

    def __init__(self) -> None:
        """Initialize pattern surfacing service"""
        pass

    async def should_surface_pattern(
        self,
        context: SurfacingContext,
        pattern: Dict[str, Any]
    ) -> SurfacingDecision:
        """
        Determine if a pattern should be surfaced now

        Args:
            context: Current conversation context
            pattern: Pattern to evaluate

        Returns:
            SurfacingDecision with recommendation

        Example:
            >>> context = SurfacingContext(
            ...     user_id="123",
            ...     current_message="Why am I so tired today?",
            ...     recent_events=[...],
            ...     conversation_history=[...],
            ...     time_of_day=14,
            ...     day_of_week=2
            ... )
            >>> decision = await service.should_surface_pattern(context, pattern)
            >>> if decision.should_surface:
            ...     print(f"Surface pattern (score: {decision.relevance_score})")
        """
        pattern_id = pattern['id']
        pattern_type = pattern['pattern_type']

        # Get surfacing rules for this pattern type
        rules = SURFACING_RULES.get(pattern_type, {})
        if not rules:
            return SurfacingDecision(
                should_surface=False,
                pattern_id=pattern_id,
                relevance_score=0.0,
                timing="suppress",
                reason=f"No surfacing rules for type: {pattern_type}"
            )

        # 1. Check frequency limit
        frequency_ok, freq_reason = await self._check_frequency_limit(
            context.user_id,
            pattern_id,
            rules["max_frequency_days"]
        )
        if not frequency_ok:
            return SurfacingDecision(
                should_surface=False,
                pattern_id=pattern_id,
                relevance_score=0.0,
                timing="suppress",
                reason=freq_reason
            )

        # 2. Calculate relevance score
        relevance_score = await self._calculate_relevance(
            context,
            pattern
        )

        # Check minimum relevance threshold
        min_relevance = rules.get("min_relevance", 60.0)
        if relevance_score < min_relevance:
            return SurfacingDecision(
                should_surface=False,
                pattern_id=pattern_id,
                relevance_score=relevance_score,
                timing="suppress",
                reason=f"Relevance {relevance_score:.1f} below threshold {min_relevance}"
            )

        # 3. Check triggers
        trigger_matched = self._check_triggers(
            context,
            pattern,
            rules["triggers"]
        )

        if not trigger_matched:
            return SurfacingDecision(
                should_surface=False,
                pattern_id=pattern_id,
                relevance_score=relevance_score,
                timing="suppress",
                reason="No trigger conditions matched"
            )

        # All checks passed - recommend surfacing
        return SurfacingDecision(
            should_surface=True,
            pattern_id=pattern_id,
            relevance_score=relevance_score,
            timing=rules["timing"],
            reason=f"High relevance ({relevance_score:.1f}), trigger matched"
        )

    async def find_surfaceable_patterns(
        self,
        context: SurfacingContext,
        limit: int = 3
    ) -> List[Tuple[Dict[str, Any], SurfacingDecision]]:
        """
        Find all patterns that should be surfaced now

        Args:
            context: Current conversation context
            limit: Maximum patterns to surface (default: 3)

        Returns:
            List of (pattern, decision) tuples sorted by relevance
        """
        # Get high-quality patterns for user
        patterns = await get_user_patterns(
            user_id=context.user_id,
            min_confidence=0.70,
            min_impact=50.0,
            include_archived=False
        )

        # Evaluate each pattern
        surfaceable = []
        for pattern in patterns:
            decision = await self.should_surface_pattern(context, pattern)
            if decision.should_surface:
                surfaceable.append((pattern, decision))

        # Sort by relevance score
        surfaceable.sort(key=lambda x: x[1].relevance_score, reverse=True)

        # Return top N
        return surfaceable[:limit]

    async def _check_frequency_limit(
        self,
        user_id: str,
        pattern_id: int,
        max_frequency_days: int
    ) -> Tuple[bool, str]:
        """
        Check if pattern was surfaced too recently

        Args:
            user_id: User ID
            pattern_id: Pattern to check
            max_frequency_days: Minimum days between surfacing

        Returns:
            (passes_check, reason)
        """
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Check last time pattern was surfaced
                    await cur.execute(
                        """
                        SELECT
                            metadata->>'last_surfaced' as last_surfaced
                        FROM discovered_patterns
                        WHERE id = %s AND user_id = %s
                        """,
                        (pattern_id, user_id)
                    )
                    row = await cur.fetchone()

                    if not row or not row['last_surfaced']:
                        # Never surfaced before
                        return (True, "Never surfaced before")

                    last_surfaced = datetime.fromisoformat(row['last_surfaced'])
                    days_since = (datetime.now() - last_surfaced).days

                    if days_since < max_frequency_days:
                        return (
                            False,
                            f"Surfaced {days_since} days ago (limit: {max_frequency_days} days)"
                        )

                    return (True, f"Last surfaced {days_since} days ago")

        except Exception as e:
            logger.error(f"Frequency check failed: {e}")
            # Default to allowing if check fails
            return (True, "Frequency check failed, allowing")

    async def _calculate_relevance(
        self,
        context: SurfacingContext,
        pattern: Dict[str, Any]
    ) -> float:
        """
        Calculate pattern relevance to current context

        Scoring factors:
        - Semantic match (30 points): Keywords in message match pattern
        - Temporal match (30 points): Current time matches pattern timing
        - Contextual match (25 points): Recent events match pattern triggers
        - Recency (10 points): Pattern observed recently
        - Impact (5 points): High-impact patterns prioritized

        Returns:
            Relevance score 0-100
        """
        relevance = 0.0
        pattern_rule = pattern.get('pattern_rule', {})

        # 1. Semantic match (30 points max)
        semantic_score = self._calculate_semantic_match(
            context.current_message,
            pattern
        )
        relevance += semantic_score * 0.30

        # 2. Temporal match (30 points max)
        temporal_score = self._calculate_temporal_match(
            context,
            pattern
        )
        relevance += temporal_score * 0.30

        # 3. Contextual match (25 points max)
        contextual_score = self._calculate_contextual_match(
            context.recent_events,
            pattern_rule
        )
        relevance += contextual_score * 0.25

        # 4. Recency bonus (10 points max)
        recency_score = self._calculate_recency_score(pattern)
        relevance += recency_score * 0.10

        # 5. Impact bonus (5 points max)
        impact_score = min(pattern.get('impact_score', 0) / 20.0, 5.0)
        relevance += impact_score * 0.05

        return min(relevance, 100.0)

    def _calculate_semantic_match(
        self,
        message: str,
        pattern: Dict[str, Any]
    ) -> float:
        """Calculate semantic match between message and pattern (0-100)"""
        message_lower = message.lower()
        insight = pattern.get('actionable_insight', '').lower()
        pattern_rule = pattern.get('pattern_rule', {})

        # Extract keywords from message
        message_words = set(message_lower.split())

        # Extract keywords from pattern
        pattern_keywords = set()

        # Add words from insight
        pattern_keywords.update(insight.split())

        # Add characteristic keywords
        if pattern['pattern_type'] == 'temporal_correlation':
            trigger = pattern_rule.get('trigger', {}).get('characteristic', '')
            outcome = pattern_rule.get('outcome', {}).get('characteristic', '')
            pattern_keywords.update(trigger.lower().split('_'))
            pattern_keywords.update(outcome.lower().split('_'))

        # Calculate overlap
        if not message_words or not pattern_keywords:
            return 0.0

        overlap = len(message_words & pattern_keywords)
        return min((overlap / len(message_words)) * 100, 100.0)

    def _calculate_temporal_match(
        self,
        context: SurfacingContext,
        pattern: Dict[str, Any]
    ) -> float:
        """Calculate temporal match (0-100)"""
        pattern_type = pattern['pattern_type']
        pattern_rule = pattern.get('pattern_rule', {})

        # For temporal correlations, check if we're in the time window
        if pattern_type == 'temporal_correlation':
            time_window = pattern_rule.get('time_window', {})
            # This would require checking recent events
            # Simplified: return 50 for now
            return 50.0

        # For cyclical patterns, check if current day matches
        elif pattern_type == 'cyclical_pattern':
            cycle = pattern_rule.get('cycle', '')
            pattern_detail = pattern_rule.get('pattern', {})

            if cycle == 'weekly':
                day_of_week = pattern_detail.get('day_of_week', '')
                # Map day names to numbers
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                if day_of_week in days and context.day_of_week == days.index(day_of_week):
                    return 100.0

        return 0.0

    def _calculate_contextual_match(
        self,
        recent_events: List[Dict[str, Any]],
        pattern_rule: Dict[str, Any]
    ) -> float:
        """Calculate contextual match based on recent events (0-100)"""
        if not recent_events:
            return 0.0

        # For temporal correlations, check if trigger event occurred
        if 'trigger' in pattern_rule:
            trigger = pattern_rule['trigger']
            trigger_type = trigger.get('event_type')
            trigger_char = trigger.get('characteristic', '')

            # Check if any recent event matches trigger
            for event in recent_events:
                if event.get('event_type') == trigger_type:
                    # Simple match for now
                    return 75.0

        # For multifactor patterns, check if all factors present
        if 'factors' in pattern_rule:
            factors = pattern_rule['factors']
            matched_factors = 0

            for factor in factors:
                factor_type = factor.get('event_type')
                for event in recent_events:
                    if event.get('event_type') == factor_type:
                        matched_factors += 1
                        break

            if len(factors) > 0:
                return (matched_factors / len(factors)) * 100

        return 0.0

    def _calculate_recency_score(self, pattern: Dict[str, Any]) -> float:
        """Calculate recency score (0-100)"""
        updated_at = pattern.get('updated_at')
        if not updated_at:
            return 50.0

        days_since = (datetime.now() - updated_at).days

        if days_since <= 7:
            return 100.0
        elif days_since <= 30:
            return 70.0
        elif days_since <= 90:
            return 40.0
        else:
            return 20.0

    def _check_triggers(
        self,
        context: SurfacingContext,
        pattern: Dict[str, Any],
        trigger_rules: List[str]
    ) -> bool:
        """
        Check if any trigger condition is met

        Trigger types:
        - user_asks_why: Message contains "why", "how come"
        - symptom_mentioned: Message mentions symptom
        - trigger_event_logged: Recent event matches pattern trigger
        - user_asks_prediction: Message asks about future
        - user_asks_advice: Message asks for advice
        """
        message_lower = context.current_message.lower()

        for trigger in trigger_rules:
            if trigger == "user_asks_why":
                if any(word in message_lower for word in ["why", "how come", "reason"]):
                    return True

            elif trigger == "symptom_mentioned":
                symptoms = ["tired", "fatigue", "headache", "pain", "bloat", "nausea", "dizzy"]
                if any(symptom in message_lower for symptom in symptoms):
                    return True

            elif trigger == "user_asks_prediction":
                if any(word in message_lower for word in ["will", "going to", "expect", "predict"]):
                    return True

            elif trigger == "user_asks_advice":
                if any(word in message_lower for word in ["should", "what to", "recommend", "suggest"]):
                    return True

            elif trigger == "trigger_event_logged":
                # Check if recent events match pattern trigger
                pattern_rule = pattern.get('pattern_rule', {})
                if 'trigger' in pattern_rule:
                    trigger_type = pattern_rule['trigger'].get('event_type')
                    if any(e.get('event_type') == trigger_type for e in context.recent_events):
                        return True

        return False

    async def record_pattern_surfaced(
        self,
        user_id: str,
        pattern_id: int
    ) -> None:
        """
        Record that a pattern was surfaced to the user

        Updates pattern metadata with surfacing timestamp
        """
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE discovered_patterns
                        SET metadata = COALESCE(metadata, '{}'::jsonb) ||
                            jsonb_build_object(
                                'last_surfaced', %s,
                                'surface_count', COALESCE((metadata->>'surface_count')::int, 0) + 1
                            )
                        WHERE id = %s AND user_id = %s
                        """,
                        (datetime.now().isoformat(), pattern_id, user_id)
                    )
                    await conn.commit()

                    logger.info(f"Recorded pattern {pattern_id} surfaced to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to record pattern surfaced: {e}")


# Global service instance
_surfacing_service: Optional[PatternSurfacingService] = None


def get_surfacing_service() -> PatternSurfacingService:
    """Get or create the global pattern surfacing service instance"""
    global _surfacing_service

    if _surfacing_service is None:
        _surfacing_service = PatternSurfacingService()

    return _surfacing_service
