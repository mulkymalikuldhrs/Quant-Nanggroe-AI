"""API Key Authentication Dependency for FastAPI.

Implements the X-API-Key header check for trading endpoints.
All trading routes MUST use this dependency to ensure that
only authenticated requests can place or manage orders.

P0-1 SAFETY: This module is the gatekeeper for all trading operations.
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from quant_nanggroe.config import get_settings

logger = logging.getLogger(__name__)

# ── API Key Header Definition ──────────────────────────────────────

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API key for trading endpoint authentication. "
    "Required when REQUIRE_AUTH is enabled (default).",
)


async def verify_api_key(
    request: Request,
    api_key: str = Security(api_key_header),
) -> str:
    """Verify the X-API-Key header against configured valid keys.

    This is a FastAPI Depends() dependency. Add it to any route
    that requires authentication.

    If REQUIRE_AUTH is False (development mode), the check is bypassed
    with a warning log.

    Args:
        request: The incoming HTTP request.
        api_key: The value from the X-API-Key header.

    Returns:
        The validated API key string.

    Raises:
        HTTPException 401: If no API key is provided.
        HTTPException 403: If the API key is invalid.
    """
    settings = get_settings()

    # If auth is disabled (development mode), bypass the check
    if not settings.require_auth:
        logger.warning(
            "AUTH BYPASSED: require_auth is False. "
            "Request from %s to %s %s — no API key required.",
            request.client.host if request.client else "unknown",
            request.method,
            request.url.path,
        )
        return "auth_disabled_dev_mode"

    # Auth is required — check the key
    if api_key is None:
        logger.warning(
            "AUTH FAILED: No X-API-Key header provided. "
            "Request from %s to %s %s",
            request.client.host if request.client else "unknown",
            request.method,
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required. Provide a valid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    valid_keys = settings.api_keys_list
    if not valid_keys:
        # No API keys configured — this is a SAFETY issue
        logger.critical(
            "AUTH MISCONFIGURED: No API keys configured (QNAI_API_KEYS is empty). "
            "ALL requests are being rejected. Configure API keys or set "
            "QNAI_REQUIRE_AUTH=false for local development."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured. "
            "Set QNAI_API_KEYS environment variable with valid keys.",
        )

    if api_key not in valid_keys:
        logger.warning(
            "AUTH FAILED: Invalid API key provided. "
            "Request from %s to %s %s",
            request.client.host if request.client else "unknown",
            request.method,
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return api_key
