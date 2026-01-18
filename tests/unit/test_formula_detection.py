"""
Unit tests for Formula Detection Service
Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json

from src.services.formula_detection import (
    FormulaDetectionService,
    FormulaCandidate,
    FormulaDetectionError,
    get_formula_detection_service
)


class TestFormulaDetectionService:
    """Test suite for FormulaDetectionService"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return FormulaDetectionService()

    @pytest.fixture
    def sample_food_entries(self):
        """Sample food entries for pattern detection"""
        now = datetime.now()
        return [
            {
                "id": "uuid-1",
                "foods": json.dumps([
                    {"name": "Protein Powder", "quantity": "30g", "calories": 120},
                    {"name": "Banana", "quantity": "1 medium", "calories": 105},
                    {"name": "Almond Milk", "quantity": "250ml", "calories": 40}
                ]),
                "total_calories": 265,
                "total_macros": json.dumps({"protein": 25, "carbs": 30, "fat": 5}),
                "timestamp": now - timedelta(days=1),
                "photo_path": "/photos/shake1.jpg",
                "notes": "morning protein shake"
            },
            {
                "id": "uuid-2",
                "foods": json.dumps([
                    {"name": "Protein Powder", "quantity": "30g", "calories": 120},
                    {"name": "Banana", "quantity": "1 medium", "calories": 105},
                    {"name": "Almond Milk", "quantity": "255ml", "calories": 40}  # Slight variation
                ]),
                "total_calories": 265,
                "total_macros": json.dumps({"protein": 25, "carbs": 30, "fat": 5}),
                "timestamp": now - timedelta(days=5),
                "photo_path": "/photos/shake2.jpg",
                "notes": "protein shake"
            },
            {
                "id": "uuid-3",
                "foods": json.dumps([
                    {"name": "Protein Powder", "quantity": "30g", "calories": 120},
                    {"name": "Banana", "quantity": "1 medium", "calories": 105},
                    {"name": "Almond Milk", "quantity": "250ml", "calories": 40}
                ]),
                "total_calories": 265,
                "total_macros": json.dumps({"protein": 25, "carbs": 30, "fat": 5}),
                "timestamp": now - timedelta(days=10),
                "photo_path": "/photos/shake3.jpg",
                "notes": "usual shake"
            }
        ]

    def test_normalize_quantity(self, service):
        """Test quantity normalization for grouping"""
        # Test rounding to nearest 10
        assert service._normalize_quantity("250ml") == "250ml"
        assert service._normalize_quantity("255ml") == "260ml"  # Rounds up
        assert service._normalize_quantity("245ml") == "240ml"  # Rounds down

        # Test with different units
        assert service._normalize_quantity("30g") == "30g"
        assert service._normalize_quantity("35g") == "40g"

        # Test edge cases
        assert service._normalize_quantity("") == ""
        assert service._normalize_quantity("1 medium") == "1 medium"

    def test_create_group_key(self, service):
        """Test group key generation for similar meals"""
        foods1 = [
            {"name": "Protein Powder", "quantity": "30g"},
            {"name": "Banana", "quantity": "1 medium"}
        ]
        foods2 = [
            {"name": "Banana", "quantity": "1 medium"},
            {"name": "Protein Powder", "quantity": "30g"}
        ]

        # Should produce same key regardless of order (sorted)
        key1 = service._create_group_key(foods1)
        key2 = service._create_group_key(foods2)

        # Keys should match after sorting
        assert key1 == key2

    def test_group_similar_meals(self, service, sample_food_entries):
        """Test meal grouping logic"""
        groups = service._group_similar_meals(sample_food_entries)

        # All three shakes should be grouped together (minor variations allowed)
        assert len(groups) == 1

        # Group should contain all 3 entries
        group_entries = list(groups.values())[0]
        assert len(group_entries) == 3

    def test_calculate_consistency(self, service):
        """Test consistency score calculation"""
        # Perfect consistency
        entries_perfect = [
            {"total_calories": 250},
            {"total_calories": 250},
            {"total_calories": 250}
        ]
        score = service._calculate_consistency(entries_perfect)
        assert score == 1.0

        # High consistency (5% variation)
        entries_high = [
            {"total_calories": 250},
            {"total_calories": 255},
            {"total_calories": 245}
        ]
        score = service._calculate_consistency(entries_high)
        assert score > 0.8

        # Low consistency (30% variation)
        entries_low = [
            {"total_calories": 200},
            {"total_calories": 300},
            {"total_calories": 250}
        ]
        score = service._calculate_consistency(entries_low)
        assert score < 0.5

    def test_calculate_recency(self, service):
        """Test recency score calculation"""
        now = datetime.now()

        # Very recent (today)
        entries_recent = [
            {"timestamp": now}
        ]
        score = service._calculate_recency(entries_recent)
        assert score == 1.0

        # 45 days ago (mid-range)
        entries_mid = [
            {"timestamp": now - timedelta(days=45)}
        ]
        score = service._calculate_recency(entries_mid)
        assert 0.3 < score < 0.7

        # 90 days ago (old)
        entries_old = [
            {"timestamp": now - timedelta(days=90)}
        ]
        score = service._calculate_recency(entries_old)
        assert score == 0.0

    def test_generate_formula_name(self, service):
        """Test formula name generation"""
        # Single food item
        foods_single = [{"name": "Protein Shake"}]
        template = {"notes": ""}
        name = service._generate_formula_name(foods_single, template)
        assert name == "Protein Shake"

        # Multiple items (2-3)
        foods_multi = [
            {"name": "Protein Powder"},
            {"name": "Banana"}
        ]
        name = service._generate_formula_name(foods_multi, template)
        assert "Protein" in name and "Banana" in name

        # Use notes if available
        template_with_notes = {"notes": "morning protein shake delicious"}
        name = service._generate_formula_name(foods_multi, template_with_notes)
        assert "Morning Protein Shake Delicious" == name

        # Many items (>3)
        foods_many = [
            {"name": f"Food {i}"} for i in range(5)
        ]
        name = service._generate_formula_name(foods_many, template)
        assert "5-Item Meal" == name

    def test_generate_keywords(self, service):
        """Test keyword generation"""
        foods = [
            {"name": "Protein Powder"},
            {"name": "Almond Milk"}
        ]
        template = {"notes": "morning protein shake"}

        keywords = service._generate_keywords(foods, template)

        # Should include food names
        assert "protein powder" in keywords
        assert "almond milk" in keywords

        # Should include individual words
        assert "protein" in keywords
        assert "almond" in keywords

        # Should include notes keywords
        assert "morning" in keywords
        assert "shake" in keywords

        # Should be deduplicated
        assert len(keywords) == len(set(keywords))

        # Should be limited to 10
        assert len(keywords) <= 10

    @pytest.mark.asyncio
    async def test_detect_formula_candidates_insufficient_data(self, service):
        """Test detection with insufficient entries"""
        with patch.object(service, '_group_similar_meals', return_value={}):
            with patch('src.services.formula_detection.db') as mock_db:
                mock_cursor = AsyncMock()
                mock_cursor.fetchall = AsyncMock(return_value=[])
                mock_conn = AsyncMock()
                mock_conn.cursor = AsyncMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_cursor),
                    __aexit__=AsyncMock()
                ))
                mock_db.connection = AsyncMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))

                candidates = await service.detect_formula_candidates(
                    user_id="test_user",
                    days_back=90,
                    min_occurrences=3
                )

                assert candidates == []

    @pytest.mark.asyncio
    async def test_fuzzy_match_formula_exact_match(self, service):
        """Test fuzzy matching with exact keyword match"""
        mock_formulas = [
            {
                "id": "formula-1",
                "name": "Morning Protein Shake",
                "keywords": ["protein shake", "shake", "morning shake"],
                "foods": [{"name": "Protein Powder"}],
                "total_calories": 250,
                "total_macros": {"protein": 25},
                "times_used": 5
            }
        ]

        with patch('src.services.formula_detection.db') as mock_db:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall = AsyncMock(return_value=mock_formulas)
            mock_conn = AsyncMock()
            mock_conn.cursor = AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_cursor),
                __aexit__=AsyncMock()
            ))
            mock_db.connection = AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock()
            ))

            match = await service.fuzzy_match_formula(
                user_id="test_user",
                text="protein shake",
                threshold=0.6
            )

            assert match is not None
            assert match["name"] == "Morning Protein Shake"
            assert match["match_score"] == 1.0  # Exact match

    @pytest.mark.asyncio
    async def test_fuzzy_match_formula_no_match(self, service):
        """Test fuzzy matching with no match"""
        mock_formulas = [
            {
                "id": "formula-1",
                "name": "Morning Protein Shake",
                "keywords": ["protein shake"],
                "foods": [],
                "total_calories": 250,
                "total_macros": {},
                "times_used": 5
            }
        ]

        with patch('src.services.formula_detection.db') as mock_db:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall = AsyncMock(return_value=mock_formulas)
            mock_conn = AsyncMock()
            mock_conn.cursor = AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_cursor),
                __aexit__=AsyncMock()
            ))
            mock_db.connection = AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock()
            ))

            match = await service.fuzzy_match_formula(
                user_id="test_user",
                text="chicken salad",  # Completely different
                threshold=0.6
            )

            assert match is None

    def test_create_candidate_from_group(self, service, sample_food_entries):
        """Test formula candidate creation from entry group"""
        candidate = service._create_candidate_from_group(sample_food_entries)

        assert isinstance(candidate, FormulaCandidate)
        assert candidate.occurrence_count == 3
        assert candidate.total_calories == 265
        assert 0.0 <= candidate.confidence_score <= 1.0
        assert len(candidate.entry_ids) == 3
        assert candidate.suggested_name != ""
        assert len(candidate.suggested_keywords) > 0

    def test_singleton_service(self):
        """Test that get_formula_detection_service returns singleton"""
        service1 = get_formula_detection_service()
        service2 = get_formula_detection_service()

        assert service1 is service2


