"""
API Authentication — JWT + Basic Auth + Auth Middleware
========================================================
Merged from ai-manus feat/auth branch and adapted for Quant-Nanggroe-AI.

Provides:
  - JWTManager: Create, verify, and refresh JWT tokens
  - AuthService: User registration, authentication, token management
  - AuthMiddleware: FastAPI middleware for request authentication
  - get_current_user: Dependency for extracting authenticated user

Adapted from:
  - ai-manus/backend/app/application/services/jwt.py
  - ai-manus/backend/app/application/services/auth_service.py
  - ai-manus/backend/app/infrastructure/middleware/auth.py
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import lru_cache
from typing import Any, Optional

import jwt
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from quant_nanggroe_ai.config import get_settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Domain Models
# ══════════════════════════════════════════════════════════════════════


class UserRole(str, Enum):
    """User role enum for access control."""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class User(BaseModel):
    """User model for authentication context."""
    id: str
    fullname: str = ""
    email: str = ""
    role: UserRole = UserRole.VIEWER
    is_active: bool = True
    password_hash: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.updated_at = datetime.now(UTC)

    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.now(UTC)

    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True
        self.updated_at = datetime.now(UTC)


# ══════════════════════════════════════════════════════════════════════
# JWT Manager
# ══════════════════════════════════════════════════════════════════════


class JWTManager:
    """
    JWT token manager for authentication.

    Handles creation, verification, and introspection of JWT access
    and refresh tokens using the application's secret key.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # -- Configuration helpers ------------------------------------------------

    @property
    def _jwt_secret(self) -> str:
        """JWT secret key from application settings."""
        return self._settings.secret_key

    @property
    def _jwt_algorithm(self) -> str:
        """JWT signing algorithm."""
        return "HS256"

    @property
    def _access_token_expire_minutes(self) -> int:
        """Access token expiration in minutes."""
        return 30

    @property
    def _refresh_token_expire_days(self) -> int:
        """Refresh token expiration in days."""
        return 7

    # -- Token creation -------------------------------------------------------

    def create_access_token(self, user: User) -> str:
        """
        Create JWT access token for user.

        Args:
            user: The User object to encode in the token.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self._access_token_expire_minutes)

        payload = {
            "sub": user.id,
            "fullname": user.fullname,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "access",
        }

        try:
            token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
            logger.debug("Created access token for user: %s", user.fullname)
            return token
        except Exception as e:
            logger.error("Failed to create access token: %s", e)
            raise

    def create_refresh_token(self, user: User) -> str:
        """
        Create JWT refresh token for user.

        Args:
            user: The User object to encode in the token.

        Returns:
            Encoded JWT refresh token string.
        """
        now = datetime.now(UTC)
        expire = now + timedelta(days=self._refresh_token_expire_days)

        payload = {
            "sub": user.id,
            "fullname": user.fullname,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "refresh",
        }

        try:
            token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
            logger.debug("Created refresh token for user: %s", user.fullname)
            return token
        except Exception as e:
            logger.error("Failed to create refresh token: %s", e)
            raise

    # -- Token verification ---------------------------------------------------

    def verify_token(self, token: str) -> Optional[dict[str, Any]]:
        """
        Verify JWT token and return payload.

        Args:
            token: The encoded JWT string.

        Returns:
            Decoded payload dict, or None if the token is invalid/expired.
        """
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
            )
            exp = payload.get("exp")
            if exp and exp < int(datetime.now(UTC).timestamp()):
                logger.warning("Token has expired")
                return None
            logger.debug("Token verified for user: %s", payload.get("fullname"))
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token: %s", e)
            return None
        except Exception as e:
            logger.error("Token verification failed: %s", e)
            return None

    def get_user_from_token(self, token: str) -> Optional[dict[str, Any]]:
        """
        Extract user information from JWT token.

        Args:
            token: The encoded JWT string.

        Returns:
            Dict with user info (id, fullname, email, role, is_active, token_type),
            or None if the token is invalid.
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        return {
            "id": payload.get("sub"),
            "fullname": payload.get("fullname"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "is_active": payload.get("is_active", True),
            "token_type": payload.get("type", "access"),
        }

    def is_token_valid(self, token: str) -> bool:
        """Check if token is valid."""
        return self.verify_token(token) is not None

    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """Get token expiration time."""
        payload = self.verify_token(token)
        if not payload:
            return None
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, UTC)
        return None

    def revoke_token(self, token: str) -> bool:
        """
        Revoke token (placeholder for token blacklist implementation).

        In production, implement a Redis-based token blacklist.
        """
        logger.info("Token revocation requested (placeholder)")
        return True


@lru_cache()
def get_jwt_manager() -> JWTManager:
    """Get cached JWT manager instance."""
    return JWTManager()


# ══════════════════════════════════════════════════════════════════════
# Auth Service
# ══════════════════════════════════════════════════════════════════════


