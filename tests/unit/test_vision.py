"""Unit tests for vision AI (mocked)"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.utils.vision import analyze_food_photo, _get_mock_result
from src.models.food import VisionAnalysisResult


def test_mock_result():
    """Test that mock result is properly formatted"""
    result = _get_mock_result()

    assert isinstance(result, VisionAnalysisResult)
    assert len(result.foods) > 0
    assert result.confidence in ["low", "medium", "high"]
    assert isinstance(result.clarifying_questions, list)


@pytest.mark.asyncio
@patch("src.utils.vision.VISION_MODEL", "openai:gpt-4o-mini")
@patch("src.utils.vision.analyze_with_openai")
async def test_analyze_food_photo_routes_to_openai(mock_openai):
    """Test that OpenAI model routes correctly"""
    # Setup mock
    mock_result = _get_mock_result()
    mock_openai.return_value = mock_result

    # Create temporary test image
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"fake image data")
        tmp_path = tmp.name

    try:
        result = await analyze_food_photo(tmp_path)

        # Verify OpenAI was called
        mock_openai.assert_called_once()
        assert isinstance(result, VisionAnalysisResult)

    finally:
        Path(tmp_path).unlink()


@pytest.mark.asyncio
@patch("src.utils.vision.VISION_MODEL", "anthropic:claude-3-5-sonnet-latest")
@patch("src.utils.vision.analyze_with_anthropic")
async def test_analyze_food_photo_routes_to_anthropic(mock_anthropic):
    """Test that Anthropic model routes correctly"""
    # Setup mock
    mock_result = _get_mock_result()
    mock_anthropic.return_value = mock_result

    # Create temporary test image
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"fake image data")
        tmp_path = tmp.name

    try:
        result = await analyze_food_photo(tmp_path)

        # Verify Anthropic was called
        mock_anthropic.assert_called_once()
        assert isinstance(result, VisionAnalysisResult)

    finally:
        Path(tmp_path).unlink()


@pytest.mark.asyncio
@patch("src.utils.vision.VISION_MODEL", "unknown:model")
async def test_analyze_food_photo_fallback():
    """Test fallback to mock data for unknown model"""
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"fake image data")
        tmp_path = tmp.name

    try:
        result = await analyze_food_photo(tmp_path)

        # Should return mock result
        assert isinstance(result, VisionAnalysisResult)
        assert result.confidence == "low"

    finally:
        Path(tmp_path).unlink()
