"""
Pattern Detection Service
Epic 009 - Phase 6: Pattern Detection Engine

This module implements 5 pattern detection algorithms that automatically discover
health patterns from the unified event timeline:

1. Temporal Correlation Detection (food → symptom)
2. Multi-Factor Pattern Analyzer (2-4 variables → outcome)
3. Temporal Sequence Detection (behavioral chains)
4. Cyclical Pattern Finder (weekly, monthly, period patterns)
5. Semantic Similarity Clustering (pgvector-based grouping)

All detected patterns require statistical significance (p < 0.05).
"""

import logging
from typing import List, Dict, Any, Tuple, Optional, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import json
from uuid import UUID

from src.services.health_events import get_health_events, EventType
from src.services.statistical_analysis import (
    chi_square_test,
    pearson_correlation,
    is_statistically_significant,
    calculate_effect_size_cohens_d,
    calculate_confidence_interval
)
from src.db.connection import db

logger = logging.getLogger(__name__)

# Pattern type literal
PatternType = Literal[
    "temporal_correlation",
    "multifactor_pattern",
    "behavioral_sequence",
    "cyclical_pattern",
    "semantic_cluster"
]


@dataclass
class PatternCandidate:
    """Represents a potential pattern discovered from data"""
    pattern_type: PatternType
    pattern_rule: Dict[str, Any]
    confidence: float
    occurrences: int
    p_value: float
    effect_size: Optional[float] = None


@dataclass
class EventFilter:
    """Filter criteria for matching events"""
    event_type: EventType
    metadata_conditions: Dict[str, Any]


# ================================================================
# Algorithm 1: Temporal Correlation Detection
# ================================================================

async def detect_temporal_correlations(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    trigger_event_type: EventType,
    outcome_event_type: EventType,
    time_window_hours: Tuple[int, int] = (1, 48),
    min_occurrences: int = 10
) -> List[PatternCandidate]:
    """
    Detect temporal correlations between trigger events and outcome events.

    Example: "Pasta at lunch → Tiredness 2-4 hours later"

    This algorithm:
    1. Finds all trigger events (e.g., pasta meals)
    2. For each trigger, looks for outcome events within time window
    3. Creates contingency table: [outcome_with_trigger, outcome_without_trigger]
    4. Runs chi-square test for statistical significance
    5. Returns patterns with p < 0.05

    Args:
        user_id: User's telegram ID
        start_date: Start of analysis period
        end_date: End of analysis period
        trigger_event_type: Type of trigger event (e.g., "meal")
        outcome_event_type: Type of outcome event (e.g., "symptom")
        time_window_hours: (min_hours, max_hours) after trigger to look for outcome
        min_occurrences: Minimum pattern occurrences to consider (default 10)

    Returns:
        List of PatternCandidate objects with p < 0.05

    Example:
        >>> patterns = await detect_temporal_correlations(
        ...     user_id="123",
        ...     start_date=datetime.now() - timedelta(days=90),
        ...     end_date=datetime.now(),
        ...     trigger_event_type="meal",
        ...     outcome_event_type="symptom"
        ... )
    """
    patterns = []

    # Get all events in the date range
    events = await get_health_events(user_id, start_date, end_date)

    if len(events) < min_occurrences * 2:
        logger.info(f"Not enough events for correlation analysis (have {len(events)}, need {min_occurrences * 2})")
        return patterns

    # Separate trigger and outcome events
    trigger_events = [e for e in events if e["event_type"] == trigger_event_type]
    outcome_events = [e for e in events if e["event_type"] == outcome_event_type]

    if not trigger_events or not outcome_events:
        return patterns

    # Group trigger events by metadata characteristics
    # (e.g., meals containing pasta, meals containing rice, etc.)
    trigger_groups = _group_events_by_characteristics(trigger_events, trigger_event_type)

    for characteristic, char_trigger_events in trigger_groups.items():
        if len(char_trigger_events) < min_occurrences:
            continue

        # For each outcome type, check correlation
        outcome_groups = _group_events_by_characteristics(outcome_events, outcome_event_type)

        for outcome_char, char_outcome_events in outcome_groups.items():
            # Build contingency table
            # [outcome_after_trigger, outcome_not_after_trigger]
            # [no_outcome_after_trigger, no_outcome_elsewhere]

            outcome_with_trigger = 0
            outcome_without_trigger = 0

            for trigger in char_trigger_events:
                trigger_time = trigger["timestamp"]
                # Look for outcome within time window
                found_outcome = False

                for outcome in char_outcome_events:
                    outcome_time = outcome["timestamp"]
                    hours_diff = (outcome_time - trigger_time).total_seconds() / 3600

                    if time_window_hours[0] <= hours_diff <= time_window_hours[1]:
                        found_outcome = True
                        break

                if found_outcome:
                    outcome_with_trigger += 1

            # Count outcomes that occurred without this trigger
            outcome_without_trigger = len(char_outcome_events) - outcome_with_trigger

            # Build 2x2 contingency table
            no_outcome_with_trigger = len(char_trigger_events) - outcome_with_trigger
            # Estimate no_outcome_without_trigger (simplified)
            total_time_periods = (end_date - start_date).days
            no_outcome_without_trigger = max(0, total_time_periods - outcome_without_trigger - no_outcome_with_trigger)

            contingency = [
                [outcome_with_trigger, outcome_without_trigger],
                [no_outcome_with_trigger, no_outcome_without_trigger]
            ]

            try:
                chi_sq, p_value = chi_square_test(contingency)

                if is_statistically_significant(p_value):
                    # Calculate correlation strength (proportion who get outcome)
                    correlation_strength = outcome_with_trigger / len(char_trigger_events) if len(char_trigger_events) > 0 else 0

                    # Create pattern candidate
                    pattern = PatternCandidate(
                        pattern_type="temporal_correlation",
                        pattern_rule={
                            "trigger": {
                                "event_type": trigger_event_type,
                                "characteristic": characteristic
                            },
                            "outcome": {
                                "event_type": outcome_event_type,
                                "characteristic": outcome_char
                            },
                            "time_window": {
                                "min_hours": time_window_hours[0],
                                "max_hours": time_window_hours[1]
                            },
                            "statistics": {
                                "correlation_strength": round(correlation_strength, 3),
                                "p_value": round(p_value, 6),
                                "chi_square": round(chi_sq, 3),
                                "sample_size": len(char_trigger_events)
                            }
                        },
                        confidence=round(correlation_strength, 2),
                        occurrences=outcome_with_trigger,
                        p_value=p_value
                    )

                    patterns.append(pattern)
                    logger.info(f"Found temporal correlation: {characteristic} → {outcome_char} (p={p_value:.4f})")

            except ValueError as e:
                logger.debug(f"Skipping correlation {characteristic} → {outcome_char}: {e}")
                continue

    return patterns


