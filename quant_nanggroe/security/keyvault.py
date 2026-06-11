"""Secure Secrets Management — Environment-variable-only key vault.

Provides a secure interface for loading secrets from environment
variables only. **No hardcoded keys, no config files, no logging.**

Features
--------
* Load secrets from environment variables ONLY
* ``get_secret(key_name, required=True)`` → str (fail-fast if missing)
* ``get_optional_secret(key_name, default=None)`` → Optional[str]
* Validation: fail fast if required secret missing
* Never log or expose secret values

Security
--------
This module is designed to be the single entry point for all secrets
in the system. It intentionally:

1. Only reads from ``os.environ`` — no files, no .env parsing.
2. Never logs secret values, even at DEBUG level.
3. Raises immediately on missing required secrets (fail-fast).
4. Masks secret values in any error messages.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum length to show in masked errors
_MASK_SHOW_LENGTH = 4


class SecretNotFoundError(EnvironmentError):
    """Raised when a required secret is not found in environment variables."""

    def __init__(self, key_name: str) -> None:
        self.key_name = key_name
        super().__init__(
            f"Required secret '{key_name}' not found in environment variables. "
            f"Set the {key_name} environment variable before starting the application."
        )


class KeyVault:
    """Secure secrets manager — environment variables only.

    All secrets are loaded from ``os.environ``. There is no fallback
    to config files, .env files, or hardcoded defaults.

    Examples
    --------
    .. code-block:: python

        vault = KeyVault()

        # Required secret — raises if missing
        api_key = vault.get_secret("ALPACA_API_KEY")

        # Optional secret — returns None or default
        redis_url = vault.get_optional_secret("REDIS_URL", default="redis://localhost:6379")

        # Check if a secret exists
        if vault.has_secret("BINANCE_API_KEY"):
            key = vault.get_secret("BINANCE_API_KEY")
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def get_secret(self, key_name: str, required: bool = True) -> str:
        """Get a secret from environment variables.

        Parameters
        ----------
        key_name:
            Environment variable name.
        required:
            If ``True`` (default), raises :class:`SecretNotFoundError`
            when the variable is not set or is empty.

        Returns
        -------
        str
            The secret value.

        Raises
        ------
        SecretNotFoundError
            If ``required=True`` and the variable is not set or empty.
        """
        # Check cache first
        if key_name in self._cache:
            return self._cache[key_name]

        value = os.environ.get(key_name, "")

        if not value:
            if required:
                raise SecretNotFoundError(key_name)
            return ""

        self._cache[key_name] = value
        return value

    def get_optional_secret(
        self,
        key_name: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Get an optional secret from environment variables.

        Parameters
        ----------
        key_name:
            Environment variable name.
        default:
            Default value if the variable is not set.

        Returns
        -------
        str or None
            The secret value, or ``default`` if not set.
        """
        value = os.environ.get(key_name, "")
        if not value:
            return default
        self._cache[key_name] = value
        return value

    def has_secret(self, key_name: str) -> bool:
        """Check if a secret exists in environment variables.

        Parameters
        ----------
        key_name:
            Environment variable name.

        Returns
        -------
        bool
            ``True`` if the variable is set and non-empty.
        """
        value = os.environ.get(key_name, "")
        return bool(value)

    def require_secrets(self, key_names: list[str]) -> None:
        """Validate that multiple required secrets are available.

        Parameters
        ----------
        key_names:
            List of environment variable names to check.

        Raises
        ------
        SecretNotFoundError
            If any required secret is missing. Only reports the
            first missing key.
        """
        for key_name in key_names:
            self.get_secret(key_name, required=True)

    def clear_cache(self) -> None:
        """Clear the internal secret cache.

        Forces re-reading from environment variables on next access.
        """
        self._cache.clear()

    @staticmethod
    def mask_value(value: str, show_length: int = _MASK_SHOW_LENGTH) -> str:
        """Mask a secret value for safe display.

        Parameters
        ----------
        value:
            The secret value to mask.
        show_length:
            Number of characters to show at the start.

        Returns
        -------
        str
            Masked value like ``"abcd****"``.
        """
        if not value:
            return "****"
        if len(value) <= show_length:
            return "****"
        return value[:show_length] + "****"

    def __repr__(self) -> str:
        cached_count = len(self._cache)
        return f"KeyVault(cached_secrets={cached_count})"
