"""FastAPI auth middleware — API key and JWT authentication for all routes.

Provides dependency injection for FastAPI routes with role-based access control.
Supports both API key (X-API-Key header) and JWT Bearer token authentication.

Usage:
    from quant_nanggroe.security.auth_middleware import (
        require_auth, require_role, optional_auth
    )

    @app.post("/api/v1/trade", dependencies=[Depends(require_role("trade"))])
    async def execute_trade(request: TradeRequest, auth: AuthContext = Depends(require_auth)):
        ...
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from quant_nanggroe.security.auth import (
    APIKeyAuth,
    AuthResult,
    JWTAuth,
    UserRole,
    _ROLE_PERMISSIONS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security schemes
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Auth provider initialization
# ---------------------------------------------------------------------------

_auth_initialized = False
_api_key_auth: Optional[APIKeyAuth] = None
_jwt_auth: Optional[JWTAuth] = None


def _init_auth() -> None:
    """Initialize auth providers from environment configuration."""
    global _auth_initialized, _api_key_auth, _jwt_auth
    if _auth_initialized:
        return

    # Initialize API key auth
    _api_key_auth = APIKeyAuth()

    # Load API keys from environment (comma-separated: key1:user1:role1,key2:user2:role2)
    api_keys_str = os.getenv("QNAI_API_KEYS", "")
    if api_keys_str:
        for entry in api_keys_str.split(","):
            parts = entry.strip().split(":")
            if len(parts) == 3:
                key, user_id, role_name = parts
                try:
                    role = UserRole(role_name.lower())
                    _api_key_auth.add_key(key, user_id, role)
                except ValueError:
                    logger.warning("Invalid role '%s' for API key user '%s'", role_name, user_id)

    # If no API keys configured, add a default admin key for development
    if _api_key_auth.key_count == 0:
        dev_key = os.getenv("QNAI_DEV_API_KEY", "qnai-dev-admin-key")
        _api_key_auth.add_key(dev_key, "dev-admin", UserRole.ADMIN)
        logger.warning(
            "No API keys configured. Using development key. "
            "Set QNAI_API_KEYS env var for production."
        )

    # Initialize JWT auth
    jwt_secret = os.getenv("QNAI_JWT_SECRET", "")
    if not jwt_secret:
        logger.warning(
            "QNAI_JWT_SECRET not set. JWT auth disabled. "
            "Set QNAI_JWT_SECRET for production."
        )
    else:
        _jwt_auth = JWTAuth(secret_key=jwt_secret, default_ttl=3600)

    _auth_initialized = True


# ---------------------------------------------------------------------------
# Auth context
# ---------------------------------------------------------------------------


class AuthContext:
    """Authenticated user context available in route handlers."""

    def __init__(
        self,
        user_id: str,
        role: UserRole,
        auth_method: str = "api_key",
    ) -> None:
        self.user_id = user_id
        self.role = role
        self.auth_method = auth_method

    @property
    def permissions(self) -> list[str]:
        return _ROLE_PERMISSIONS.get(self.role, [])

    def has_permission(self, action: str) -> bool:
        return action in self.permissions

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def can_trade(self) -> bool:
        return "trade" in self.permissions


# ---------------------------------------------------------------------------
# Dependency functions
# ---------------------------------------------------------------------------


async def require_auth(
    request: Request,
    api_key: str = Security(_api_key_header),
    bearer: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> AuthContext:
    """Require authentication via API key or JWT Bearer token.

    This is the primary auth dependency for protected routes.

    Raises
    ------
    HTTPException
        401 if no valid credentials provided.
    """
    _init_auth()

    # Try API key first
    if api_key and _api_key_auth:
        result = _api_key_auth.authenticate(api_key)
        if result.success and result.role:
            return AuthContext(
                user_id=result.user_id,
                role=result.role,
                auth_method="api_key",
            )

    # Try JWT Bearer token
    if bearer and _jwt_auth:
        try:
            payload = _jwt_auth.validate_token(bearer.credentials)
            return AuthContext(
                user_id=payload.user_id,
                role=payload.role,
                auth_method="jwt",
            )
        except ValueError as e:
            logger.warning("JWT validation failed: %s", e)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid API key or JWT token required. Use X-API-Key header or Authorization: Bearer <token>.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def optional_auth(
    request: Request,
    api_key: str = Security(_api_key_header),
    bearer: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> Optional[AuthContext]:
    """Optional authentication — returns None if no valid credentials.

    Use for endpoints that work for both authenticated and anonymous users
    (e.g., health check, public data).
    """
    try:
        return await require_auth(request, api_key, bearer)
    except HTTPException:
        return None


def require_role(minimum_action: str):
    """Create a dependency that requires a minimum permission level.

    Parameters
    ----------
    minimum_action:
        Required action: ``"read"``, ``"analyze"``, ``"trade"``, or ``"admin"``.

    Returns
    -------
    Callable
        FastAPI dependency function.

    Usage
    -----
        @app.post("/trade", dependencies=[Depends(require_role("trade"))])
        async def execute_trade(auth: AuthContext = Depends(require_auth)):
            ...
    """

    async def _check_role(auth: AuthContext = Depends(require_auth)) -> AuthContext:
        if not auth.has_permission(minimum_action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: '{minimum_action}', your role: '{auth.role.value}'",
            )
        return auth

    return _check_role


# ---------------------------------------------------------------------------
# Login endpoint helper (for JWT token issuance)
# ---------------------------------------------------------------------------


def authenticate_and_issue_token(api_key: str) -> dict:
    """Authenticate with API key and issue a JWT token.

    Parameters
    ----------
    api_key:
        Valid API key string.

    Returns
    -------
    dict
        Token response with access_token, token_type, user info.

    Raises
    ------
    HTTPException
        401 if API key is invalid.
    """
    _init_auth()

    if not _api_key_auth:
        raise HTTPException(status_code=500, detail="Auth not initialized")

    result = _api_key_auth.authenticate(api_key)
    if not result.success or not result.role or not result.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error or "Invalid API key",
        )

    if _jwt_auth:
        token = _jwt_auth.create_token(
            user_id=result.user_id, role=result.role, ttl=3600
        )
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "user_id": result.user_id,
            "role": result.role.value,
        }
    else:
        # JWT not configured — return API key info only
        return {
            "access_token": api_key,
            "token_type": "ApiKey",
            "user_id": result.user_id,
            "role": result.role.value,
            "warning": "JWT not configured. Using API key as token.",
        }