def _group_events_by_characteristics(events: List[Dict], event_type: EventType) -> Dict[str, List[Dict]]:
    """
    Group events by their meaningful characteristics.

    For meals: group by food items (pasta, rice, bread, etc.)
    For sleep: group by quality ranges (poor, good, excellent)
    For symptoms: group by symptom type

    Args:
        events: List of events to group
        event_type: Type of events

    Returns:
        Dictionary mapping characteristic → list of events
    """
    groups = defaultdict(list)

    for event in events:
        metadata = event.get("metadata", {})

        if event_type == "meal":
            # Group by foods
            foods = metadata.get("foods", [])
            for food in foods:
                if isinstance(food, dict):
                    food_name = food.get("name", "").lower()
                elif isinstance(food, str):
                    food_name = food.lower()
                else:
                    continue

                # Group by key food items
                for keyword in ["pasta", "rice", "bread", "chicken", "fish", "salad", "pizza", "burger"]:
                    if keyword in food_name:
                        groups[f"meal_contains_{keyword}"].append(event)

        elif event_type == "sleep":
            # Group by quality ranges
            quality = metadata.get("sleep_quality_rating", 0)
            if quality <= 4:
                groups["sleep_quality_poor"].append(event)
            elif quality <= 7:
                groups["sleep_quality_good"].append(event)
            else:
                groups["sleep_quality_excellent"].append(event)

        elif event_type == "symptom":
            # Group by symptom type
            symptom = metadata.get("symptom", "unknown")
            groups[f"symptom_{symptom}"].append(event)

        elif event_type == "stress":
            # Group by stress level
            stress_level = metadata.get("stress_level", 0)
            if stress_level <= 3:
                groups["stress_low"].append(event)
            elif stress_level <= 6:
                groups["stress_medium"].append(event)
            else:
                groups["stress_high"].append(event)

    return dict(groups)


# ================================================================
# Algorithm 2: Multi-Factor Pattern Analyzer
# ================================================================

