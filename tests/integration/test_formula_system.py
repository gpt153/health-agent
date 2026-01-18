"""
Integration tests for Formula System (End-to-End)
Epic 009 - Phase 3: Food Formulas & Auto-Suggestion

NOTE: These tests require a running PostgreSQL database with migrations applied.
Run with: pytest tests/integration/test_formula_system.py -v --run-integration
"""
import pytest
from datetime import datetime, timedelta
import json

from src.services.formula_detection import get_formula_detection_service
from src.services.formula_suggestions import get_suggestion_service
from src.db.connection import db


@pytest.mark.integration
@pytest.mark.asyncio
class TestFormulaSystemIntegration:
    """
    End-to-end integration tests for the formula system

    These tests verify:
    1. Pattern detection from food logs
    2. Formula creation and storage
    3. Keyword and visual matching
    4. Auto-suggestion functionality
    """

    @pytest.fixture
    async def setup_test_user(self):
        """Setup test user and sample data"""
        test_user_id = "test_user_formulas"

        # Clean up any existing test data
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM food_formulas WHERE user_id = %s",
                    (test_user_id,)
                )
                await cur.execute(
                    "DELETE FROM food_entries WHERE user_id = %s",
                    (test_user_id,)
                )
                await conn.commit()

        yield test_user_id

        # Cleanup after test
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM food_formulas WHERE user_id = %s",
                    (test_user_id,)
                )
                await cur.execute(
                    "DELETE FROM food_entries WHERE user_id = %s",
                    (test_user_id,)
                )
                await conn.commit()

    async def test_pattern_detection_workflow(self, setup_test_user):
        """
        Test complete pattern detection workflow:
        1. Create recurring food entries
        2. Detect patterns
        3. Verify formula candidates
        """
        user_id = await setup_test_user

        # Create 3 similar protein shake entries
        shake_foods = [
            {"name": "Protein Powder", "quantity": "30g", "calories": 120},
            {"name": "Banana", "quantity": "1 medium", "calories": 105},
            {"name": "Almond Milk", "quantity": "250ml", "calories": 40}
        ]

        now = datetime.now()
        for i in range(3):
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO food_entries
                        (user_id, foods, total_calories, total_macros, timestamp, notes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            json.dumps(shake_foods),
                            265,
                            json.dumps({"protein": 25, "carbs": 30, "fat": 5}),
                            now - timedelta(days=i),
                            "protein shake"
                        )
                    )
                    await conn.commit()

        # Detect patterns
        service = get_formula_detection_service()
        candidates = await service.detect_formula_candidates(
            user_id=user_id,
            days_back=7,
            min_occurrences=3
        )

        # Verify detection
        assert len(candidates) >= 1
        top_candidate = candidates[0]
        assert top_candidate.occurrence_count == 3
        assert top_candidate.total_calories == 265
        assert top_candidate.confidence_score > 0.7

    async def test_keyword_search(self, setup_test_user):
        """
        Test keyword-based formula search
        """
        user_id = await setup_test_user

        # Create a test formula
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO food_formulas
                    (user_id, name, keywords, foods, total_calories, total_macros)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        "Morning Protein Shake",
                        ["protein shake", "shake", "morning shake"],
                        json.dumps([{"name": "Protein Powder"}]),
                        250,
                        json.dumps({"protein": 25})
                    )
                )
                await conn.commit()

        # Test search
        service = get_formula_detection_service()
        results = await service.find_formulas_by_keyword(
            user_id=user_id,
            keyword="shake",
            limit=5
        )

        assert len(results) == 1
        assert results[0]["name"] == "Morning Protein Shake"
        assert results[0]["match_score"] > 0.5

    async def test_suggestion_system(self, setup_test_user):
        """
        Test auto-suggestion system
        """
        user_id = await setup_test_user

        # Create a formula
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                formula_id = await cur.execute(
                    """
                    INSERT INTO food_formulas
                    (user_id, name, keywords, foods, total_calories, total_macros)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        "Breakfast Bowl",
                        ["breakfast", "bowl", "oatmeal"],
                        json.dumps([{"name": "Oatmeal"}]),
                        300,
                        json.dumps({"protein": 10, "carbs": 50, "fat": 5})
                    )
                )
                formula_id = (await cur.fetchone())["id"]

                # Log some usage at breakfast time (8 AM)
                for i in range(3):
                    # Create food entry
                    await cur.execute(
                        """
                        INSERT INTO food_entries
                        (user_id, foods, total_calories, total_macros, timestamp)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            user_id,
                            json.dumps([{"name": "Oatmeal"}]),
                            300,
                            json.dumps({"protein": 10}),
                            datetime.now().replace(hour=8, minute=0) - timedelta(days=i)
                        )
                    )
                    entry_id = (await cur.fetchone())["id"]

                    # Log formula usage
                    await cur.execute(
                        """
                        INSERT INTO formula_usage_log
                        (formula_id, food_entry_id, user_id, match_method, used_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            formula_id,
                            entry_id,
                            user_id,
                            "keyword",
                            datetime.now().replace(hour=8, minute=0) - timedelta(days=i)
                        )
                    )

                await conn.commit()

        # Test suggestion at breakfast time
        service = get_suggestion_service()
        suggestions = await service.suggest_formulas(
            user_id=user_id,
            text="breakfast",
            current_time=datetime.now().replace(hour=8, minute=30)
        )

        # Should suggest the breakfast formula
        assert len(suggestions) > 0


@pytest.mark.integration
def test_migration_022_applied():
    """
    Verify that migration 022 has been applied successfully

    This test checks that the required tables and functions exist.
    """
    import asyncio

    async def check_schema():
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Check food_formulas table exists
                await cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'food_formulas'
                    )
                    """
                )
                result = await cur.fetchone()
                assert result[0], "food_formulas table not found"

                # Check formula_usage_log table exists
                await cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'formula_usage_log'
                    )
                    """
                )
                result = await cur.fetchone()
                assert result[0], "formula_usage_log table not found"

                # Check search function exists
                await cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM pg_proc
                        WHERE proname = 'search_formulas_by_keyword'
                    )
                    """
                )
                result = await cur.fetchone()
                assert result[0], "search_formulas_by_keyword function not found"

    asyncio.run(check_schema())


if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/test_formula_system.py -v
    pytest.main([__file__, "-v", "--run-integration"])
