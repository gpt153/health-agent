"""Shared fixtures for API integration tests"""
import pytest
import httpx
from typing import AsyncGenerator, Dict, List
import os
from uuid import uuid4


@pytest.fixture
def api_base_url() -> str:
    """Base URL for API testing"""
    return os.getenv("API_BASE_URL", "http://localhost:8080")


@pytest.fixture
def test_api_key() -> str:
    """Test API key for authentication"""
    return os.getenv("TEST_API_KEY", "test_key_123")


@pytest.fixture
def auth_headers(test_api_key: str) -> Dict[str, str]:
    """Valid authentication headers"""
    return {"Authorization": f"Bearer {test_api_key}"}


@pytest.fixture
async def api_client(api_base_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client with base configuration"""
    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=30.0,
        follow_redirects=True
    ) as client:
        yield client


@pytest.fixture
def unique_user_id() -> str:
    """Generate unique user ID for test isolation"""
    return f"test_user_{uuid4().hex[:12]}"


@pytest.fixture
def multiple_user_ids() -> List[str]:
    """Generate multiple unique user IDs"""
    return [f"test_user_{uuid4().hex[:12]}" for _ in range(3)]


@pytest.fixture
async def test_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    unique_user_id: str
) -> AsyncGenerator[str, None]:
    """
    Create a test user and clean it up after the test.

    Yields the user_id for use in tests.
    """
    user_id = unique_user_id

    # Create user
    response = await api_client.post(
        "/api/v1/users",
        json={"user_id": user_id},
        headers=auth_headers
    )

    # Yield for test usage
    yield user_id

    # Cleanup: Delete user after test
    try:
        await api_client.delete(
            f"/api/v1/users/{user_id}",
            headers=auth_headers
        )
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
async def test_users(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    multiple_user_ids: List[str]
) -> AsyncGenerator[List[str], None]:
    """
    Create multiple test users and clean them up after the test.

    Yields list of user_ids for use in tests.
    """
    user_ids = multiple_user_ids

    # Create users
    for user_id in user_ids:
        await api_client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=auth_headers
        )

    # Yield for test usage
    yield user_ids

    # Cleanup: Delete users after test
    for user_id in user_ids:
        try:
            await api_client.delete(
                f"/api/v1/users/{user_id}",
                headers=auth_headers
            )
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture
async def cleanup_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """
    Helper fixture for manual user cleanup.

    Usage:
        async def test_something(cleanup_user):
            user_id = "my_test_user"
            # ... test code ...
            await cleanup_user(user_id)
    """
    async def _cleanup(user_id: str):
        try:
            await api_client.delete(
                f"/api/v1/users/{user_id}",
                headers=auth_headers
            )
        except Exception:
            pass

    return _cleanup
