"""Tests for chat API endpoint"""
import pytest
import httpx
from datetime import datetime


@pytest.mark.asyncio
async def test_chat_endpoint():
    """Test basic chat functionality"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        response = await client.post(
            "/api/v1/chat",
            json={
                "user_id": "test_user_001",
                "message": "Hello, how are you?",
                "message_history": []
            },
            headers={"Authorization": "Bearer test_key_123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["user_id"] == "test_user_001"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_chat_with_history():
    """Test chat with conversation history"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        history = [
            {"role": "user", "content": "My name is Alice"},
            {"role": "assistant", "content": "Nice to meet you, Alice!"}
        ]

        response = await client.post(
            "/api/v1/chat",
            json={
                "user_id": "test_user_001",
                "message": "What's my name?",
                "message_history": history
            },
            headers={"Authorization": "Bearer test_key_123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "alice" in data["response"].lower()


@pytest.mark.asyncio
async def test_chat_without_api_key():
    """Test that chat requires authentication"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        response = await client.post(
            "/api/v1/chat",
            json={
                "user_id": "test_user_001",
                "message": "Hello"
            }
        )

        assert response.status_code == 403  # Forbidden without API key


@pytest.mark.asyncio
async def test_chat_invalid_api_key():
    """Test chat with invalid API key"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        response = await client.post(
            "/api/v1/chat",
            json={
                "user_id": "test_user_001",
                "message": "Hello"
            },
            headers={"Authorization": "Bearer invalid_key"}
        )

        assert response.status_code == 401  # Unauthorized