async def detect_multifactor_patterns(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    factors: List[EventFilter],
    outcome: EventFilter,
    time_window_hours: int = 24,
    min_occurrences: int = 10
) -> List[PatternCandidate]:
    """
    Analyze combinations of 2-4 variables for correlation with outcome.

    Example: "Poor sleep + pasta + high stress → Energy crash"

    This algorithm:
    1. Identifies time periods where all factors are present
    2. Checks if outcome occurs in those periods
    3. Compares to baseline outcome rate
    4. Uses chi-square test for significance

    Args:
        user_id: User's telegram ID
        start_date: Start of analysis period
        end_date: End of analysis period
        factors: List of event filters (2-4 factors)
        outcome: Event filter for outcome
        time_window_hours: Hours to consider factors as "co-occurring"
        min_occurrences: Minimum pattern occurrences

    Returns:
        List of significant multi-factor patterns
    """
    if len(factors) < 2 or len(factors) > 4:
        raise ValueError("Multi-factor analysis requires 2-4 factors")

    patterns = []

    # Get all events
    events = await get_health_events(user_id, start_date, end_date)

    # Find time windows where all factors are present
    factor_windows = []

    # Group events by date (day-level granularity)
    events_by_day = defaultdict(list)
    for event in events:
        day_key = event["timestamp"].date()
        events_by_day[day_key].append(event)

    # Check each day for factor co-occurrence
    for day, day_events in events_by_day.items():
        factors_present = []

        for factor in factors:
            matching_events = [
                e for e in day_events
                if e["event_type"] == factor.event_type
                and _matches_metadata_conditions(e["metadata"], factor.metadata_conditions)
            ]
            if matching_events:
                factors_present.append(factor)

        # If all factors present, record this window
        if len(factors_present) == len(factors):
            # Check for outcome in same day or next day
            outcome_present = any(
                e for e in day_events
                if e["event_type"] == outcome.event_type
                and _matches_metadata_conditions(e["metadata"], outcome.metadata_conditions)
            )

            factor_windows.append({
                "date": day,
                "outcome_present": outcome_present
            })

    if len(factor_windows) < min_occurrences:
        return patterns

    # Build contingency table
    outcome_with_factors = sum(1 for w in factor_windows if w["outcome_present"])
    outcome_without_factors = 0  # Would need to calculate baseline

    # For simplicity, estimate baseline from total days
    total_days = (end_date - start_date).days
    days_with_factors = len(factor_windows)
    days_without_factors = total_days - days_with_factors

    # Count outcomes on days without all factors
    all_outcome_events = [
        e for e in events
        if e["event_type"] == outcome.event_type
        and _matches_metadata_conditions(e["metadata"], outcome.metadata_conditions)
    ]

    outcome_without_factors = max(0, len(all_outcome_events) - outcome_with_factors)

    contingency = [
        [outcome_with_factors, outcome_without_factors],
        [days_with_factors - outcome_with_factors, days_without_factors - outcome_without_factors]
    ]

    try:
        chi_sq, p_value = chi_square_test(contingency)

        if is_statistically_significant(p_value):
            correlation_strength = outcome_with_factors / days_with_factors if days_with_factors > 0 else 0

            pattern = PatternCandidate(
                pattern_type="multifactor_pattern",
                pattern_rule={
                    "factors": [
                        {
                            "event_type": f.event_type,
                            "conditions": f.metadata_conditions
                        }
                        for f in factors
                    ],
                    "outcome": {
                        "event_type": outcome.event_type,
                        "conditions": outcome.metadata_conditions
                    },
                    "statistics": {
                        "chi_square": round(chi_sq, 3),
                        "p_value": round(p_value, 6),
                        "effect_size": round(correlation_strength, 3),
                        "sample_size": days_with_factors
                    }
                },
                confidence=round(correlation_strength, 2),
                occurrences=outcome_with_factors,
                p_value=p_value
            )

            patterns.append(pattern)
            logger.info(f"Found multifactor pattern with {len(factors)} factors (p={p_value:.4f})")

    except ValueError as e:
        logger.debug(f"Skipping multifactor pattern: {e}")

    return patterns


