"""API authentication using API keys"""
import os
import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_api_keys() -> list[str]:
    """Load API keys from environment variable"""
    api_keys_str = os.getenv("API_KEYS", "")
    if not api_keys_str:
        logger.warning("No API_KEYS configured in environment")
        return []
    return [key.strip() for key in api_keys_str.split(",") if key.strip()]


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify API key from Authorization header

    Args:
        credentials: HTTP authorization credentials

    Returns:
        The verified API key

    Raises:
        HTTPException: If API key is invalid
    """
    api_key = credentials.credentials
    valid_keys = get_api_keys()

    if not valid_keys:
        logger.error("No API keys configured - rejecting all requests")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication not configured"
        )

    if api_key not in valid_keys:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    logger.debug(f"API key validated: {api_key[:10]}...")
    return api_key
