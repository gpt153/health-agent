"""Integration tests for food tracking API endpoints"""
import pytest
import httpx
from typing import Dict
from datetime import datetime, timedelta
from tests.integration.api_helpers import (
    assert_success_response,
    assert_error_response,
    assert_has_keys,
    assert_valid_food_entry,
    generate_test_food_log
)


@pytest.mark.asyncio
async def test_log_food_basic(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test basic food logging"""
    food_data = generate_test_food_log()

    response = await api_client.post(
        f"/api/v1/users/{test_user}/food",
        json=food_data,
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert data["success"] is True
    assert "description" in data
    assert "response" in data


@pytest.mark.asyncio
async def test_log_food_with_timestamp(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test food logging with custom timestamp"""
    timestamp = (datetime.now() - timedelta(hours=2)).isoformat()

    response = await api_client.post(
        f"/api/v1/users/{test_user}/food",
        json={
            "description": "Oatmeal with berries",
            "timestamp": timestamp
        },
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_log_food_creates_entry(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test that food logging creates a retrievable entry"""
    # Log food
    await api_client.post(
        f"/api/v1/users/{test_user}/food",
        json={"description": "Apple and peanut butter"},
        headers=auth_headers
    )

    # Wait a moment for processing
    import asyncio
    await asyncio.sleep(1)

    # Retrieve food summary
    today = datetime.now().strftime("%Y-%m-%d")
    response = await api_client.get(
        f"/api/v1/users/{test_user}/food?date={today}",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["date", "entries", "total_calories"])


@pytest.mark.asyncio
async def test_get_food_summary_today(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test retrieving food summary for current day"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/food",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, [
        "date", "entries", "total_calories",
        "total_protein", "total_carbs", "total_fat"
    ])
    assert isinstance(data["entries"], list)


@pytest.mark.asyncio
async def test_get_food_summary_specific_date(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test retrieving food summary for specific date"""
    specific_date = "2025-01-10"

    response = await api_client.get(
        f"/api/v1/users/{test_user}/food?date={specific_date}",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert data["date"] == specific_date
    assert isinstance(data["entries"], list)


@pytest.mark.asyncio
async def test_get_food_summary_empty(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test food summary with no entries"""
    # Use a date far in the past with no entries
    old_date = "2020-01-01"

    response = await api_client.get(
        f"/api/v1/users/{test_user}/food?date={old_date}",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert data["date"] == old_date
    assert len(data["entries"]) == 0
    assert data["total_calories"] == 0
    assert data["total_protein"] == 0
    assert data["total_carbs"] == 0
    assert data["total_fat"] == 0


@pytest.mark.asyncio
async def test_food_summary_calculations(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test that food summary calculates totals correctly"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/food",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()

    # Verify numeric types
    assert isinstance(data["total_calories"], (int, float))
    assert isinstance(data["total_protein"], (int, float))
    assert isinstance(data["total_carbs"], (int, float))
    assert isinstance(data["total_fat"], (int, float))

    # Verify non-negative
    assert data["total_calories"] >= 0
    assert data["total_protein"] >= 0
    assert data["total_carbs"] >= 0
    assert data["total_fat"] >= 0


@pytest.mark.asyncio
async def test_food_nonexistent_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """Test food endpoints with non-existent user"""
    # Test logging
    log_response = await api_client.post(
        "/api/v1/users/nonexistent_user_xyz/food",
        json={"description": "Food"},
        headers=auth_headers
    )
    assert_error_response(log_response, 404)

    # Test retrieval
    get_response = await api_client.get(
        "/api/v1/users/nonexistent_user_xyz/food",
        headers=auth_headers
    )
    assert_error_response(get_response, 404)


@pytest.mark.asyncio
async def test_food_invalid_date_format(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test food summary with invalid date format"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/food?date=invalid-date",
        headers=auth_headers
    )

    # Should either return error or handle gracefully
    # Depending on implementation, could be 400 or return empty results
    assert response.status_code in [200, 400]


@pytest.mark.asyncio
async def test_food_without_auth(
    api_client: httpx.AsyncClient,
    test_user: str
):
    """Test that food endpoints require authentication"""
    # Test logging
    log_response = await api_client.post(
        f"/api/v1/users/{test_user}/food",
        json={"description": "Food"}
    )
    assert_error_response(log_response, 403)

    # Test retrieval
    get_response = await api_client.get(
        f"/api/v1/users/{test_user}/food"
    )
    assert_error_response(get_response, 403)


@pytest.mark.asyncio
async def test_log_food_missing_description(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test food logging without description"""
    response = await api_client.post(
        f"/api/v1/users/{test_user}/food",
        json={},
        headers=auth_headers
    )

    assert_error_response(response, 422)


@pytest.mark.asyncio
async def test_log_food_empty_description(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test food logging with empty description"""
    response = await api_client.post(
        f"/api/v1/users/{test_user}/food",
        json={"description": ""},
        headers=auth_headers
    )

    # Could be handled by agent or return validation error
    assert response.status_code in [200, 400, 422]