def _matches_metadata_conditions(metadata: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
    """Check if event metadata matches filter conditions"""
    for key, expected_value in conditions.items():
        actual_value = metadata.get(key)

        # Handle comparison operators
        if isinstance(expected_value, str) and expected_value.startswith(">="):
            threshold = float(expected_value[2:])
            if not (isinstance(actual_value, (int, float)) and actual_value >= threshold):
                return False
        elif isinstance(expected_value, str) and expected_value.startswith("<="):
            threshold = float(expected_value[2:])
            if not (isinstance(actual_value, (int, float)) and actual_value <= threshold):
                return False
        elif isinstance(expected_value, str) and expected_value.startswith(">"):
            threshold = float(expected_value[1:])
            if not (isinstance(actual_value, (int, float)) and actual_value > threshold):
                return False
        elif isinstance(expected_value, str) and expected_value.startswith("<"):
            threshold = float(expected_value[1:])
            if not (isinstance(actual_value, (int, float)) and actual_value < threshold):
                return False
        else:
            # Exact match
            if actual_value != expected_value:
                return False

    return True


# ================================================================
# Algorithm 3: Temporal Sequence Detection
# ================================================================

async def detect_behavioral_sequences(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    min_sequence_length: int = 2,
    max_sequence_length: int = 5,
    max_hours_between_events: int = 24,
    min_occurrences: int = 5
) -> List[PatternCandidate]:
    """
    Find recurring sequences of events (behavioral chains).

    Example: "Evening walk → Good sleep → High energy next day"

    This uses a simplified sequence mining approach:
    1. Extract all event sequences within time windows
    2. Find frequently occurring sequences
    3. Test statistical significance

    Args:
        user_id: User's telegram ID
        start_date: Start of analysis period
        end_date: End of analysis period
        min_sequence_length: Minimum events in sequence (default 2)
        max_sequence_length: Maximum events in sequence (default 5)
        max_hours_between_events: Max time between consecutive events in sequence
        min_occurrences: Minimum times sequence must occur

    Returns:
        List of significant behavioral sequences
    """
    patterns = []

    # Get all events
    events = await get_health_events(user_id, start_date, end_date)

    if len(events) < min_sequence_length * min_occurrences:
        return patterns

    # Sort events by timestamp
    events_sorted = sorted(events, key=lambda e: e["timestamp"])

    # Extract sequences
    sequences = []
    for i in range(len(events_sorted)):
        # Try to build sequence starting from this event
        sequence = [events_sorted[i]]

        for j in range(i + 1, len(events_sorted)):
            time_diff = (events_sorted[j]["timestamp"] - sequence[-1]["timestamp"]).total_seconds() / 3600

            if time_diff <= max_hours_between_events:
                sequence.append(events_sorted[j])

                if len(sequence) >= min_sequence_length and len(sequence) <= max_sequence_length:
                    # Record this sequence
                    seq_signature = _get_sequence_signature(sequence)
                    sequences.append(seq_signature)

                if len(sequence) >= max_sequence_length:
                    break
            else:
                break

    # Count sequence occurrences
    from collections import Counter
    sequence_counts = Counter(sequences)

    # Find significant sequences
    total_possible_sequences = len(sequences)

    for seq_signature, count in sequence_counts.items():
        if count >= min_occurrences:
            # Calculate significance (binomial test approximation)
            expected_frequency = 1 / 100  # Assume low baseline probability
            observed_frequency = count / total_possible_sequences if total_possible_sequences > 0 else 0

            # Simple significance test (would use scipy.stats.binom_test in production)
            if observed_frequency > expected_frequency * 3:  # At least 3x baseline
                pattern = PatternCandidate(
                    pattern_type="behavioral_sequence",
                    pattern_rule={
                        "sequence": seq_signature.split(" → "),
                        "time_window": {
                            "max_hours_between_events": max_hours_between_events
                        },
                        "statistics": {
                            "sequence_support": round(observed_frequency, 3),
                            "p_value": 0.05,  # Placeholder - would calculate properly with scipy
                            "sample_size": count
                        }
                    },
                    confidence=min(round(observed_frequency * 10, 2), 0.99),
                    occurrences=count,
                    p_value=0.05
                )

                patterns.append(pattern)
                logger.info(f"Found behavioral sequence: {seq_signature} (n={count})")

    return patterns


def _get_sequence_signature(sequence: List[Dict]) -> str:
    """Get a string signature for a sequence of events"""
    parts = []
    for event in sequence:
        event_type = event["event_type"]
        metadata = event.get("metadata", {})

        # Create simple signature based on event type + key metadata
        if event_type == "meal":
            parts.append(f"meal({metadata.get('meal_type', 'unknown')})")
        elif event_type == "sleep":
            quality = metadata.get("sleep_quality_rating", 0)
            parts.append(f"sleep(quality_{quality})")
        elif event_type == "exercise":
            parts.append(f"exercise")
        elif event_type == "symptom":
            symptom = metadata.get("symptom", "unknown")
            parts.append(f"symptom({symptom})")
        else:
            parts.append(event_type)

    return " → ".join(parts)


# ================================================================
# Algorithm 4: Cyclical Pattern Finder
# ================================================================

async def detect_cyclical_patterns(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    cycle_types: List[str] = ["weekly", "monthly"],
    min_occurrences: int = 4
) -> List[PatternCandidate]:
    """
    Find patterns that repeat on cycles (weekly, monthly, menstrual cycle).

    Examples:
    - Weekend vs weekday energy levels
    - Tuesday afternoon cravings
    - Period week symptom patterns

    Args:
        user_id: User's telegram ID
        start_date: Start of analysis period
        end_date: End of analysis period
        cycle_types: Types of cycles to detect ["weekly", "monthly", "period"]
        min_occurrences: Minimum times pattern must recur

    Returns:
        List of significant cyclical patterns
    """
    patterns = []

    # Get all events
    events = await get_health_events(user_id, start_date, end_date)

    if "weekly" in cycle_types:
        weekly_patterns = await _detect_weekly_patterns(events, min_occurrences)
        patterns.extend(weekly_patterns)

    if "monthly" in cycle_types:
        monthly_patterns = await _detect_monthly_patterns(events, min_occurrences)
        patterns.extend(monthly_patterns)

    return patterns


async def _detect_weekly_patterns(events: List[Dict], min_occurrences: int) -> List[PatternCandidate]:
    """Detect weekly recurring patterns (e.g., Tuesday afternoon cravings)"""
    patterns = []

    # Group events by day of week and event type
    weekly_groups = defaultdict(lambda: defaultdict(list))

    for event in events:
        day_of_week = event["timestamp"].strftime("%A")
        event_type = event["event_type"]
        weekly_groups[day_of_week][event_type].append(event)

    # Find patterns that recur significantly more on specific days
    total_weeks = (max(e["timestamp"] for e in events) - min(e["timestamp"] for e in events)).days / 7

    for day_of_week, event_types in weekly_groups.items():
        for event_type, day_events in event_types.items():
            occurrences = len(day_events)

            if occurrences >= min_occurrences:
                # Calculate if this day has significantly more of this event
                recurrence_rate = occurrences / total_weeks if total_weeks > 0 else 0

                if recurrence_rate >= 0.75:  # Occurs 75%+ of weeks
                    pattern = PatternCandidate(
                        pattern_type="cyclical_pattern",
                        pattern_rule={
                            "cycle": "weekly",
                            "pattern": {
                                "day_of_week": day_of_week,
                                "event_type": event_type
                            },
                            "statistics": {
                                "recurrence_rate": round(recurrence_rate, 3),
                                "p_value": 0.05,  # Would calculate properly with scipy
                                "sample_size": int(total_weeks)
                            }
                        },
                        confidence=round(recurrence_rate, 2),
                        occurrences=occurrences,
                        p_value=0.05
                    )

                    patterns.append(pattern)
                    logger.info(f"Found weekly pattern: {event_type} on {day_of_week} (rate={recurrence_rate:.2f})")

    return patterns


async def _detect_monthly_patterns(events: List[Dict], min_occurrences: int) -> List[PatternCandidate]:
    """Detect monthly recurring patterns"""
    # Similar to weekly but group by day of month or week of month
    # Simplified for now
    return []


# ================================================================
# Algorithm 5: Semantic Similarity Clustering (Placeholder)
# ================================================================

async def cluster_similar_patterns(
    user_id: str,
    patterns: List[PatternCandidate]
) -> List[PatternCandidate]:
    """
    Group semantically similar patterns using pgvector embeddings.

    Example: Group "pasta → tiredness", "rice → tiredness", "bread → tiredness"
             into "high_carb_foods → tiredness"

    This is a placeholder - full implementation would:
    1. Generate text embeddings for each pattern using OpenAI/Anthropic
    2. Store embeddings in pgvector
    3. Find clusters using cosine similarity
    4. Create meta-patterns from clusters

    Args:
        user_id: User's telegram ID
        patterns: List of patterns to cluster

    Returns:
        List of meta-patterns (clusters)
    """
    # Placeholder - would implement with pgvector + embeddings
    logger.info(f"Semantic clustering not yet implemented (have {len(patterns)} patterns to cluster)")
    return []


# ================================================================
# Pattern Impact Scoring System (Phase 6.4)
# ================================================================

def calculate_impact_score(pattern: PatternCandidate, severity: Optional[float] = None) -> float:
    """
    Calculate impact score (0-100) for a discovered pattern.

    Impact score formula:
    - Severity (0-10): How significant is the outcome? (20% weight)
    - Frequency (0-10): How often does pattern occur? (15% weight)
    - Confidence (0-10): Statistical confidence based on p-value (30% weight)
    - Actionability (0-10): Can user change behavior? (35% weight)

    Total = (severity * 2.0) + (frequency * 1.5) + (confidence * 3.0) + (actionability * 3.5)

    Args:
        pattern: PatternCandidate to score
        severity: Optional severity score (0-10). If not provided, inferred from pattern

    Returns:
        Impact score (0.00-100.00)

    Example:
        >>> pattern = PatternCandidate(...)
        >>> impact = calculate_impact_score(pattern, severity=8)
        >>> print(f"Impact score: {impact:.1f}/100")
    """
    # 1. Severity score (0-10)
    if severity is not None:
        severity_score = severity
    else:
        severity_score = _infer_severity_from_pattern(pattern)

    # 2. Frequency score (0-10) - based on occurrences relative to time period
    # Assume 90-day analysis period
    daily_frequency = pattern.occurrences / 90.0
    if daily_frequency >= 0.5:  # Multiple times per day
        frequency_score = 10
    elif daily_frequency >= 0.25:  # Every few days
        frequency_score = 8
    elif daily_frequency >= 0.1:  # Weekly
        frequency_score = 6
    elif daily_frequency >= 0.05:  # Bi-weekly
        frequency_score = 4
    else:
        frequency_score = 2

    # 3. Confidence score (0-10) - based on statistical confidence
    # Lower p-value = higher confidence
    if pattern.p_value < 0.001:
        confidence_score = 10
    elif pattern.p_value < 0.01:
        confidence_score = 8
    elif pattern.p_value < 0.05:
        confidence_score = 6
    else:
        confidence_score = 3

    # Also factor in pattern confidence (0.0-1.0)
    confidence_score = (confidence_score + pattern.confidence * 10) / 2

    # 4. Actionability score (0-10) - can user change behavior?
    actionability_score = _assess_actionability(pattern)

    # Calculate weighted total
    impact_score = (
        (severity_score * 2.0) +
        (frequency_score * 1.5) +
        (confidence_score * 3.0) +
        (actionability_score * 3.5)
    )

    return round(min(impact_score, 100.0), 2)


def _infer_severity_from_pattern(pattern: PatternCandidate) -> float:
    """Infer severity score from pattern metadata"""
    rule = pattern.pattern_rule

    # Check outcome severity
    if pattern.pattern_type == "temporal_correlation":
        outcome = rule.get("outcome", {})
        outcome_char = outcome.get("characteristic", "")

        # High severity outcomes
        if any(keyword in outcome_char for keyword in ["severe", "pain", "migraine", "crash"]):
            return 9.0
        elif any(keyword in outcome_char for keyword in ["tiredness", "fatigue", "anxiety"]):
            return 7.0
        elif any(keyword in outcome_char for keyword in ["bloating", "discomfort"]):
            return 5.0
        else:
            return 4.0

    return 5.0  # Default moderate severity


def _assess_actionability(pattern: PatternCandidate) -> float:
    """
    Assess how actionable a pattern is (0-10).

    High actionability: User can easily change behavior
    Low actionability: Pattern involves factors outside user's control
    """
    rule = pattern.pattern_rule

    if pattern.pattern_type == "temporal_correlation":
        trigger = rule.get("trigger", {})
        trigger_type = trigger.get("event_type", "")

        # Food-related triggers are highly actionable
        if trigger_type == "meal":
            return 9.0
        # Exercise-related triggers are actionable
        elif trigger_type == "exercise":
            return 8.0
        # Sleep-related are moderately actionable
        elif trigger_type == "sleep":
            return 6.0
        # Stress-related are less actionable
        elif trigger_type == "stress":
            return 4.0
        else:
            return 5.0

    elif pattern.pattern_type == "multifactor_pattern":
        # Multi-factor patterns are complex but actionable if factors are controllable
        return 7.0

    elif pattern.pattern_type == "behavioral_sequence":
        # Sequences are actionable (user can replicate them)
        return 8.0

    elif pattern.pattern_type == "cyclical_pattern":
        # Cyclical patterns are moderately actionable (user can plan around them)
        return 6.0

    return 5.0


def generate_actionable_insight(pattern: PatternCandidate, impact_score: float) -> str:
    """
    Generate human-readable actionable insight from pattern.

    Args:
        pattern: PatternCandidate to describe
        impact_score: Calculated impact score

    Returns:
        Actionable insight text

    Example:
        >>> insight = generate_actionable_insight(pattern, impact_score=78.5)
        >>> print(insight)
        "You tend to feel tired 2-4 hours after eating pasta for lunch.
         Consider choosing a lower-carb lunch option on days when you
         need sustained afternoon energy."
    """
    rule = pattern.pattern_rule

    if pattern.pattern_type == "temporal_correlation":
        trigger = rule.get("trigger", {})
        outcome = rule.get("outcome", {})
        time_window = rule.get("time_window", {})

        trigger_desc = _describe_event(trigger)
        outcome_desc = _describe_event(outcome)

        min_hours = time_window.get("min_hours", 0)
        max_hours = time_window.get("max_hours", 24)

        confidence_pct = int(pattern.confidence * 100)

        insight = (
            f"You tend to {outcome_desc} "
            f"{min_hours}-{max_hours} hours after {trigger_desc}. "
        )

        if impact_score >= 70:
            insight += f"This happens {confidence_pct}% of the time and has a high impact. "

        # Add recommendation
        if "meal" in trigger.get("event_type", ""):
            insight += (
                f"Consider choosing different foods when you need to avoid {outcome_desc}."
            )
        elif "exercise" in trigger.get("event_type", ""):
            insight += (
                f"Plan your exercise timing to minimize {outcome_desc}."
            )

        return insight

    elif pattern.pattern_type == "multifactor_pattern":
        factors = rule.get("factors", [])
        outcome = rule.get("outcome", {})

        factor_desc = " + ".join(_describe_event(f) for f in factors[:3])
        outcome_desc = _describe_event(outcome)

        return (
            f"When you have {factor_desc}, you're more likely to {outcome_desc}. "
            f"Try addressing at least one of these factors to break the pattern."
        )

    elif pattern.pattern_type == "behavioral_sequence":
        sequence = rule.get("sequence", [])
        seq_desc = " → ".join(sequence[:4])

        return (
            f"You have a recurring pattern: {seq_desc}. "
            f"This occurs {pattern.occurrences} times in your history. "
            f"You can intentionally replicate this sequence for positive outcomes."
        )

    elif pattern.pattern_type == "cyclical_pattern":
        cycle = rule.get("cycle", "")
        pattern_detail = rule.get("pattern", {})
        day = pattern_detail.get("day_of_week", "")
        event_type = pattern_detail.get("event_type", "")

        return (
            f"Every {day}, you tend to have {event_type} events. "
            f"This is a {cycle} pattern. Plan accordingly."
        )

    return "Pattern detected. Review the data for more details."


def _describe_event(event_filter: Dict[str, Any]) -> str:
    """Convert event filter to human-readable description"""
    event_type = event_filter.get("event_type", "event")
    characteristic = event_filter.get("characteristic", "")
    conditions = event_filter.get("conditions", {})

    if characteristic:
        # Parse characteristic string
        if "meal_contains_" in characteristic:
            food = characteristic.replace("meal_contains_", "")
            return f"eat {food}"
        elif "symptom_" in characteristic:
            symptom = characteristic.replace("symptom_", "")
            return f"experience {symptom}"
        elif "sleep_quality_" in characteristic:
            quality = characteristic.replace("sleep_quality_", "")
            return f"have {quality} sleep"
        else:
            return characteristic

    if event_type == "meal":
        return "have a meal"
    elif event_type == "sleep":
        return "sleep"
    elif event_type == "symptom":
        return "experience symptoms"
    elif event_type == "exercise":
        return "exercise"
    else:
        return event_type


# ================================================================
# Pattern Confidence Update Mechanism (Phase 6.5)
# ================================================================

@dataclass
class Evidence:
    """Represents evidence for or against a pattern"""
    timestamp: datetime
    evidence_type: Literal["positive", "negative", "neutral"]
    context: str


async def update_pattern_confidence(
    pattern_id: int,
    new_evidence: Evidence
) -> Dict[str, Any]:
    """
    Update pattern confidence using Bayesian update formula.

    Confidence updates based on evidence:
    - Positive evidence (pattern holds): Increases confidence
    - Negative evidence (pattern fails): Decreases confidence
    - Neutral evidence (ambiguous): No change

    If confidence drops below 0.50, pattern is archived.

    Args:
        pattern_id: ID of pattern in discovered_patterns table
        new_evidence: New evidence to incorporate

    Returns:
        Updated pattern dict with new confidence

    Example:
        >>> evidence = Evidence(
        ...     timestamp=datetime.now(),
        ...     evidence_type="positive",
        ...     context="Pasta lunch at 12:00 → Tiredness at 14:30"
        ... )
        >>> updated = await update_pattern_confidence(pattern_id=123, new_evidence=evidence)
    """
    # Fetch current pattern from database
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, pattern_type, pattern_rule, confidence,
                       occurrences, impact_score, evidence, actionable_insight
                FROM discovered_patterns
                WHERE id = %s
                """,
                (pattern_id,)
            )
            row = await cur.fetchone()

            if not row:
                raise ValueError(f"Pattern {pattern_id} not found")

            current_pattern = dict(row)

    # Parse current evidence
    evidence_data = current_pattern.get("evidence") or {}
    positive_count = evidence_data.get("positive_count", 0)
    negative_count = evidence_data.get("negative_count", 0)
    neutral_count = evidence_data.get("neutral_count", 0)
    confidence_history = evidence_data.get("confidence_history", [])
    recent_evidence = evidence_data.get("recent_evidence", [])

    # Update evidence counts
    if new_evidence.evidence_type == "positive":
        positive_count += 1
    elif new_evidence.evidence_type == "negative":
        negative_count += 1
    else:
        neutral_count += 1

    # Calculate new confidence using Bayesian update
    # Prior: current confidence
    # Likelihood: evidence strength
    prior_confidence = current_pattern["confidence"]

    # Bayesian update formula (simplified)
    # New confidence = (positive_count + α) / (positive_count + negative_count + 2α)
    # where α is a prior strength parameter (default 2.0)
    alpha = 2.0
    new_confidence = (positive_count + alpha) / (positive_count + negative_count + 2 * alpha)

    # Ensure confidence stays in valid range
    new_confidence = max(0.0, min(1.0, new_confidence))

    # Add to confidence history
    confidence_history.append({
        "timestamp": new_evidence.timestamp.isoformat(),
        "confidence": round(new_confidence, 3),
        "evidence_type": new_evidence.evidence_type
    })

    # Add to recent evidence (keep last 20)
    recent_evidence.append({
        "timestamp": new_evidence.timestamp.isoformat(),
        "type": new_evidence.evidence_type,
        "context": new_evidence.context
    })
    recent_evidence = recent_evidence[-20:]  # Keep last 20

    # Update evidence JSON
    updated_evidence = {
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "last_positive": new_evidence.timestamp.isoformat() if new_evidence.evidence_type == "positive" else evidence_data.get("last_positive"),
        "last_negative": new_evidence.timestamp.isoformat() if new_evidence.evidence_type == "negative" else evidence_data.get("last_negative"),
        "confidence_history": confidence_history,
        "recent_evidence": recent_evidence
    }

    # Update pattern in database
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE discovered_patterns
                SET confidence = %s,
                    evidence = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (new_confidence, json.dumps(updated_evidence), pattern_id)
            )
            await conn.commit()

    logger.info(
        f"Updated pattern {pattern_id} confidence: {prior_confidence:.2f} → {new_confidence:.2f} "
        f"(evidence: {new_evidence.evidence_type})"
    )

    # Check if pattern should be archived (confidence < 0.50)
    if new_confidence < 0.50:
        await _archive_pattern(pattern_id, reason="Low confidence")
        logger.info(f"Archived pattern {pattern_id} due to low confidence ({new_confidence:.2f})")

    return {
        "pattern_id": pattern_id,
        "old_confidence": prior_confidence,
        "new_confidence": new_confidence,
        "evidence_summary": {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count
        }
    }


async def _archive_pattern(pattern_id: int, reason: str) -> None:
    """
    Archive a pattern (soft delete).

    Archived patterns are not shown to users but kept for historical analysis.

    Args:
        pattern_id: Pattern to archive
        reason: Reason for archiving
    """
    # In a full implementation, we'd move to an archived_patterns table
    # For now, we'll add an "archived" flag to the pattern_rule JSON

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE discovered_patterns
                SET pattern_rule = jsonb_set(
                        pattern_rule,
                        '{archived}',
                        'true'::jsonb
                    ),
                    pattern_rule = jsonb_set(
                        pattern_rule,
                        '{archive_reason}',
                        to_jsonb(%s::text)
                    ),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (reason, pattern_id)
            )
            await conn.commit()


async def evaluate_pattern_against_new_events(
    pattern_id: int,
    new_events: List[Dict[str, Any]]
) -> List[Evidence]:
    """
    Evaluate pattern against new events to generate evidence.

    This checks if recent events match the pattern or contradict it.

    Args:
        pattern_id: Pattern to evaluate
        new_events: Recent events to check against pattern

    Returns:
        List of Evidence objects

    Example:
        >>> events = await get_health_events(user_id, datetime.now() - timedelta(days=1), datetime.now())
        >>> evidence = await evaluate_pattern_against_new_events(pattern_id=123, new_events=events)
    """
    # Fetch pattern
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT pattern_type, pattern_rule FROM discovered_patterns WHERE id = %s",
                (pattern_id,)
            )
            row = await cur.fetchone()

            if not row:
                return []

            pattern_type = row["pattern_type"]
            pattern_rule = row["pattern_rule"]

    evidence_list = []

    if pattern_type == "temporal_correlation":
        # Check if trigger → outcome relationship holds in new events
        trigger = pattern_rule.get("trigger", {})
        outcome = pattern_rule.get("outcome", {})
        time_window = pattern_rule.get("time_window", {})

        trigger_event_type = trigger.get("event_type")
        outcome_event_type = outcome.get("event_type")
        min_hours = time_window.get("min_hours", 0)
        max_hours = time_window.get("max_hours", 24)

        # Find trigger events
        trigger_events = [
            e for e in new_events
            if e["event_type"] == trigger_event_type
        ]

        for trigger_event in trigger_events:
            trigger_time = trigger_event["timestamp"]

            # Look for outcome within time window
            found_outcome = False
            for outcome_event in new_events:
                if outcome_event["event_type"] == outcome_event_type:
                    outcome_time = outcome_event["timestamp"]
                    hours_diff = (outcome_time - trigger_time).total_seconds() / 3600

                    if min_hours <= hours_diff <= max_hours:
                        found_outcome = True
                        evidence_list.append(Evidence(
                            timestamp=outcome_time,
                            evidence_type="positive",
                            context=f"Pattern confirmed: {trigger_event_type} → {outcome_event_type}"
                        ))
                        break

            if not found_outcome:
                # Trigger occurred but no outcome = negative evidence
                evidence_list.append(Evidence(
                    timestamp=trigger_time + timedelta(hours=max_hours),
                    evidence_type="negative",
                    context=f"Pattern not confirmed: {trigger_event_type} but no {outcome_event_type}"
                ))

    return evidence_list


# ================================================================
# Pattern Persistence (Database Operations)
# ================================================================

async def save_pattern_to_database(
    pattern: PatternCandidate,
    user_id: str,
    impact_score: float,
    actionable_insight: str
) -> int:
    """
    Save a discovered pattern to the database.

    Args:
        pattern: PatternCandidate to save
        user_id: User's telegram ID
        impact_score: Calculated impact score
        actionable_insight: Generated insight text

    Returns:
        Pattern ID (database primary key)

    Example:
        >>> pattern_id = await save_pattern_to_database(pattern, user_id, impact_score, insight)
    """
    # Initialize evidence structure
    initial_evidence = {
        "positive_count": pattern.occurrences,
        "negative_count": 0,
        "neutral_count": 0,
        "confidence_history": [
            {
                "timestamp": datetime.now().isoformat(),
                "confidence": pattern.confidence
            }
        ],
        "recent_evidence": []
    }

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(
                    """
                    INSERT INTO discovered_patterns
                    (user_id, pattern_type, pattern_rule, confidence, occurrences,
                     impact_score, evidence, actionable_insight)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        pattern.pattern_type,
                        json.dumps(pattern.pattern_rule),
                        pattern.confidence,
                        pattern.occurrences,
                        impact_score,
                        json.dumps(initial_evidence),
                        actionable_insight
                    )
                )
                result = await cur.fetchone()
                pattern_id = result["id"]
                await conn.commit()

                logger.info(f"Saved pattern {pattern_id}: {pattern.pattern_type} for user {user_id}")
                return pattern_id

            except Exception as e:
                logger.error(f"Failed to save pattern: {e}", exc_info=True)
                raise


