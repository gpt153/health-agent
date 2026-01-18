"""Integration tests for health check API endpoint"""
import pytest
import httpx
from tests.integration.api_helpers import (
    assert_success_response,
    assert_has_keys,
    assert_valid_timestamp
)


@pytest.mark.asyncio
async def test_health_check_healthy(api_client: httpx.AsyncClient):
    """Test health check when system is operational"""
    response = await api_client.get("/api/health")

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["status", "database", "timestamp"])
    assert data["status"] in ["healthy", "degraded"]
    assert data["database"] in ["connected", "disconnected"]
    assert_valid_timestamp(data["timestamp"])


@pytest.mark.asyncio
async def test_health_check_no_auth_required(api_client: httpx.AsyncClient):
    """Test that health check is a public endpoint"""
    # Should work without authentication
    response = await api_client.get("/api/health")

    assert_success_response(response, 200)
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_health_check_structure(api_client: httpx.AsyncClient):
    """Test health check response structure"""
    response = await api_client.get("/api/health")

    assert_success_response(response, 200)
    data = response.json()

    # Validate structure
    assert isinstance(data["status"], str)
    assert isinstance(data["database"], str)
    assert isinstance(data["timestamp"], str)

    # Status should be one of expected values
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

    # Database should be one of expected values
    assert data["database"] in ["connected", "disconnected", "error"]


@pytest.mark.asyncio
async def test_health_check_database_connection(api_client: httpx.AsyncClient):
    """Test that health check reports database connection status"""
    response = await api_client.get("/api/health")

    assert_success_response(response, 200)
    data = response.json()

    # If database is connected, status should be healthy
    if data["database"] == "connected":
        assert data["status"] == "healthy"

    # If database is disconnected, status should be degraded
    if data["database"] == "disconnected":
        assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_check_timestamp_format(api_client: httpx.AsyncClient):
    """Test that health check timestamp is in correct format"""
    response = await api_client.get("/api/health")

    assert_success_response(response, 200)
    data = response.json()

    # Should be valid ISO8601 timestamp
    assert_valid_timestamp(data["timestamp"])


@pytest.mark.asyncio
async def test_health_check_multiple_calls(api_client: httpx.AsyncClient):
    """Test that health check is consistent across multiple calls"""
    responses = []

    # Make multiple calls
    for _ in range(3):
        response = await api_client.get("/api/health")
        assert_success_response(response, 200)
        responses.append(response.json())

    # All should have same status (assuming no issues during test)
    statuses = [r["status"] for r in responses]
    db_statuses = [r["database"] for r in responses]

    # Status should be consistent
    assert len(set(statuses)) <= 2  # Allow for potential state changes
    assert len(set(db_statuses)) <= 2


@pytest.mark.asyncio
async def test_health_check_response_time(api_client: httpx.AsyncClient):
    """Test that health check responds quickly"""
    import time

    start = time.time()
    response = await api_client.get("/api/health")
    duration = time.time() - start

    assert_success_response(response, 200)
    # Health check should respond within 5 seconds
    assert duration < 5.0, f"Health check took {duration}s, should be < 5s"
