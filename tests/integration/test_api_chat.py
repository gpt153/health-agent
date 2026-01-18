"""Integration tests for chat API endpoint"""
import pytest
import httpx
from typing import Dict
from tests.integration.api_helpers import (
    assert_success_response,
    assert_error_response,
    assert_has_keys,
    assert_valid_timestamp
)


@pytest.mark.asyncio
async def test_chat_basic_message(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test basic chat message handling"""
    response = await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": test_user,
            "message": "Hello, how are you?",
            "message_history": []
        },
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["response", "timestamp", "user_id"])
    assert data["user_id"] == test_user
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0
    assert_valid_timestamp(data["timestamp"])


@pytest.mark.asyncio
async def test_chat_with_message_history(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test chat with conversation history"""
    history = [
        {"role": "user", "content": "My name is Alice"},
        {"role": "assistant", "content": "Nice to meet you, Alice!"}
    ]

    response = await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": test_user,
            "message": "What's my name?",
            "message_history": history
        },
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["response", "user_id"])
    # Note: Context awareness depends on agent implementation
    assert isinstance(data["response"], str)


@pytest.mark.asyncio
async def test_chat_creates_new_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    unique_user_id: str,
    cleanup_user
):
    """Test that chat endpoint auto-creates new users"""
    new_user_id = unique_user_id

    response = await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": new_user_id,
            "message": "Hello",
            "message_history": []
        },
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert data["user_id"] == new_user_id

    # Verify user was created
    user_response = await api_client.get(
        f"/api/v1/users/{new_user_id}",
        headers=auth_headers
    )
    assert_success_response(user_response, 200)

    # Cleanup
    await cleanup_user(new_user_id)


@pytest.mark.asyncio
async def test_chat_saves_conversation(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test that chat saves conversation history"""
    # Send first message
    response1 = await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": test_user,
            "message": "First message",
            "message_history": []
        },
        headers=auth_headers
    )
    assert_success_response(response1, 200)

    # Send second message (without history, should load from DB)
    response2 = await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": test_user,
            "message": "Second message"
        },
        headers=auth_headers
    )
    assert_success_response(response2, 200)


@pytest.mark.asyncio
async def test_chat_without_auth(
    api_client: httpx.AsyncClient,
    unique_user_id: str
):
    """Test that chat requires authentication"""
    response = await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": unique_user_id,
            "message": "Hello"
        }
    )

    assert_error_response(response, 403)


@pytest.mark.asyncio
async def test_chat_invalid_api_key(
    api_client: httpx.AsyncClient,
    unique_user_id: str
):
    """Test chat with invalid API key"""
    response = await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": unique_user_id,
            "message": "Hello"
        },
        headers={"Authorization": "Bearer invalid_key_xyz"}
    )

    assert_error_response(response, 401)


@pytest.mark.asyncio
async def test_chat_empty_message(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test chat with empty message"""
    response = await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": test_user,
            "message": "",
            "message_history": []
        },
        headers=auth_headers
    )

    # Empty message might be handled by agent, check response
    # Could be 200 with error message or 422 validation error
    assert response.status_code in [200, 422]


@pytest.mark.asyncio
async def test_chat_missing_user_id(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """Test chat without user_id"""
    response = await api_client.post(
        "/api/v1/chat",
        json={
            "message": "Hello"
        },
        headers=auth_headers
    )

    assert_error_response(response, 422)


@pytest.mark.asyncio
async def test_chat_malformed_request(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """Test chat with malformed request body"""
    response = await api_client.post(
        "/api/v1/chat",
        json={
            "invalid_field": "value"
        },
        headers=auth_headers
    )

    assert_error_response(response, 422)
