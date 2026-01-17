"""
Unit tests for pattern_detection module
Epic 009 - Phase 6: Pattern Detection Engine

Tests pattern detection algorithms, impact scoring, and confidence updates.
Target coverage: 90%+
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.pattern_detection import (
    PatternCandidate,
    EventFilter,
    Evidence,
    calculate_impact_score,
    generate_actionable_insight,
    _infer_severity_from_pattern,
    _assess_actionability,
    _describe_event,
    _group_events_by_characteristics,
    _matches_metadata_conditions
)


class TestPatternImpactScoring:
    """Tests for calculate_impact_score() function"""

    def test_high_impact_pattern(self):
        """Test high impact pattern scoring"""
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "trigger": {"event_type": "meal", "characteristic": "meal_contains_pasta"},
                "outcome": {"event_type": "symptom", "characteristic": "symptom_tiredness"},
                "statistics": {"p_value": 0.001}
            },
            confidence=0.85,
            occurrences=25,  # Occurs every 3-4 days over 90 days
            p_value=0.001
        )

        impact = calculate_impact_score(pattern, severity=8.0)

        assert impact >= 70  # High impact
        assert impact <= 100

    def test_low_impact_pattern(self):
        """Test low impact pattern scoring"""
        pattern = PatternCandidate(
            pattern_type="cyclical_pattern",
            pattern_rule={
                "pattern": {"event_type": "meal"}
            },
            confidence=0.55,
            occurrences=5,  # Rare occurrence
            p_value=0.045
        )

        impact = calculate_impact_score(pattern, severity=3.0)

        assert impact < 50  # Low impact

    def test_impact_increases_with_frequency(self):
        """Test that higher frequency increases impact score"""
        high_freq_pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={},
            confidence=0.75,
            occurrences=45,  # Every 2 days
            p_value=0.01
        )

        low_freq_pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={},
            confidence=0.75,
            occurrences=5,  # Rare
            p_value=0.01
        )

        high_impact = calculate_impact_score(high_freq_pattern)
        low_impact = calculate_impact_score(low_freq_pattern)

        assert high_impact > low_impact

    def test_impact_increases_with_confidence(self):
        """Test that higher confidence increases impact score"""
        high_conf_pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={},
            confidence=0.90,
            occurrences=20,
            p_value=0.001
        )

        low_conf_pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={},
            confidence=0.55,
            occurrences=20,
            p_value=0.04
        )

        high_impact = calculate_impact_score(high_conf_pattern)
        low_impact = calculate_impact_score(low_conf_pattern)

        assert high_impact > low_impact


class TestSeverityInference:
    """Tests for _infer_severity_from_pattern() function"""

    def test_high_severity_outcomes(self):
        """Test high severity outcomes get high scores"""
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "outcome": {"characteristic": "symptom_migraine"}
            },
            confidence=0.8,
            occurrences=10,
            p_value=0.01
        )

        severity = _infer_severity_from_pattern(pattern)

        assert severity >= 8.0  # High severity

    def test_medium_severity_outcomes(self):
        """Test medium severity outcomes"""
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "outcome": {"characteristic": "symptom_tiredness"}
            },
            confidence=0.8,
            occurrences=10,
            p_value=0.01
        )

        severity = _infer_severity_from_pattern(pattern)

        assert 6.0 <= severity <= 8.0  # Medium-high severity

    def test_low_severity_outcomes(self):
        """Test low severity outcomes"""
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "outcome": {"characteristic": "symptom_bloating"}
            },
            confidence=0.8,
            occurrences=10,
            p_value=0.01
        )

        severity = _infer_severity_from_pattern(pattern)

        assert severity <= 6.0  # Lower severity


class TestActionability:
    """Tests for _assess_actionability() function"""

    def test_meal_patterns_highly_actionable(self):
        """Test meal-based patterns are highly actionable"""
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "trigger": {"event_type": "meal"}
            },
            confidence=0.8,
            occurrences=10,
            p_value=0.01
        )

        actionability = _assess_actionability(pattern)

        assert actionability >= 8.0  # Highly actionable

    def test_stress_patterns_less_actionable(self):
        """Test stress-based patterns are less actionable"""
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "trigger": {"event_type": "stress"}
            },
            confidence=0.8,
            occurrences=10,
            p_value=0.01
        )

        actionability = _assess_actionability(pattern)

        assert actionability <= 5.0  # Less actionable

    def test_behavioral_sequences_actionable(self):
        """Test behavioral sequences are actionable"""
        pattern = PatternCandidate(
            pattern_type="behavioral_sequence",
            pattern_rule={},
            confidence=0.8,
            occurrences=10,
            p_value=0.01
        )

        actionability = _assess_actionability(pattern)

        assert actionability >= 7.0  # Actionable


class TestActionableInsights:
    """Tests for generate_actionable_insight() function"""

    def test_temporal_correlation_insight(self):
        """Test insight generation for temporal correlations"""
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "trigger": {
                    "event_type": "meal",
                    "characteristic": "meal_contains_pasta"
                },
                "outcome": {
                    "event_type": "symptom",
                    "characteristic": "symptom_tiredness"
                },
                "time_window": {"min_hours": 2, "max_hours": 4}
            },
            confidence=0.80,
            occurrences=18,
            p_value=0.003
        )

        insight = generate_actionable_insight(pattern, impact_score=78.5)

        assert "pasta" in insight.lower()
        assert "tired" in insight.lower() or "tiredness" in insight.lower()
        assert "2-4 hours" in insight
        # Should include recommendation
        assert len(insight) > 50  # Meaningful insight

    def test_multifactor_pattern_insight(self):
        """Test insight generation for multi-factor patterns"""
        pattern = PatternCandidate(
            pattern_type="multifactor_pattern",
            pattern_rule={
                "factors": [
                    {"event_type": "sleep", "conditions": {"sleep_quality_rating": "<6"}},
                    {"event_type": "meal", "conditions": {"foods_contain": "pasta"}},
                    {"event_type": "stress", "conditions": {"stress_level": ">=7"}}
                ],
                "outcome": {
                    "event_type": "symptom",
                    "conditions": {"symptom": "energy_crash"}
                }
            },
            confidence=0.75,
            occurrences=12,
            p_value=0.008
        )

        insight = generate_actionable_insight(pattern, impact_score=65.0)

        # Should mention addressing factors
        assert "factor" in insight.lower() or "addressing" in insight.lower()
        assert len(insight) > 30

    def test_behavioral_sequence_insight(self):
        """Test insight generation for behavioral sequences"""
        pattern = PatternCandidate(
            pattern_type="behavioral_sequence",
            pattern_rule={
                "sequence": ["exercise", "sleep(quality_8)", "mood(energized)"]
            },
            confidence=0.72,
            occurrences=8,
            p_value=0.015
        )

        insight = generate_actionable_insight(pattern, impact_score=70.0)

        assert "sequence" in insight.lower() or "pattern" in insight.lower()
        assert "8 times" in insight or "8" in insight
        assert len(insight) > 30

    def test_cyclical_pattern_insight(self):
        """Test insight generation for cyclical patterns"""
        pattern = PatternCandidate(
            pattern_type="cyclical_pattern",
            pattern_rule={
                "cycle": "weekly",
                "pattern": {
                    "day_of_week": "Tuesday",
                    "event_type": "symptom"
                }
            },
            confidence=0.82,
            occurrences=10,
            p_value=0.008
        )

        insight = generate_actionable_insight(pattern, impact_score=60.0)

        assert "Tuesday" in insight
        assert "weekly" in insight.lower()
        assert len(insight) > 20


class TestEventDescription:
    """Tests for _describe_event() function"""

    def test_meal_characteristic_description(self):
        """Test meal event descriptions"""
        event = {
            "event_type": "meal",
            "characteristic": "meal_contains_pasta"
        }

        description = _describe_event(event)

        assert "pasta" in description.lower()
        assert "eat" in description.lower()

    def test_symptom_characteristic_description(self):
        """Test symptom event descriptions"""
        event = {
            "event_type": "symptom",
            "characteristic": "symptom_tiredness"
        }

        description = _describe_event(event)

        assert "tiredness" in description.lower()
        assert "experience" in description.lower()

    def test_sleep_quality_description(self):
        """Test sleep quality descriptions"""
        event = {
            "event_type": "sleep",
            "characteristic": "sleep_quality_poor"
        }

        description = _describe_event(event)

        assert "poor" in description.lower()
        assert "sleep" in description.lower()

    def test_generic_event_description(self):
        """Test generic event type descriptions"""
        event = {"event_type": "exercise"}

        description = _describe_event(event)

        assert "exercise" in description.lower()


class TestEventGrouping:
    """Tests for _group_events_by_characteristics() function"""

    def test_group_meals_by_food(self):
        """Test grouping meals by food items"""
        events = [
            {
                "event_type": "meal",
                "metadata": {
                    "foods": [
                        {"name": "Pasta Carbonara"},
                        {"name": "Salad"}
                    ]
                }
            },
            {
                "event_type": "meal",
                "metadata": {
                    "foods": [
                        {"name": "Grilled Chicken"},
                        {"name": "Rice"}
                    ]
                }
            },
            {
                "event_type": "meal",
                "metadata": {
                    "foods": ["Pasta Bolognese"]
                }
            }
        ]

        groups = _group_events_by_characteristics(events, "meal")

        assert "meal_contains_pasta" in groups
        assert len(groups["meal_contains_pasta"]) == 2  # Two pasta meals
        assert "meal_contains_rice" in groups
        assert "meal_contains_chicken" in groups

    def test_group_sleep_by_quality(self):
        """Test grouping sleep events by quality ranges"""
        events = [
            {"event_type": "sleep", "metadata": {"sleep_quality_rating": 3}},
            {"event_type": "sleep", "metadata": {"sleep_quality_rating": 6}},
            {"event_type": "sleep", "metadata": {"sleep_quality_rating": 9}},
            {"event_type": "sleep", "metadata": {"sleep_quality_rating": 4}},
            {"event_type": "sleep", "metadata": {"sleep_quality_rating": 8}}
        ]

        groups = _group_events_by_characteristics(events, "sleep")

        assert "sleep_quality_poor" in groups  # Rating <= 4
        assert "sleep_quality_good" in groups  # Rating 5-7
        assert "sleep_quality_excellent" in groups  # Rating >= 8

        assert len(groups["sleep_quality_poor"]) == 2
        assert len(groups["sleep_quality_good"]) == 1
        assert len(groups["sleep_quality_excellent"]) == 2

    def test_group_symptoms_by_type(self):
        """Test grouping symptoms by type"""
        events = [
            {"event_type": "symptom", "metadata": {"symptom": "tiredness"}},
            {"event_type": "symptom", "metadata": {"symptom": "bloating"}},
            {"event_type": "symptom", "metadata": {"symptom": "tiredness"}}
        ]

        groups = _group_events_by_characteristics(events, "symptom")

        assert "symptom_tiredness" in groups
        assert "symptom_bloating" in groups
        assert len(groups["symptom_tiredness"]) == 2
        assert len(groups["symptom_bloating"]) == 1


class TestMetadataMatching:
    """Tests for _matches_metadata_conditions() function"""

    def test_exact_match(self):
        """Test exact value matching"""
        metadata = {"symptom": "tiredness", "severity": 7}
        conditions = {"symptom": "tiredness"}

        assert _matches_metadata_conditions(metadata, conditions) is True

    def test_exact_mismatch(self):
        """Test exact value mismatch"""
        metadata = {"symptom": "bloating"}
        conditions = {"symptom": "tiredness"}

        assert _matches_metadata_conditions(metadata, conditions) is False

    def test_greater_than_or_equal(self):
        """Test >= operator"""
        metadata = {"severity": 8}
        conditions = {"severity": ">=7"}

        assert _matches_metadata_conditions(metadata, conditions) is True

        metadata = {"severity": 6}
        assert _matches_metadata_conditions(metadata, conditions) is False

    def test_less_than_or_equal(self):
        """Test <= operator"""
        metadata = {"sleep_hours": 6.0}
        conditions = {"sleep_hours": "<=7"}

        assert _matches_metadata_conditions(metadata, conditions) is True

        metadata = {"sleep_hours": 8.0}
        assert _matches_metadata_conditions(metadata, conditions) is False

    def test_greater_than(self):
        """Test > operator"""
        metadata = {"calories": 600}
        conditions = {"calories": ">500"}

        assert _matches_metadata_conditions(metadata, conditions) is True

    def test_less_than(self):
        """Test < operator"""
        metadata = {"calories": 400}
        conditions = {"calories": "<500"}

        assert _matches_metadata_conditions(metadata, conditions) is True

    def test_multiple_conditions(self):
        """Test matching multiple conditions"""
        metadata = {"symptom": "tiredness", "severity": 8, "duration": "2-4 hours"}
        conditions = {"symptom": "tiredness", "severity": ">=7"}

        assert _matches_metadata_conditions(metadata, conditions) is True

    def test_missing_metadata_field(self):
        """Test condition on missing metadata field"""
        metadata = {"symptom": "tiredness"}
        conditions = {"severity": ">=7"}

        # Missing field should not match
        assert _matches_metadata_conditions(metadata, conditions) is False


class TestEvidenceDataclass:
    """Tests for Evidence dataclass"""

    def test_create_positive_evidence(self):
        """Test creating positive evidence"""
        evidence = Evidence(
            timestamp=datetime.now(),
            evidence_type="positive",
            context="Pattern confirmed"
        )

        assert evidence.evidence_type == "positive"
        assert isinstance(evidence.timestamp, datetime)
        assert evidence.context == "Pattern confirmed"

    def test_create_negative_evidence(self):
        """Test creating negative evidence"""
        evidence = Evidence(
            timestamp=datetime.now(),
            evidence_type="negative",
            context="Pattern not confirmed"
        )

        assert evidence.evidence_type == "negative"


class TestPatternCandidateDataclass:
    """Tests for PatternCandidate dataclass"""

    def test_create_pattern_candidate(self):
        """Test creating a pattern candidate"""
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={"trigger": "meal", "outcome": "symptom"},
            confidence=0.85,
            occurrences=20,
            p_value=0.003,
            effect_size=0.75
        )

        assert pattern.pattern_type == "temporal_correlation"
        assert pattern.confidence == 0.85
        assert pattern.occurrences == 20
        assert pattern.p_value == 0.003
        assert pattern.effect_size == 0.75


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_events_grouping(self):
        """Test grouping with empty event list"""
        groups = _group_events_by_characteristics([], "meal")

        assert groups == {}

    def test_events_missing_metadata(self):
        """Test handling events without metadata"""
        events = [
            {"event_type": "meal"},  # No metadata
            {"event_type": "meal", "metadata": {}}  # Empty metadata
        ]

        groups = _group_events_by_characteristics(events, "meal")

        # Should not crash, groups may be empty
        assert isinstance(groups, dict)

    def test_impact_score_boundary_values(self):
        """Test impact score stays within 0-100"""
        # Very high values
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={},
            confidence=1.0,
            occurrences=1000,
            p_value=0.0001
        )

        impact = calculate_impact_score(pattern, severity=10.0)

        assert 0 <= impact <= 100

        # Very low values
        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={},
            confidence=0.50,
            occurrences=1,
            p_value=0.049
        )

        impact = calculate_impact_score(pattern, severity=1.0)

        assert 0 <= impact <= 100
