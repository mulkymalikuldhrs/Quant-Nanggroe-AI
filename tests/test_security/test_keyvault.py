"""Tests for KeyVault — Secure secrets management.

Tests verify that secrets are loaded from environment variables only,
with fail-fast behavior for missing required secrets.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from quant_nanggroe.security.keyvault import KeyVault, SecretNotFoundError


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def vault():
    """Create a fresh KeyVault instance."""
    return KeyVault()


@pytest.fixture
def clean_env():
    """Ensure no test env vars leak between tests."""
    test_vars = ["TEST_SECRET_KEY", "TEST_OPTIONAL_KEY", "TEST_EMPTY_KEY"]
    original = {k: os.environ.get(k) for k in test_vars}
    # Clean up
    for k in test_vars:
        os.environ.pop(k, None)
    yield
    # Restore
    for k, v in original.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


# ======================================================================
# get_secret — Required secrets
# ======================================================================

class TestGetSecret:
    """Tests for the get_secret method."""

    def test_get_existing_secret(self, vault, clean_env):
        """Should return the value of an existing env var."""
        os.environ["TEST_SECRET_KEY"] = "my-api-key-12345"
        result = vault.get_secret("TEST_SECRET_KEY")
        assert result == "my-api-key-12345"

    def test_get_missing_required_secret_raises(self, vault, clean_env):
        """Should raise SecretNotFoundError for missing required secrets."""
        os.environ.pop("TEST_SECRET_KEY", None)
        with pytest.raises(SecretNotFoundError) as exc_info:
            vault.get_secret("TEST_SECRET_KEY")
        assert "TEST_SECRET_KEY" in str(exc_info.value)

    def test_get_missing_optional_secret_returns_empty(self, vault, clean_env):
        """Should return empty string for missing optional secrets."""
        os.environ.pop("TEST_SECRET_KEY", None)
        result = vault.get_secret("TEST_SECRET_KEY", required=False)
        assert result == ""

    def test_get_empty_secret_raises_if_required(self, vault, clean_env):
        """Should raise for empty string if required."""
        os.environ["TEST_SECRET_KEY"] = ""
        with pytest.raises(SecretNotFoundError):
            vault.get_secret("TEST_SECRET_KEY")

    def test_get_empty_secret_returns_empty_if_optional(self, vault, clean_env):
        """Should return empty string for empty env var if not required."""
        os.environ["TEST_SECRET_KEY"] = ""
        result = vault.get_secret("TEST_SECRET_KEY", required=False)
        assert result == ""


# ======================================================================
# get_optional_secret
# ======================================================================

class TestGetOptionalSecret:
    """Tests for the get_optional_secret method."""

    def test_get_existing_optional_secret(self, vault, clean_env):
        """Should return the value of an existing env var."""
        os.environ["TEST_OPTIONAL_KEY"] = "redis://localhost:6379"
        result = vault.get_optional_secret("TEST_OPTIONAL_KEY")
        assert result == "redis://localhost:6379"

    def test_get_missing_optional_secret_returns_default(self, vault, clean_env):
        """Should return the default value for missing env vars."""
        os.environ.pop("TEST_OPTIONAL_KEY", None)
        result = vault.get_optional_secret("TEST_OPTIONAL_KEY", default="default-val")
        assert result == "default-val"

    def test_get_missing_optional_secret_returns_none(self, vault, clean_env):
        """Should return None by default for missing env vars."""
        os.environ.pop("TEST_OPTIONAL_KEY", None)
        result = vault.get_optional_secret("TEST_OPTIONAL_KEY")
        assert result is None

    def test_get_empty_optional_secret_returns_none(self, vault, clean_env):
        """Should return None for empty env var."""
        os.environ["TEST_OPTIONAL_KEY"] = ""
        result = vault.get_optional_secret("TEST_OPTIONAL_KEY")
        assert result is None


# ======================================================================
# has_secret
# ======================================================================

class TestHasSecret:
    """Tests for the has_secret method."""

    def test_has_existing_secret(self, vault, clean_env):
        """Should return True for existing, non-empty env vars."""
        os.environ["TEST_SECRET_KEY"] = "value"
        assert vault.has_secret("TEST_SECRET_KEY") is True

    def test_has_missing_secret(self, vault, clean_env):
        """Should return False for missing env vars."""
        os.environ.pop("TEST_SECRET_KEY", None)
        assert vault.has_secret("TEST_SECRET_KEY") is False

    def test_has_empty_secret(self, vault, clean_env):
        """Should return False for empty env vars."""
        os.environ["TEST_SECRET_KEY"] = ""
        assert vault.has_secret("TEST_SECRET_KEY") is False


# ======================================================================
# require_secrets
# ======================================================================

class TestRequireSecrets:
    """Tests for the require_secrets method."""

    def test_require_all_present(self, vault, clean_env):
        """Should succeed when all required secrets are present."""
        os.environ["TEST_SECRET_KEY"] = "value1"
        os.environ["TEST_OPTIONAL_KEY"] = "value2"
        vault.require_secrets(["TEST_SECRET_KEY", "TEST_OPTIONAL_KEY"])

    def test_require_missing_raises(self, vault, clean_env):
        """Should raise when any required secret is missing."""
        os.environ.pop("TEST_SECRET_KEY", None)
        with pytest.raises(SecretNotFoundError):
            vault.require_secrets(["TEST_SECRET_KEY"])


# ======================================================================
# Caching
# ======================================================================

class TestKeyVaultCaching:
    """Tests for the caching mechanism."""

    def test_cache_on_first_access(self, vault, clean_env):
        """Should cache values on first access."""
        os.environ["TEST_SECRET_KEY"] = "cached-value"
        vault.get_secret("TEST_SECRET_KEY")
        assert "TEST_SECRET_KEY" in vault._cache
        assert vault._cache["TEST_SECRET_KEY"] == "cached-value"

    def test_cache_hit(self, vault, clean_env):
        """Should return cached value on subsequent access."""
        os.environ["TEST_SECRET_KEY"] = "original-value"
        vault.get_secret("TEST_SECRET_KEY")

        # Change the env var — cache should still hold old value
        os.environ["TEST_SECRET_KEY"] = "new-value"
        result = vault.get_secret("TEST_SECRET_KEY")
        assert result == "original-value"

    def test_clear_cache(self, vault, clean_env):
        """Should clear the cache."""
        os.environ["TEST_SECRET_KEY"] = "value"
        vault.get_secret("TEST_SECRET_KEY")
        vault.clear_cache()
        assert len(vault._cache) == 0

        # Should re-read from env after cache clear
        os.environ["TEST_SECRET_KEY"] = "updated-value"
        result = vault.get_secret("TEST_SECRET_KEY")
        assert result == "updated-value"


# ======================================================================
# Masking
# ======================================================================

class TestKeyVaultMasking:
    """Tests for the mask_value method."""

    def test_mask_long_value(self):
        """Should show first 4 chars and mask the rest."""
        result = KeyVault.mask_value("abcdefghijklmnopqrstuvwxyz")
        assert result == "abcd****"
        assert "efgh" not in result

    def test_mask_short_value(self):
        """Should fully mask short values."""
        result = KeyVault.mask_value("ab")
        assert result == "****"

    def test_mask_empty_value(self):
        """Should mask empty values."""
        result = KeyVault.mask_value("")
        assert result == "****"

    def test_mask_custom_show_length(self):
        """Should respect custom show_length."""
        result = KeyVault.mask_value("abcdefghij", show_length=6)
        assert result == "abcdef****"

    def test_mask_exact_show_length(self):
        """Value same length as show_length should be fully masked."""
        result = KeyVault.mask_value("abcd", show_length=4)
        assert result == "****"


# ======================================================================
# SecretNotFoundError
# ======================================================================

class TestSecretNotFoundError:
    """Tests for the SecretNotFoundError exception."""

    def test_error_message_contains_key_name(self):
        err = SecretNotFoundError("MY_API_KEY")
        assert "MY_API_KEY" in str(err)
        assert err.key_name == "MY_API_KEY"

    def test_is_environment_error(self):
        err = SecretNotFoundError("KEY")
        assert isinstance(err, EnvironmentError)


# ======================================================================
# Repr
# ======================================================================

class TestKeyVaultRepr:
    """Tests for the KeyVault repr."""

    def test_repr_empty(self, vault):
        result = repr(vault)
        assert "KeyVault" in result
        assert "cached_secrets=0" in result

    def test_repr_with_cache(self, vault, clean_env):
        os.environ["TEST_SECRET_KEY"] = "value"
        vault.get_secret("TEST_SECRET_KEY")
        result = repr(vault)
        assert "cached_secrets=1" in result
