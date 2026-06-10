"""
Auth Routes — User registration, login, token management
==========================================================
Provides endpoints for authentication and authorization:
  - POST /register  — Create a new user account
  - POST /login     — Authenticate and receive JWT tokens
  - POST /refresh   — Refresh an access token
  - POST /logout    — Invalidate the current token
  - GET  /me        — Get current user info
  - POST /change-password — Change user password
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from quant_nanggroe_ai.api.auth import (
    AuthService,
    UnauthorizedError,
    ValidationError,
    get_current_user,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════
# Schemas
# ══════════════════════════════════════════════════════════════════════


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    fullname: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.VIEWER


class RegisterResponse(BaseModel):
    """Response schema for user registration."""

    user_id: str
    fullname: str
    email: str
    role: UserRole
    is_active: bool = True


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response schema for JWT token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str = ""
    role: str = ""


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Request schema for password change."""

    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class UserInfoResponse(BaseModel):
    """Response schema for current user info."""

    id: str
    fullname: str
    email: str
    role: str
    is_active: bool


# ══════════════════════════════════════════════════════════════════════
# Singleton AuthService
# ══════════════════════════════════════════════════════════════════════

_auth_service: AuthService | None = None


def _get_auth_service() -> AuthService:
    """Get or create the AuthService singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(auth_provider="local")
    return _auth_service


# ══════════════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════════════


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest) -> RegisterResponse:
    """
    Register a new user account.

    Creates a user with the provided credentials. Returns the user
    information without tokens — the user must login separately.

    Requires no authentication.
    """
    auth = _get_auth_service()
    try:
        user = await auth.register_user(
            fullname=body.fullname,
            password=body.password,
            email=body.email,
            role=body.role,
        )
        logger.info("user_registered", user_id=user.id, email=user.email)
        return RegisterResponse(
            user_id=user.id,
            fullname=user.fullname,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """
    Authenticate user and return JWT token pair.

    Validates email/password credentials and returns both
    an access token (short-lived) and refresh token (long-lived).

    Requires no authentication.
    """
    auth = _get_auth_service()
    try:
        result = await auth.login_with_tokens(
            email=body.email,
            password=body.password,
        )
        user: User = result["user"]
        logger.info("user_login", user_id=user.id, email=user.email)
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            user_id=user.id,
            role=user.role.value,
        )
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        )


@router.post("/refresh", response_model=dict[str, Any])
async def refresh_token(body: RefreshRequest) -> dict[str, Any]:
    """
    Refresh an access token using a valid refresh token.

    Returns a new access token. The refresh token itself is not rotated.
    """
    auth = _get_auth_service()
    try:
        result = await auth.refresh_access_token(body.refresh_token)
        return result
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        )


@router.post("/logout")
async def logout(user: User = Depends(get_current_user)) -> dict[str, str]:
    """
    Logout the current user.

    In a full implementation, this would add the token to a blacklist.
    Currently, it returns a success message as token invalidation
    happens client-side (by discarding the token).
    """
    logger.info("user_logout", user_id=user.id)
    return {"status": "logged_out", "message": "Token discarded successfully"}


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(user: User = Depends(get_current_user)) -> UserInfoResponse:
    """
    Get the currently authenticated user's information.

    Requires a valid Bearer token in the Authorization header.
    """
    return UserInfoResponse(
        id=user.id,
        fullname=user.fullname,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """
    Change the current user's password.

    Requires the old password for verification and a new password
    that meets minimum length requirements.
    """
    auth = _get_auth_service()
    try:
        success = await auth.change_password(
            user_id=user.id,
            old_password=body.old_password,
            new_password=body.new_password,
        )
        if success:
            return {"status": "password_changed", "message": "Password updated successfully"}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        )
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        )


@router.get("/status")
async def auth_status() -> dict[str, Any]:
    """
    Get authentication system status.

    Returns the current auth configuration and health.
    No authentication required.
    """
    auth = _get_auth_service()
    return {
        "auth_provider": auth.auth_provider,
        "status": "operational",
        "jwt_algorithm": "HS256",
        "access_token_ttl_minutes": 30,
        "refresh_token_ttl_days": 7,
    }
