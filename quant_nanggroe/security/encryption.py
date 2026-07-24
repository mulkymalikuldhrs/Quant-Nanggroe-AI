"""Encryption at rest — Fernet-based symmetric encryption for sensitive data.

Provides EncryptedStore for encrypting/decrypting files and values
using Fernet (AES-128-CBC with HMAC-SHA256).  Only encrypts when the
QNAI_ENCRYPTION_KEY environment variable is set.  Without the key,
all operations pass through (no-op) so the system works transparently
in development.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None  # type: ignore
    InvalidToken = type("InvalidToken", (Exception,), {})  # type: ignore


def _get_fernet() -> Optional["Fernet"]:
    """Return a Fernet instance if QNAI_ENCRYPTION_KEY is set, else None."""
    key = os.environ.get("QNAI_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        if Fernet is None:
            raise ImportError("cryptography package not installed")
        # If the key isn't base64-encoded 32 bytes, derive one
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, base64.binascii.Error):
            # Key is not valid Fernet format — derive via SHA-256
            import hashlib
            derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
            return Fernet(derived)
    except Exception as exc:
        logger.warning("Failed to initialise encryption: %s", exc)
        return None


class EncryptedStore:
    """Simple encryption for sensitive data at rest.

    Uses Fernet (symmetric encryption) for state files and trail files
    when QNAI_ENCRYPTION_KEY is set.  Without the key all operations
    pass through — the system remains functional in development.
    """

    def __init__(self) -> None:
        self._fernet = _get_fernet()
        self._enabled = self._fernet is not None
        if self._enabled:
            logger.info("EncryptedStore active — data will be encrypted at rest")
        else:
            logger.info("EncryptedStore pass-through — set QNAI_ENCRYPTION_KEY for encryption")

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ── File operations ────────────────────────────────────────────

    def encrypt_file(self, path: str | Path) -> None:
        """Encrypt a file in-place.  If encryption is disabled this is a no-op."""
        if not self._enabled:
            return
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        plain = path.read_bytes()
        encrypted = self._fernet.encrypt(plain)  # type: ignore[union-attr]
        path.write_bytes(encrypted)
        logger.debug("Encrypted %s", path)

    def decrypt_file(self, path: str | Path) -> bytes:
        """Decrypt a file in-place.  If encryption is disabled, read plaintext."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        data = path.read_bytes()
        if not self._enabled:
            return data
        try:
            return self._fernet.decrypt(data)  # type: ignore[union-attr]
        except InvalidToken:
            raise ValueError(f"File {path} is not valid encrypted data or key has changed")

    # ── Value operations ───────────────────────────────────────────

    def encrypt_value(self, value: str) -> str:
        """Encrypt a string value.
        
        Returns base64-encoded ciphertext when QNAI_ENCRYPTION_KEY is set.
        When encryption is disabled (no key), returns the input value
        unchanged — pass-through mode.  This is a known limitation:
        production deployments MUST set QNAI_ENCRYPTION_KEY.
        
        // ponytail: upgrade to AES-256-GCM with key-wrapping:
        //   pip install cryptography
        //   from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        //   key = AESGCM.generate_key(bit_length=256)
        //   aesgcm = AESGCM(key)
        //   nonce = os.urandom(12)
        //   ct = aesgcm.encrypt(nonce, plaintext, aad)
        //   Store nonce + ct together (nonce prepended).
        // Key management: wrap with KMS (AWS KMS / GCP Cloud KMS)
        // or derive via argon2id from a master passphrase.
        """
        if not self._enabled:
            return value
        encrypted = self._fernet.encrypt(value.encode())  # type: ignore[union-attr]
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_value(self, value: str) -> str:
        """Decrypt a base64-encoded ciphertext string.
        
        When encryption is disabled (no key), returns the input value
        unchanged — pass-through mode.
        """
        if not self._enabled:
            return value
        try:
            raw = base64.urlsafe_b64decode(value.encode())
            return self._fernet.decrypt(raw).decode()  # type: ignore[union-attr]
        except (InvalidToken, base64.binascii.Error, ValueError):
            # If value wasn't actually encrypted, return as-is
            return value

    # ── Context manager helpers ────────────────────────────────────

    def __enter__(self) -> "EncryptedStore":
        return self

    def __exit__(self, *args: object) -> None:
        pass