class TestFormulaCandidate:
    """Test FormulaCandidate dataclass"""

    def test_formula_candidate_creation(self):
        """Test creating a formula candidate"""
        candidate = FormulaCandidate(
            foods=[{"name": "Test Food"}],
            total_calories=200,
            total_macros={"protein": 20},
            occurrence_count=5,
            entry_ids=["id1", "id2"],
            confidence_score=0.85,
            suggested_name="Test Formula",
            suggested_keywords=["test", "formula"]
        )

        assert candidate.total_calories == 200
        assert candidate.occurrence_count == 5
        assert candidate.confidence_score == 0.85


@pytest.mark.asyncio
class TestFormulaDetectionIntegration:
    """Integration tests requiring database/service mocks"""

    async def test_find_formulas_by_keyword_with_results(self):
        """Test keyword search with results"""
        service = FormulaDetectionService()

        mock_results = [
            {
                "formula_id": "uuid-1",
                "name": "Protein Shake",
                "keywords": ["shake", "protein"],
                "foods": [{"name": "Protein Powder"}],
                "total_calories": 250,
                "total_macros": {"protein": 25},
                "times_used": 10,
                "match_score": 1.0
            }
        ]

        with patch('src.services.formula_detection.db') as mock_db:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall = AsyncMock(return_value=mock_results)
            mock_conn = AsyncMock()
            mock_conn.cursor = AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_cursor),
                __aexit__=AsyncMock()
            ))
            mock_db.connection = AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock()
            ))

            formulas = await service.find_formulas_by_keyword(
                user_id="test_user",
                keyword="shake",
                limit=5
            )

            assert len(formulas) == 1
            assert formulas[0]["name"] == "Protein Shake"
            assert formulas[0]["match_score"] == 1.0

    async def test_find_formulas_by_keyword_no_results(self):
        """Test keyword search with no results"""
        service = FormulaDetectionService()

        with patch('src.services.formula_detection.db') as mock_db:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall = AsyncMock(return_value=[])
            mock_conn = AsyncMock()
            mock_conn.cursor = AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_cursor),
                __aexit__=AsyncMock()
            ))
            mock_db.connection = AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock()
            ))

            formulas = await service.find_formulas_by_keyword(
                user_id="test_user",
                keyword="nonexistent",
                limit=5
            )

            assert len(formulas) == 0