class AuthError(Exception):
    """Base exception for auth errors."""

    def __init__(self, message: str, code: str = "AUTH_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class UnauthorizedError(AuthError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, code="UNAUTHORIZED")


class ValidationError(AuthError):
    """Raised when input validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


# Simple in-memory user store (replace with database in production)
_user_store: dict[str, User] = {}


class AuthService:
    """
    Authentication service handling user authentication and authorization.

    Supports three auth providers:
      - "none": No authentication — returns anonymous user
      - "local": Single local admin configured via env vars
      - "password": Database-backed user/password authentication

    For the Quant-Nanggroe-AI trading platform, this service is primarily
    used for API key management and admin access control.
    """

    def __init__(self, auth_provider: str = "local") -> None:
        self.auth_provider = auth_provider
        self.jwt_manager = get_jwt_manager()

    # -- Password hashing -----------------------------------------------------

    @staticmethod
    def _hash_password(password: str, salt: str | None = None) -> str:
        """
        Hash password using PBKDF2 with SHA-256.

        Args:
            password: Plain-text password.
            salt: Optional salt (auto-generated if not provided).

        Returns:
            Salt + hash hex string.
        """
        if salt is None:
            salt = secrets.token_hex(32)
        password_bytes = password.encode("utf-8")
        salt_bytes = salt.encode("utf-8")
        rounds = 100_000  # OWASP recommended minimum
        hash_bytes = hashlib.pbkdf2_hmac("sha256", password_bytes, salt_bytes, rounds)
        return salt + hash_bytes.hex()

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        """
        Verify password against stored hash.

        Args:
            password: Plain-text password to verify.
            password_hash: Stored salt+hash string.

        Returns:
            True if the password matches.
        """
        if not password_hash:
            return False
        try:
            salt = password_hash[:64]
            expected_hash = password_hash[64:]
            rounds = 100_000
            generated_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                rounds,
            ).hex()
            return generated_hash == expected_hash
        except Exception as e:
            logger.error("Password verification error: %s", e)
            return False

    @staticmethod
    def _generate_user_id() -> str:
        """Generate unique user ID."""
        return secrets.token_urlsafe(16)

    # -- User management ------------------------------------------------------

    async def register_user(
        self,
        fullname: str,
        password: str,
        email: str,
        role: UserRole = UserRole.VIEWER,
    ) -> User:
        """
        Register a new user.

        Args:
            fullname: User's full name (min 2 chars).
            password: User's password (min 6 chars).
            email: User's email address.
            role: User role (default VIEWER).

        Returns:
            Created User object.

        Raises:
            ValidationError: If input validation fails.
        """
        logger.info("Registering user: %s", email)

        if not fullname or len(fullname.strip()) < 2:
            raise ValidationError("Full name must be at least 2 characters long")
        if not email or "@" not in email:
            raise ValidationError("Valid email is required")
        if not password or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")

        # Check if email already exists
        for existing_user in _user_store.values():
            if existing_user.email == email.lower():
                raise ValidationError("Email already exists")

        password_hash = self._hash_password(password)
        user = User(
            id=self._generate_user_id(),
            fullname=fullname.strip(),
            email=email.lower(),
            password_hash=password_hash,
            role=role,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        _user_store[user.id] = user
        logger.info("User registered successfully: %s", user.id)
        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user by email and password.

        Args:
            email: User's email.
            password: User's password.

        Returns:
            Authenticated User, or None if authentication fails.
        """
        logger.debug("Authenticating user: %s", email)

        if self.auth_provider == "none":
            return User(
                id="anonymous",
                fullname="anonymous",
                email="anonymous@localhost",
                role=UserRole.VIEWER,
                is_active=True,
            )

        elif self.auth_provider == "local":
            # Local authentication — single admin user from settings
            settings = get_settings()
            local_email = getattr(settings, "local_auth_email", "admin@localhost")
            local_password = getattr(settings, "local_auth_password", "admin")
            if email == local_email and password == local_password:
                return User(
                    id="local_admin",
                    fullname="Local Admin",
                    email=email,
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            logger.warning("Local authentication failed for user: %s", email)
            return None

        else:
            # Password-based authentication from user store
            for user in _user_store.values():
                if user.email == email.lower():
                    if not user.is_active:
                        logger.warning("User account is inactive: %s", email)
                        return None
                    if self._verify_password(password, user.password_hash):
                        user.update_last_login()
                        logger.info("User authenticated successfully: %s", email)
                        return user
            logger.warning("User not found or invalid password: %s", email)
            return None

    async def login_with_tokens(self, email: str, password: str) -> dict[str, Any]:
        """
        Authenticate user and return JWT tokens.

        Args:
            email: User's email.
            password: User's password.

        Returns:
            Dict with user, access_token, refresh_token, and token_type.

        Raises:
            UnauthorizedError: If authentication fails.
        """
        user = await self.authenticate_user(email, password)
        if not user:
            raise UnauthorizedError("Invalid email or password")

        access_token = self.jwt_manager.create_access_token(user)
        refresh_token = self.jwt_manager.create_refresh_token(user)

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: The refresh JWT token.

        Returns:
            Dict with new access_token and token_type.

        Raises:
            UnauthorizedError: If the refresh token is invalid.
        """
        payload = self.jwt_manager.verify_token(refresh_token)
        if not payload:
            raise UnauthorizedError("Invalid refresh token")
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        user_id = payload.get("sub")
        user = _user_store.get(str(user_id)) if user_id else None

        if not user:
            # For local/none auth, create user from token info
            user = User(
                id=str(user_id),
                fullname=payload.get("fullname", ""),
                role=UserRole(payload.get("role", "viewer")),
                is_active=payload.get("is_active", True),
            )

        if not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        new_access_token = self.jwt_manager.create_access_token(user)
        return {"access_token": new_access_token, "token_type": "bearer"}

    async def verify_token(self, token: str) -> Optional[User]:
        """
        Verify JWT token and return user.

        Args:
            token: The encoded JWT string.

        Returns:
            User object, or None if the token is invalid.
        """
        user_info = self.jwt_manager.get_user_from_token(token)
        if not user_info:
            return None

        # For database users, verify user still exists and is active
        if self.auth_provider == "password":
            user = _user_store.get(user_info["id"])
            if not user or not user.is_active:
                return None
            return user

        # For local/none authentication, create user from token info
        return User(
            id=user_info["id"],
            fullname=user_info["fullname"],
            email=user_info.get("email", ""),
            role=UserRole(user_info.get("role", "viewer")),
            is_active=user_info.get("is_active", True),
        )

    async def logout(self, token: str) -> bool:
        """Logout user by revoking token."""
        return self.jwt_manager.revoke_token(token)

    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: The user's ID.
            old_password: Current password for verification.
            new_password: New password (min 6 chars).

        Returns:
            True if password was changed successfully.

        Raises:
            ValidationError: If user not found or validation fails.
            UnauthorizedError: If old password is incorrect.
        """
        logger.info("Changing password for user: %s", user_id)
        user = _user_store.get(user_id)
        if not user:
            raise ValidationError("User not found")
        if not user.is_active:
            raise UnauthorizedError("User account is inactive")
        if not user.password_hash or not self._verify_password(
            old_password, user.password_hash
        ):
            raise UnauthorizedError("Invalid old password")
        if not new_password or len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters long")

        user.password_hash = self._hash_password(new_password)
        user.updated_at = datetime.now(UTC)
        logger.info("Password changed successfully for user: %s", user_id)
        return True


# ══════════════════════════════════════════════════════════════════════
# Auth Middleware
# ══════════════════════════════════════════════════════════════════════


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for API requests.

    Supports Basic Auth and Bearer token authentication.
    Configurable excluded paths that bypass authentication.

    Usage::

        app.add_middleware(
            AuthMiddleware,
            excluded_paths=["/api/v1/auth/login", "/docs"],
        )
    """

    def __init__(
        self,
        app: Any,
        excluded_paths: list[str] | None = None,
        auth_provider: str = "local",
    ) -> None:
        super().__init__(app)
        self.auth_service = AuthService(auth_provider=auth_provider)

        # Default paths that don't require authentication
        self.excluded_paths = excluded_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/status",
            "/api/v1/auth/refresh",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process authentication for each request."""

        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)

        # Skip for non-API paths
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        # Extract authentication information
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._unauthorized_response("Missing Authorization header")

        try:
            if auth_header.startswith("Basic "):
                user = await self._handle_basic_auth(auth_header)
            elif auth_header.startswith("Bearer "):
                user = await self._handle_bearer_auth(auth_header)
            else:
                return self._unauthorized_response("Invalid authentication scheme")

            if not user:
                return self._unauthorized_response("Authentication failed")

            if not user.is_active:
                return self._unauthorized_response("User account is inactive")

            # Add user to request state
            request.state.user = user
            return await call_next(request)

        except Exception as e:
            logger.error("Authentication error: %s", e)
            return self._unauthorized_response("Authentication failed")

    async def _handle_basic_auth(self, auth_header: str) -> Optional[User]:
        """Handle HTTP Basic Authentication."""
        try:
            encoded_credentials = auth_header.split(" ")[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
            return await self.auth_service.authenticate_user(username, password)
        except Exception as e:
            logger.warning("Basic auth failed: %s", e)
            return None

    async def _handle_bearer_auth(self, auth_header: str) -> Optional[User]:
        """Handle Bearer Token Authentication."""
        try:
            token = auth_header.split(" ")[1]
            return await self.auth_service.verify_token(token)
        except Exception as e:
            logger.warning("Bearer token auth failed: %s", e)
            return None

    @staticmethod
    def _unauthorized_response(message: str) -> JSONResponse:
        """Return 401 Unauthorized response."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"code": 401, "msg": message, "data": None},
        )


def get_current_user(request: Request) -> User:
    """
    FastAPI dependency to get current authenticated user from request state.

    Args:
        request: The incoming HTTP request.

    Returns:
        The authenticated User object.

    Raises:
        HTTPException: 401 if no authenticated user found.
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return request.state.user
