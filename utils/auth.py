"""
API Key authentication for the Background Removal API.
"""
import os
import logging
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)


async def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    """
    Validate the X-API-Key header against the configured API_KEY.
    Raises 401 if missing or invalid.
    """
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        logger.warning("API_KEY environment variable is not set")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    if not x_api_key or x_api_key.strip() != expected_key.strip():
        logger.warning("Invalid or missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key