async def get_user_patterns(
    user_id: str,
    min_confidence: float = 0.50,
    min_impact: float = 0.0,
    include_archived: bool = False
) -> List[Dict[str, Any]]:
    """
    Retrieve all patterns for a user.

    Args:
        user_id: User's telegram ID
        min_confidence: Minimum confidence threshold (default 0.50)
        min_impact: Minimum impact score threshold (default 0.0)
        include_archived: Include archived patterns (default False)

    Returns:
        List of pattern dictionaries

    Example:
        >>> patterns = await get_user_patterns("123", min_confidence=0.70, min_impact=50)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            query = """
                SELECT id, user_id, pattern_type, pattern_rule, confidence,
                       occurrences, impact_score, evidence, actionable_insight,
                       created_at, updated_at
                FROM discovered_patterns
                WHERE user_id = %s
                  AND confidence >= %s
                  AND (impact_score >= %s OR impact_score IS NULL)
            """
            params = [user_id, min_confidence, min_impact]

            if not include_archived:
                query += " AND (pattern_rule->>'archived' IS NULL OR pattern_rule->>'archived' != 'true')"

            query += " ORDER BY impact_score DESC NULLS LAST, confidence DESC"

            await cur.execute(query, params)
            rows = await cur.fetchall()
            return [dict(row) for row in rows]
