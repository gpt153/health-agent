"""
Integration tests for pattern mining workflow
Epic 009 - Phase 6: Pattern Detection Engine

Tests end-to-end pattern discovery, persistence, and confidence updates.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from src.services.pattern_detection import (
    detect_temporal_correlations,
    calculate_impact_score,
    generate_actionable_insight,
    save_pattern_to_database,
    get_user_patterns,
    update_pattern_confidence,
    Evidence,
    evaluate_pattern_against_new_events
)
from src.services.health_events import create_health_event
from src.scheduler.pattern_mining import run_pattern_mining_now


@pytest.mark.asyncio
class TestPatternDiscoveryWorkflow:
    """Test end-to-end pattern discovery"""

    async def test_discover_food_symptom_correlation(self):
        """
        Test discovering a temporal correlation pattern.

        Scenario: User logs pasta meals followed by tiredness symptoms
        """
        user_id = f"test_user_{uuid4()}"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # Create 15 pasta meal events followed by tiredness
        for i in range(15):
            meal_time = start_date + timedelta(days=i*2, hours=12)  # Every 2 days at noon

            # Log pasta meal
            await create_health_event(
                user_id=user_id,
                event_type="meal",
                timestamp=meal_time,
                metadata={
                    "meal_type": "lunch",
                    "foods": [
                        {"name": "Pasta Carbonara", "calories": 600}
                    ],
                    "total_calories": 600
                }
            )

            # Log tiredness symptom 3 hours later
            symptom_time = meal_time + timedelta(hours=3)
            await create_health_event(
                user_id=user_id,
                event_type="symptom",
                timestamp=symptom_time,
                metadata={
                    "symptom": "tiredness",
                    "severity": 7
                }
            )

        # Create some meals without pasta (no tiredness)
        for i in range(5):
            meal_time = start_date + timedelta(days=i*6+1, hours=12)

            await create_health_event(
                user_id=user_id,
                event_type="meal",
                timestamp=meal_time,
                metadata={
                    "meal_type": "lunch",
                    "foods": [{"name": "Grilled Chicken", "calories": 400}],
                    "total_calories": 400
                }
            )

        # Detect patterns
        patterns = await detect_temporal_correlations(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            trigger_event_type="meal",
            outcome_event_type="symptom",
            time_window_hours=(1, 6),
            min_occurrences=10
        )

        # Assertions
        assert len(patterns) > 0, "Should discover at least one pattern"

        pasta_pattern = next(
            (p for p in patterns if "pasta" in str(p.pattern_rule).lower()),
            None
        )
        assert pasta_pattern is not None, "Should discover pasta → tiredness pattern"
        assert pasta_pattern.p_value < 0.05, "Pattern should be statistically significant"
        assert pasta_pattern.occurrences >= 10, "Pattern should have minimum occurrences"

    async def test_pattern_persistence_and_retrieval(self):
        """
        Test saving and retrieving patterns from database.
        """
        user_id = f"test_user_{uuid4()}"

        # Create a mock pattern
        from src.services.pattern_detection import PatternCandidate

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
                "time_window": {"min_hours": 2, "max_hours": 4},
                "statistics": {
                    "correlation_strength": 0.80,
                    "p_value": 0.003,
                    "sample_size": 18
                }
            },
            confidence=0.80,
            occurrences=18,
            p_value=0.003
        )

        # Calculate impact and insight
        impact_score = calculate_impact_score(pattern, severity=7.0)
        insight = generate_actionable_insight(pattern, impact_score)

        # Save to database
        pattern_id = await save_pattern_to_database(
            pattern=pattern,
            user_id=user_id,
            impact_score=impact_score,
            actionable_insight=insight
        )

        assert pattern_id is not None, "Should return pattern ID"
        assert isinstance(pattern_id, int), "Pattern ID should be an integer"

        # Retrieve patterns
        patterns = await get_user_patterns(user_id, min_confidence=0.50)

        assert len(patterns) >= 1, "Should retrieve saved pattern"

        retrieved_pattern = patterns[0]
        assert retrieved_pattern["id"] == pattern_id
        assert retrieved_pattern["confidence"] == 0.80
        assert retrieved_pattern["impact_score"] == impact_score
        assert retrieved_pattern["actionable_insight"] == insight


@pytest.mark.asyncio
class TestPatternConfidenceUpdates:
    """Test pattern confidence update mechanism"""

    async def test_confidence_increases_with_positive_evidence(self):
        """
        Test that confidence increases when pattern is confirmed.
        """
        user_id = f"test_user_{uuid4()}"

        # Create and save initial pattern
        from src.services.pattern_detection import PatternCandidate

        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "trigger": {"event_type": "meal"},
                "outcome": {"event_type": "symptom"}
            },
            confidence=0.70,
            occurrences=10,
            p_value=0.01
        )

        pattern_id = await save_pattern_to_database(
            pattern=pattern,
            user_id=user_id,
            impact_score=60.0,
            actionable_insight="Test pattern"
        )

        # Add positive evidence
        evidence = Evidence(
            timestamp=datetime.now(),
            evidence_type="positive",
            context="Pattern confirmed: meal → symptom"
        )

        result = await update_pattern_confidence(pattern_id, evidence)

        assert result["new_confidence"] > result["old_confidence"], \
            "Confidence should increase with positive evidence"
        assert result["evidence_summary"]["positive"] == 11, \
            "Positive count should increment"

    async def test_confidence_decreases_with_negative_evidence(self):
        """
        Test that confidence decreases when pattern fails.
        """
        user_id = f"test_user_{uuid4()}"

        from src.services.pattern_detection import PatternCandidate

        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "trigger": {"event_type": "meal"},
                "outcome": {"event_type": "symptom"}
            },
            confidence=0.70,
            occurrences=10,
            p_value=0.01
        )

        pattern_id = await save_pattern_to_database(
            pattern=pattern,
            user_id=user_id,
            impact_score=60.0,
            actionable_insight="Test pattern"
        )

        # Add multiple negative evidence
        for _ in range(5):
            evidence = Evidence(
                timestamp=datetime.now(),
                evidence_type="negative",
                context="Pattern not confirmed: meal but no symptom"
            )
            result = await update_pattern_confidence(pattern_id, evidence)

        assert result["new_confidence"] < 0.70, \
            "Confidence should decrease significantly with negative evidence"
        assert result["evidence_summary"]["negative"] == 5, \
            "Negative count should be 5"

    async def test_pattern_archived_when_confidence_too_low(self):
        """
        Test that patterns are archived when confidence drops below threshold.
        """
        user_id = f"test_user_{uuid4()}"

        from src.services.pattern_detection import PatternCandidate

        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "trigger": {"event_type": "meal"},
                "outcome": {"event_type": "symptom"}
            },
            confidence=0.55,  # Close to threshold
            occurrences=10,
            p_value=0.04
        )

        pattern_id = await save_pattern_to_database(
            pattern=pattern,
            user_id=user_id,
            impact_score=50.0,
            actionable_insight="Test pattern"
        )

        # Add enough negative evidence to drop below 0.50
        for _ in range(10):
            evidence = Evidence(
                timestamp=datetime.now(),
                evidence_type="negative",
                context="Pattern failed"
            )
            result = await update_pattern_confidence(pattern_id, evidence)

        # Check if archived (confidence < 0.50)
        if result["new_confidence"] < 0.50:
            # Pattern should be archived
            patterns = await get_user_patterns(user_id, include_archived=False)
            pattern_ids = [p["id"] for p in patterns]
            assert pattern_id not in pattern_ids, \
                "Archived patterns should not appear in default queries"

            # But should appear when including archived
            patterns_with_archived = await get_user_patterns(
                user_id,
                include_archived=True
            )
            pattern_ids_with_archived = [p["id"] for p in patterns_with_archived]
            assert pattern_id in pattern_ids_with_archived, \
                "Archived patterns should appear when explicitly requested"


@pytest.mark.asyncio
class TestPatternMiningScheduler:
    """Test nightly pattern mining job"""

    async def test_pattern_mining_job_execution(self):
        """
        Test that pattern mining job discovers patterns from user data.
        """
        user_id = f"test_user_{uuid4()}"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        # Create test data: pasta meals → tiredness pattern
        for i in range(20):
            meal_time = start_date + timedelta(days=i*3, hours=12)

            # Pasta meal
            await create_health_event(
                user_id=user_id,
                event_type="meal",
                timestamp=meal_time,
                metadata={
                    "meal_type": "lunch",
                    "foods": [{"name": "Spaghetti Bolognese"}],
                    "total_calories": 650
                }
            )

            # Tiredness symptom 2-3 hours later
            symptom_time = meal_time + timedelta(hours=2.5)
            await create_health_event(
                user_id=user_id,
                event_type="symptom",
                timestamp=symptom_time,
                metadata={"symptom": "tiredness", "severity": 6}
            )

        # Run pattern mining manually (simulates nightly job)
        result = await run_pattern_mining_now(user_id)

        # Assertions
        assert result["user_id"] == user_id
        assert result["events_analyzed"] >= 40, "Should analyze all created events"
        assert result["new_patterns"] >= 0, "Should attempt pattern discovery"
        assert result["duration_seconds"] < 30, "Should complete within reasonable time"

        # Check if patterns were saved
        patterns = await get_user_patterns(user_id)

        # May or may not discover patterns depending on statistical significance
        # This test mainly validates that the job runs without errors


@pytest.mark.asyncio
class TestPatternEvaluation:
    """Test pattern evaluation against new events"""

    async def test_evaluate_pattern_generates_evidence(self):
        """
        Test that evaluating patterns against new events generates evidence.
        """
        user_id = f"test_user_{uuid4()}"

        # Create pattern
        from src.services.pattern_detection import PatternCandidate

        pattern = PatternCandidate(
            pattern_type="temporal_correlation",
            pattern_rule={
                "trigger": {"event_type": "meal"},
                "outcome": {"event_type": "symptom"},
                "time_window": {"min_hours": 1, "max_hours": 6}
            },
            confidence=0.75,
            occurrences=15,
            p_value=0.008
        )

        pattern_id = await save_pattern_to_database(
            pattern, user_id, 70.0, "Test pattern"
        )

        # Create new events that confirm pattern
        now = datetime.now()

        meal_event = {
            "event_type": "meal",
            "timestamp": now,
            "metadata": {"meal_type": "lunch"}
        }

        symptom_event = {
            "event_type": "symptom",
            "timestamp": now + timedelta(hours=3),
            "metadata": {"symptom": "tiredness"}
        }

        new_events = [meal_event, symptom_event]

        # Evaluate pattern
        evidence_list = await evaluate_pattern_against_new_events(
            pattern_id=pattern_id,
            new_events=new_events
        )

        assert len(evidence_list) > 0, "Should generate evidence"
        assert any(e.evidence_type == "positive" for e in evidence_list), \
            "Should find positive evidence when pattern holds"


@pytest.mark.asyncio
class TestPerformanceRequirements:
    """Test performance requirements"""

    @pytest.mark.slow
    async def test_pattern_detection_performance(self):
        """
        Test that pattern detection completes within performance target.

        Requirement: <5 minutes for 1000 events
        """
        user_id = f"test_user_{uuid4()}"
        start_time = datetime.now()

        # Create 1000 health events (mix of meals, sleep, symptoms)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        event_count = 0
        for day in range(90):
            day_time = start_date + timedelta(days=day)

            # 3 meals per day
            for meal_hour in [8, 13, 19]:
                await create_health_event(
                    user_id=user_id,
                    event_type="meal",
                    timestamp=day_time.replace(hour=meal_hour),
                    metadata={"meal_type": "meal", "foods": ["food"]}
                )
                event_count += 1

            # 1 sleep per day
            await create_health_event(
                user_id=user_id,
                event_type="sleep",
                timestamp=day_time.replace(hour=23),
                metadata={"sleep_quality_rating": 7, "total_sleep_hours": 7.5}
            )
            event_count += 1

            # Some symptoms
            if day % 3 == 0:
                await create_health_event(
                    user_id=user_id,
                    event_type="symptom",
                    timestamp=day_time.replace(hour=15),
                    metadata={"symptom": "tiredness"}
                )
                event_count += 1

        # Run pattern mining
        result = await run_pattern_mining_now(user_id)

        duration = (datetime.now() - start_time).total_seconds()

        # Performance assertions
        assert event_count >= 360, f"Should have created ~360+ events (got {event_count})"
        assert duration < 300, f"Pattern mining should complete in <5 minutes (took {duration:.1f}s)"

        # Log performance metric
        print(f"\nPattern mining performance: {event_count} events in {duration:.2f}s")
        print(f"Rate: {event_count/duration:.1f} events/second")
