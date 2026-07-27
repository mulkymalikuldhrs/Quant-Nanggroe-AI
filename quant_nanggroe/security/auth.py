"""API Authentication — API key and JWT token-based auth with RBAC.

Provides two authentication mechanisms:

1. **APIKeyAuth** — Simple API key-based authentication
2. **JWTAuth** — JWT token-based authentication with role-based access control

Role-based access levels:
- ``admin``   — Full system access
- ``trader``  — Trading operations + read
- ``analyst`` — Read-only + analysis
- ``viewer``  — Read-only

Security
--------
- JWT tokens are signed with HMAC-SHA256
- Tokens include expiration and role claims
- API keys are validated against a configurable store
- Secret keys are never logged or exposed
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# File-backed token revocation store (survives restarts)
_REVOCATION_DIR = Path(__file__).resolve().parent.parent / "paper_state"
_REVOCATION_FILE = _REVOCATION_DIR / "revoked_tokens.json"

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    """User role with hierarchical access levels.

    Attributes
    ----------
    ADMIN:
        Full system access — can manage users, system config, and all operations.
    TRADER:
        Trading operations — can place/cancel orders and view positions.
    ANALYST:
        Analysis access — can run analysis and view data, but not trade.
    VIEWER:
        Read-only — can view data and reports only.
    """

    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"


# Role hierarchy: higher index = more permissions
_ROLE_HIERARCHY: Dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.ANALYST: 1,
    UserRole.TRADER: 2,
    UserRole.ADMIN: 3,
}

# Role → allowed actions
_ROLE_PERMISSIONS: Dict[UserRole, List[str]] = {
    UserRole.VIEWER: ["read"],
    UserRole.ANALYST: ["read", "analyze"],
    UserRole.TRADER: ["read", "analyze", "trade"],
    UserRole.ADMIN: ["read", "analyze", "trade", "admin"],
}


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class TokenPayload(BaseModel):
    """JWT token payload data.

    Attributes
    ----------
    user_id:
        Unique user identifier.
    role:
        User's role.
    issued_at:
        Token issue time (Unix timestamp).
    expires_at:
        Token expiration time (Unix timestamp).
    jti:
        JWT ID (unique token identifier for revocation).
    """

    user_id: str
    role: UserRole
    issued_at: float
    expires_at: float
    jti: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {"from_attributes": True}


class AuthResult(BaseModel):
    """Result of an authentication attempt.

    Attributes
    ----------
    success:
        Whether authentication succeeded.
    user_id:
        Authenticated user ID (if successful).
    role:
        Authenticated user's role (if successful).
    error:
        Error message (if failed).
    token:
        JWT token string (if successful, for JWT auth).
    """

    success: bool
    user_id: Optional[str] = None
    role: Optional[UserRole] = None
    error: Optional[str] = None
    token: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# API Key Auth
# ---------------------------------------------------------------------------

class APIKeyAuth:
    """API key-based authentication.

    Validates API keys against a configurable store, mapping each key
    to a user ID and role.

    Parameters
    ----------
    api_keys:
        Mapping of API key → ``{"user_id": str, "role": UserRole}``.

    Examples
    --------
    .. code-block:: python

        auth = APIKeyAuth(
            api_keys={
                "ak-test-admin-001": {"user_id": "admin1", "role": UserRole.ADMIN},
                "ak-test-trader-001": {"user_id": "trader1", "role": UserRole.TRADER},
            }
        )
        result = auth.authenticate("ak-test-admin-001")
        assert result.success
    """

    def __init__(
        self,
        api_keys: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self._api_keys: Dict[str, Dict[str, Any]] = api_keys or {}

    def add_key(self, api_key: str, user_id: str, role: UserRole) -> None:
        """Register an API key.

        Parameters
        ----------
        api_key:
            The API key string.
        user_id:
            User ID associated with this key.
        role:
            Role assigned to this key.
        """
        self._api_keys[api_key] = {"user_id": user_id, "role": role}

    def remove_key(self, api_key: str) -> None:
        """Remove an API key.

        Parameters
        ----------
        api_key:
            The API key to remove.
        """
        self._api_keys.pop(api_key, None)

    def authenticate(self, api_key: str) -> AuthResult:
        """Authenticate using an API key.

        Parameters
        ----------
        api_key:
            The API key to validate.

        Returns
        -------
        AuthResult
            Authentication result with user info.
        """
        if not api_key:
            return AuthResult(success=False, error="API key is empty")

        key_info = self._api_keys.get(api_key)
        if not key_info:
            return AuthResult(success=False, error="Invalid API key")

        return AuthResult(
            success=True,
            user_id=key_info["user_id"],
            role=key_info["role"],
        )

    def has_permission(self, api_key: str, action: str) -> bool:
        """Check if an API key has permission for an action.

        Parameters
        ----------
        api_key:
            The API key to check.
        action:
            The action to verify (``"read"``, ``"trade"``, ``"admin"``).

        Returns
        -------
        bool
        """
        result = self.authenticate(api_key)
        if not result.success or not result.role:
            return False
        permissions = _ROLE_PERMISSIONS.get(result.role, [])
        return action in permissions

    @property
    def key_count(self) -> int:
        """Number of registered API keys."""
        return len(self._api_keys)


# ---------------------------------------------------------------------------
# JWT Auth
# ---------------------------------------------------------------------------

class JWTAuth:
    """JWT token-based authentication with role-based access control.

    Uses HMAC-SHA256 for token signing. Tokens contain user ID, role,
    and expiration claims.

    Parameters
    ----------
    secret_key:
        HMAC secret key for signing tokens. **Must be kept secure.**
    default_ttl:
        Default token time-to-live in seconds (default: 3600 = 1 hour).
    algorithm:
        Signing algorithm (default: ``"HS256"``).

    Examples
    --------
    .. code-block:: python

        auth = JWTAuth(secret_key="my-secret-key")
        token = auth.create_token(user_id="trader1", role=UserRole.TRADER)
        payload = auth.validate_token(token)
        assert payload.user_id == "trader1"
    """

    def __init__(
        self,
        secret_key: str,
        default_ttl: int = 3600,
        algorithm: str = "HS256",
    ) -> None:
        self._secret_key = secret_key
        self._default_ttl = default_ttl
        self._algorithm = algorithm
        self._revoked_tokens: set[str] = set()
        self._load_revoked_tokens()

    def create_token(
        self,
        user_id: str,
        role: UserRole,
        ttl: Optional[int] = None,
    ) -> str:
        """Create a new JWT token (standard 3-part format).

        Parameters
        ----------
        user_id:
            User ID to encode in the token.
        role:
            User's role.
        ttl:
            Token time-to-live in seconds. Uses ``default_ttl`` if ``None``.

        Returns
        -------
        str
            Encoded JWT token string (header.payload.signature).
        """
        now = time.time()
        expires_at = now + (ttl or self._default_ttl)

        payload = TokenPayload(
            user_id=user_id,
            role=role,
            issued_at=now,
            expires_at=expires_at,
        )

        import base64

        # Standard JWT header
        header = json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        payload_json = payload.model_dump_json().encode()

        # Encode without padding (=)
        header_b64 = base64.urlsafe_b64encode(header).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(payload_json).rstrip(b"=").decode()

        # Sign header.payload
        signing_input = f"{header_b64}.{payload_b64}"
        signature = self._sign(signing_input)
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

        return f"{signing_input}.{signature_b64}"

    def _decode_b64(self, data: str) -> bytes:
        """Decode base64url with optional padding."""
        import base64
        data = data.rstrip("=")
        padded = data + "=" * (4 - len(data) % 4) if len(data) % 4 else data
        return base64.urlsafe_b64decode(padded)

    def validate_token(self, token: str) -> TokenPayload:
        """Validate a JWT token and return the payload.

        Accepts both standard 3-part (header.payload.signature)
        and legacy 2-part (payload.signature) tokens.

        Parameters
        ----------
        token:
            JWT token string.

        Returns
        -------
        TokenPayload
            Decoded and validated token payload.

        Raises
        ------
        ValueError
            If the token is invalid, expired, or revoked.
        """
        parts = token.split(".")
        if len(parts) not in (2, 3):
            raise ValueError("Invalid token format")

        try:
            if len(parts) == 3:
                header_b64, payload_b64, signature_b64 = parts
                signing_input = f"{header_b64}.{payload_b64}"
            else:
                payload_b64, signature_b64 = parts
                signing_input = self._decode_b64(payload_b64).decode()

            payload_json = self._decode_b64(payload_b64).decode()
            signature = self._decode_b64(signature_b64)
        except Exception as exc:
            raise ValueError(f"Invalid token encoding: {exc}") from exc

        # Verify signature
        expected_signature = self._sign(signing_input)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid token signature")

        # Decode payload
        try:
            payload = TokenPayload.model_validate_json(payload_json)
        except Exception as exc:
            raise ValueError(f"Invalid token payload: {exc}") from exc

        # Check expiration
        if time.time() > payload.expires_at:
            raise ValueError("Token has expired")

        # Check revocation
        if payload.jti in self._revoked_tokens:
            raise ValueError("Token has been revoked")

        return payload

    def refresh_token(self, token: str, ttl: Optional[int] = None) -> str:
        """Refresh an existing token, creating a new one with updated expiration.

        Parameters
        ----------
        token:
            Current valid JWT token.
        ttl:
            New token TTL in seconds. Uses ``default_ttl`` if ``None``.

        Returns
        -------
        str
            New JWT token string.

        Raises
        ------
        ValueError
            If the current token is invalid.
        """
        payload = self.validate_token(token)
        # Revoke the old token
        self._revoked_tokens.add(payload.jti)
        self._save_revoked_tokens()
        # Create a new token with the same user/role
        return self.create_token(
            user_id=payload.user_id,
            role=payload.role,
            ttl=ttl,
        )

    def revoke_token(self, token: str) -> None:
        """Revoke a token by its JWT ID.

        Parameters
        ----------
        token:
            JWT token to revoke.
        """
        try:
            payload = self.validate_token(token)
            self._revoked_tokens.add(payload.jti)
            self._save_revoked_tokens()
        except ValueError:
            # Token is already invalid, nothing to revoke
            pass

    def has_permission(self, token: str, action: str) -> bool:
        """Check if a token's role has permission for an action.

        Parameters
        ----------
        token:
            JWT token string.
        action:
            Action to check.

        Returns
        -------
        bool
        """
        try:
            payload = self.validate_token(token)
            permissions = _ROLE_PERMISSIONS.get(payload.role, [])
            return action in permissions
        except ValueError:
            return False

    @staticmethod
    def role_has_permission(role: UserRole, action: str) -> bool:
        """Check if a role has permission for an action (no token required).

        Parameters
        ----------
        role:
            User role.
        action:
            Action to check.

        Returns
        -------
        bool
        """
        permissions = _ROLE_PERMISSIONS.get(role, [])
        return action in permissions

    @staticmethod
    def is_role_at_least(role: UserRole, minimum: UserRole) -> bool:
        """Check if a role meets or exceeds a minimum level.

        Parameters
        ----------
        role:
            The role to check.
        minimum:
            The minimum required role.

        Returns
        -------
        bool
        """
        return _ROLE_HIERARCHY.get(role, 0) >= _ROLE_HIERARCHY.get(minimum, 0)

    # ----- Internal -----

    def _load_revoked_tokens(self) -> None:
        """Load revoked tokens from file-backed store."""
        try:
            if _REVOCATION_FILE.exists():
                data = json.loads(_REVOCATION_FILE.read_text(encoding="utf-8"))
                self._revoked_tokens = set(data.get("revoked", []))
        except Exception:
            logger.warning("Failed to load revoked tokens from %s", _REVOCATION_FILE)

    def _save_revoked_tokens(self) -> None:
        """Persist revoked tokens to file."""
        try:
            _REVOCATION_DIR.mkdir(parents=True, exist_ok=True)
            _REVOCATION_FILE.write_text(
                json.dumps({"revoked": list(self._revoked_tokens)}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.warning("Failed to persist revoked tokens to %s", _REVOCATION_FILE)

    def _sign(self, data: str) -> bytes:
        """Sign data using HMAC-SHA256.

        Parameters
        ----------
        data:
            String data to sign.

        Returns
        -------
        bytes
            HMAC signature.
        """
        return hmac.new(
            self._secret_key.encode(),
            data.encode(),
            hashlib.sha256,
        ).digest()

    def __repr__(self) -> str:
        return f"JWTAuth(algorithm={self._algorithm}, revoked={len(self._revoked_tokens)})"
