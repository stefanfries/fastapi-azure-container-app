"""
API key security dependency for FinHub API.

All data endpoints require a valid X-API-Key header.
The expected key is read from the API_KEY environment variable.

If no API_KEY is configured (e.g. in local development), the dependency
passes through without checking — allowing unrestricted local access.
To require a key even locally, set API_KEY in your .env file.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.logging import logger
from app.core.settings import settings

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_API_KEY_HEADER)) -> None:
    """FastAPI dependency that validates the X-API-Key request header.

    Raises HTTP 401 if a key is configured and the provided key does not match.
    Passes silently if no key is configured (development / open mode).
    """
    configured_key = settings.auth.api_key
    if configured_key is None or configured_key.get_secret_value() == "":
        logger.debug("No API key configured — running in open mode")
        return

    if api_key != configured_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
