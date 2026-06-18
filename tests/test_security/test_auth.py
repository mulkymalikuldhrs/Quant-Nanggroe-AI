"""Tests for API Key and JWT Authentication.

All tests are deterministic — no network calls or external dependencies.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from quant_nanggroe.security.auth import (
    APIKeyAuth,
    JWTAuth,
    UserRole,
    TokenPayload,
    AuthResult,
    _ROLE_HIERARCHY,
    _ROLE_PERMISSIONS,
)


# ======================================================================
# UserRole
# ======================================================================

class TestUserRole:
    """Tests for the UserRole enum."""

    def test_role_values(self):
        assert UserRole.ADMIN == "admin"
        assert UserRole.TRADER == "trader"
        assert UserRole.ANALYST == "analyst"
        assert UserRole.VIEWER == "viewer"

    def test_role_hierarchy(self):
        """Higher roles should have higher hierarchy values."""
        assert _ROLE_HIERARCHY[UserRole.ADMIN] > _ROLE_HIERARCHY[UserRole.TRADER]
        assert _ROLE_HIERARCHY[UserRole.TRADER] > _ROLE_HIERARCHY[UserRole.ANALYST]
        assert _ROLE_HIERARCHY[UserRole.ANALYST] > _ROLE_HIERARCHY[UserRole.VIEWER]

    def test_role_permissions(self):
        """Each role should have appropriate permissions."""
        assert "read" in _ROLE_PERMISSIONS[UserRole.VIEWER]
        assert "analyze" not in _ROLE_PERMISSIONS[UserRole.VIEWER]
        assert "trade" in _ROLE_PERMISSIONS[UserRole.TRADER]
        assert "admin" in _ROLE_PERMISSIONS[UserRole.ADMIN]
        assert "trade" in _ROLE_PERMISSIONS[UserRole.ADMIN]


# ======================================================================
# TokenPayload
# ======================================================================

class TestTokenPayload:
    """Tests for the TokenPayload model."""

    def test_create_payload(self):
        payload = TokenPayload(
            user_id="user1",
            role=UserRole.TRADER,
            issued_at=time.time(),
            expires_at=time.time() + 3600,
        )
        assert payload.user_id == "user1"
        assert payload.role == UserRole.TRADER
        assert payload.jti is not None  # Auto-generated UUID

    def test_custom_jti(self):
        payload = TokenPayload(
            user_id="user1",
            role=UserRole.ADMIN,
            issued_at=0,
            expires_at=0,
            jti="custom-jti",
        )
        assert payload.jti == "custom-jti"


# ======================================================================
# AuthResult
# ======================================================================

class TestAuthResult:
    """Tests for the AuthResult model."""

    def test_success_result(self):
        result = AuthResult(
            success=True,
            user_id="trader1",
            role=UserRole.TRADER,
        )
        assert result.success is True
        assert result.user_id == "trader1"
        assert result.role == UserRole.TRADER
        assert result.error is None

    def test_failure_result(self):
        result = AuthResult(
            success=False,
            error="Invalid API key",
        )
        assert result.success is False
        assert result.error == "Invalid API key"


# ======================================================================
# APIKeyAuth
# ======================================================================

class TestAPIKeyAuth:
    """Tests for the APIKeyAuth class."""

    def test_authenticate_valid_key(self):
        auth = APIKeyAuth(
            api_keys={
                "ak-admin-001": {"user_id": "admin1", "role": UserRole.ADMIN},
                "ak-trader-001": {"user_id": "trader1", "role": UserRole.TRADER},
            }
        )
        result = auth.authenticate("ak-admin-001")
        assert result.success is True
        assert result.user_id == "admin1"
        assert result.role == UserRole.ADMIN

    def test_authenticate_invalid_key(self):
        auth = APIKeyAuth(
            api_keys={
                "ak-valid-001": {"user_id": "user1", "role": UserRole.VIEWER},
            }
        )
        result = auth.authenticate("ak-invalid-key")
        assert result.success is False
        assert "Invalid" in result.error

    def test_authenticate_empty_key(self):
        auth = APIKeyAuth()
        result = auth.authenticate("")
        assert result.success is False

    def test_add_key(self):
        auth = APIKeyAuth()
        auth.add_key("ak-new-001", "new_user", UserRole.ANALYST)
        result = auth.authenticate("ak-new-001")
        assert result.success is True
        assert result.role == UserRole.ANALYST

    def test_remove_key(self):
        auth = APIKeyAuth(
            api_keys={
                "ak-remove-001": {"user_id": "user1", "role": UserRole.VIEWER},
            }
        )
        auth.remove_key("ak-remove-001")
        result = auth.authenticate("ak-remove-001")
        assert result.success is False

    def test_has_permission_true(self):
        auth = APIKeyAuth(
            api_keys={
                "ak-trader-001": {"user_id": "trader1", "role": UserRole.TRADER},
            }
        )
        assert auth.has_permission("ak-trader-001", "trade") is True
        assert auth.has_permission("ak-trader-001", "read") is True

    def test_has_permission_false(self):
        auth = APIKeyAuth(
            api_keys={
                "ak-trader-001": {"user_id": "trader1", "role": UserRole.TRADER},
            }
        )
        assert auth.has_permission("ak-trader-001", "admin") is False

    def test_has_permission_invalid_key(self):
        auth = APIKeyAuth()
        assert auth.has_permission("invalid-key", "read") is False

    def test_key_count(self):
        auth = APIKeyAuth(
            api_keys={
                "key1": {"user_id": "u1", "role": UserRole.VIEWER},
                "key2": {"user_id": "u2", "role": UserRole.TRADER},
            }
        )
        assert auth.key_count == 2


# ======================================================================
# JWTAuth — Token Creation
# ======================================================================

class TestJWTAuthCreation:
    """Tests for JWT token creation."""

    def test_create_token(self):
        auth = JWTAuth(secret_key="test-secret-key")
        token = auth.create_token(user_id="trader1", role=UserRole.TRADER)
        assert isinstance(token, str)
        assert "." in token  # Format: payload.signature

    def test_create_token_custom_ttl(self):
        auth = JWTAuth(secret_key="test-secret-key", default_ttl=3600)
        token = auth.create_token(user_id="user1", role=UserRole.ADMIN, ttl=7200)
        payload = auth.validate_token(token)
        # Expires at should be roughly now + 7200
        assert payload.expires_at - payload.issued_at >= 7000


# ======================================================================
# JWTAuth — Token Validation
# ======================================================================

class TestJWTAuthValidation:
    """Tests for JWT token validation."""

    def test_validate_valid_token(self):
        auth = JWTAuth(secret_key="test-secret-key")
        token = auth.create_token(user_id="trader1", role=UserRole.TRADER)
        payload = auth.validate_token(token)
        assert payload.user_id == "trader1"
        assert payload.role == UserRole.TRADER

    def test_validate_invalid_format(self):
        auth = JWTAuth(secret_key="test-secret-key")
        with pytest.raises(ValueError, match="Invalid token format"):
            auth.validate_token("not-a-valid-token")

    def test_validate_tampered_token(self):
        auth = JWTAuth(secret_key="test-secret-key")
        token = auth.create_token(user_id="user1", role=UserRole.ADMIN)
        # Tamper with the token
        parts = token.split(".")
        tampered = parts[0] + ".AAAA"
        with pytest.raises(ValueError, match="Invalid token"):
            auth.validate_token(tampered)

    def test_validate_wrong_secret(self):
        auth1 = JWTAuth(secret_key="secret-1")
        auth2 = JWTAuth(secret_key="secret-2")
        token = auth1.create_token(user_id="user1", role=UserRole.TRADER)
        with pytest.raises(ValueError, match="Invalid token signature"):
            auth2.validate_token(token)

    def test_validate_expired_token(self):
        auth = JWTAuth(secret_key="test-secret-key", default_ttl=-1)  # Already expired
        token = auth.create_token(user_id="user1", role=UserRole.VIEWER)
        with pytest.raises(ValueError, match="expired"):
            auth.validate_token(token)


# ======================================================================
# JWTAuth — Token Refresh
# ======================================================================

class TestJWTAuthRefresh:
    """Tests for JWT token refresh."""

    def test_refresh_token(self):
        auth = JWTAuth(secret_key="test-secret-key")
        token = auth.create_token(user_id="user1", role=UserRole.TRADER)
        new_token = auth.refresh_token(token)
        assert new_token != token

        # New token should be valid
        payload = auth.validate_token(new_token)
        assert payload.user_id == "user1"
        assert payload.role == UserRole.TRADER

    def test_refresh_revokes_old_token(self):
        auth = JWTAuth(secret_key="test-secret-key")
        token = auth.create_token(user_id="user1", role=UserRole.ADMIN)
        auth.refresh_token(token)
        # Old token should be revoked
        with pytest.raises(ValueError, match="revoked"):
            auth.validate_token(token)


# ======================================================================
# JWTAuth — Token Revocation
# ======================================================================

class TestJWTAuthRevocation:
    """Tests for JWT token revocation."""

    def test_revoke_token(self):
        auth = JWTAuth(secret_key="test-secret-key")
        token = auth.create_token(user_id="user1", role=UserRole.TRADER)
        auth.revoke_token(token)
        with pytest.raises(ValueError, match="revoked"):
            auth.validate_token(token)

    def test_revoke_invalid_token_doesnt_raise(self):
        auth = JWTAuth(secret_key="test-secret-key")
        auth.revoke_token("invalid-token")  # Should not raise

    def test_revoked_count(self):
        auth = JWTAuth(secret_key="test-secret-key")
        token = auth.create_token(user_id="user1", role=UserRole.TRADER)
        auth.revoke_token(token)
        assert len(auth._revoked_tokens) == 1


# ======================================================================
# JWTAuth — Permissions
# ======================================================================

class TestJWTAuthPermissions:
    """Tests for role-based permission checking."""

    def test_has_permission_with_valid_token(self):
        auth = JWTAuth(secret_key="test-secret-key")
        token = auth.create_token(user_id="trader1", role=UserRole.TRADER)
        assert auth.has_permission(token, "trade") is True
        assert auth.has_permission(token, "admin") is False

    def test_has_permission_with_invalid_token(self):
        auth = JWTAuth(secret_key="test-secret-key")
        assert auth.has_permission("invalid", "read") is False

    def test_role_has_permission(self):
        assert JWTAuth.role_has_permission(UserRole.ADMIN, "admin") is True
        assert JWTAuth.role_has_permission(UserRole.VIEWER, "admin") is False
        assert JWTAuth.role_has_permission(UserRole.ANALYST, "analyze") is True

    def test_is_role_at_least(self):
        assert JWTAuth.is_role_at_least(UserRole.ADMIN, UserRole.TRADER) is True
        assert JWTAuth.is_role_at_least(UserRole.VIEWER, UserRole.TRADER) is False
        assert JWTAuth.is_role_at_least(UserRole.TRADER, UserRole.TRADER) is True


# ======================================================================
# JWTAuth — Repr
# ======================================================================

class TestJWTAuthRepr:
    """Tests for JWTAuth repr."""

    def test_repr(self):
        auth = JWTAuth(secret_key="test")
        result = repr(auth)
        assert "JWTAuth" in result
        assert "HS256" in result
