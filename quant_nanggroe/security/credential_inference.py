"""Smart Credential Detection — Infer exchange/broker from API key format.

Provides utilities for detecting which exchange or broker an API key
belongs to, validating credential completeness, and testing credential
validity via read-only operations.

Features
--------
* Detect exchange/broker from API key format
* Validate credential completeness (key + secret + optional passphrase)
* Test credential validity (read-only operations only)
* Support for Alpaca, Binance, Coinbase, OKX, Bybit, Kraken, Solana

Security
--------
Credential testing uses **read-only** operations only (e.g. fetching
account balance). No trading or withdrawal operations are performed.
Credentials are never logged.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExchangeType(str, Enum):
    """Supported exchange/broker types.

    Attributes
    ----------
    ALPACA:
        Alpaca paper/live trading (US equities).
    BINANCE:
        Binance cryptocurrency exchange.
    COINBASE:
        Coinbase Pro cryptocurrency exchange.
    OKX:
        OKX cryptocurrency exchange.
    BYBIT:
        Bybit cryptocurrency exchange.
    KRAKEN:
        Kraken cryptocurrency exchange.
    SOLANA:
        Solana blockchain (Jupiter V6 swaps).
    UNKNOWN:
        Could not detect exchange type.
    """

    ALPACA = "alpaca"
    BINANCE = "binance"
    COINBASE = "coinbase"
    OKX = "okx"
    BYBIT = "bybit"
    KRAKEN = "kraken"
    SOLANA = "solana"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CredentialCheck(BaseModel):
    """Result of a credential completeness and validity check.

    Attributes
    ----------
    exchange_type:
        Detected exchange type.
    is_complete:
        Whether all required credentials are present.
    is_valid:
        Whether the credentials were verified as valid.
    missing_fields:
        List of missing required fields.
    warnings:
        List of non-critical warnings.
    error:
        Error message if validation failed.
    details:
        Additional details about the check.
    """

    exchange_type: ExchangeType = ExchangeType.UNKNOWN
    is_complete: bool = False
    is_valid: Optional[bool] = None
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Key format patterns
# ---------------------------------------------------------------------------

# Each exchange has characteristic API key prefixes/formats
_EXCHANGE_KEY_PATTERNS: Dict[ExchangeType, Dict[str, Any]] = {
    ExchangeType.ALPACA: {
        "key_prefixes": ["PK", "AK"],
        "key_length_range": (20, 80),
        "requires_secret": True,
        "requires_passphrase": False,
        "sandbox_prefix": "PK",
    },
    ExchangeType.BINANCE: {
        "key_prefixes": [],
        "key_length_range": (60, 70),
        "requires_secret": True,
        "requires_passphrase": False,
    },
    ExchangeType.COINBASE: {
        "key_prefixes": [],
        "key_length_range": (20, 40),
        "requires_secret": True,
        "requires_passphrase": True,
    },
    ExchangeType.OKX: {
        "key_prefixes": [],
        "key_length_range": (20, 40),
        "requires_secret": True,
        "requires_passphrase": True,
    },
    ExchangeType.BYBIT: {
        "key_prefixes": [],
        "key_length_range": (20, 40),
        "requires_secret": True,
        "requires_passphrase": False,
    },
    ExchangeType.KRAKEN: {
        "key_prefixes": [],
        "key_length_range": (20, 40),
        "requires_secret": True,
        "requires_passphrase": False,
    },
    ExchangeType.SOLANA: {
        "key_prefixes": [],
        "key_length_range": (80, 100),
        "requires_secret": False,
        "requires_passphrase": False,
        "is_base58": True,
    },
}


# ---------------------------------------------------------------------------
# CredentialInference
# ---------------------------------------------------------------------------

class CredentialInference:
    """Smart credential detection and validation.

    Detects the exchange/broker from API key format, validates
    credential completeness, and optionally tests credential validity
    via read-only operations.

    Examples
    --------
    .. code-block:: python

        inference = CredentialInference()

        # Detect exchange type
        exchange = inference.detect_exchange("PKABCD1234...")
        assert exchange == ExchangeType.ALPACA

        # Validate credentials
        check = inference.validate_credentials(
            exchange_type=ExchangeType.ALPACA,
            api_key="<placeholder>",
            api_secret="<placeholder>",
        )
        assert check.is_complete
    """

    def detect_exchange(
        self,
        api_key: str,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> ExchangeType:
        """Detect the exchange/broker type from API key format.

        Parameters
        ----------
        api_key:
            The API key to analyze.
        api_secret:
            Optional API secret (used for additional heuristics).
        passphrase:
            Optional passphrase (narrows down exchanges that require it).

        Returns
        -------
        ExchangeType
            Detected exchange type, or ``UNKNOWN`` if not recognized.
        """
        if not api_key:
            return ExchangeType.UNKNOWN

        # Check Alpaca prefixes (most distinctive)
        if api_key.startswith("PK") or api_key.startswith("AK"):
            if len(api_key) >= 20:
                return ExchangeType.ALPACA

        # Check Solana (Base58 private keys are typically 88 chars)
        if len(api_key) >= 80:
            try:
                import base58  # type: ignore[import-untyped]
                base58.b58decode(api_key)
                return ExchangeType.SOLANA
            except (ImportError, Exception):
                # Fallback: check if it looks like Base58
                if all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in api_key):
                    return ExchangeType.SOLANA

        # Binance keys are typically 64 hex characters
        if len(api_key) == 64:
            try:
                int(api_key, 16)
                return ExchangeType.BINANCE
            except ValueError:
                pass

        # If passphrase is provided, likely Coinbase or OKX
        if passphrase:
            return ExchangeType.OKX  # Default guess

        # Check by length
        key_len = len(api_key)
        if 60 <= key_len <= 70:
            return ExchangeType.BINANCE
        if 20 <= key_len <= 40:
            if api_secret:
                return ExchangeType.BYBIT  # Reasonable guess
            return ExchangeType.KRAKEN

        return ExchangeType.UNKNOWN

    def validate_credentials(
        self,
        exchange_type: ExchangeType,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> CredentialCheck:
        """Validate credential completeness for a specific exchange.

        Parameters
        ----------
        exchange_type:
            The target exchange type.
        api_key:
            API key.
        api_secret:
            API secret.
        passphrase:
            Optional passphrase.

        Returns
        -------
        CredentialCheck
            Validation result with missing fields and warnings.
        """
        pattern = _EXCHANGE_KEY_PATTERNS.get(exchange_type, {})
        missing: List[str] = []
        warnings: List[str] = []

        # Check required fields
        if pattern.get("requires_secret", True) and not api_secret:
            missing.append("api_secret")

        if pattern.get("requires_passphrase", False) and not passphrase:
            missing.append("passphrase")

        if not api_key:
            missing.append("api_key")

        # Validate key format
        if api_key:
            key_prefixes = pattern.get("key_prefixes", [])
            if key_prefixes and not any(api_key.startswith(p) for p in key_prefixes):
                warnings.append(
                    f"API key doesn't start with expected prefix: {key_prefixes}"
                )

            key_range = pattern.get("key_length_range")
            if key_range and not (key_range[0] <= len(api_key) <= key_range[1]):
                warnings.append(
                    f"API key length {len(api_key)} is outside expected range "
                    f"{key_range[0]}-{key_range[1]}"
                )

        is_complete = len(missing) == 0

        return CredentialCheck(
            exchange_type=exchange_type,
            is_complete=is_complete,
            missing_fields=missing,
            warnings=warnings,
        )

    async def test_credentials(
        self,
        exchange_type: ExchangeType,
        api_key: str,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        sandbox: bool = True,
    ) -> CredentialCheck:
        """Test credential validity using read-only operations.

        Performs a minimal read-only API call (e.g. get account info)
        to verify the credentials are valid. **No trading operations
        are performed.**

        Parameters
        ----------
        exchange_type:
            The target exchange type.
        api_key:
            API key.
        api_secret:
            API secret.
        passphrase:
            Optional passphrase.
        sandbox:
            Use sandbox/testnet mode.

        Returns
        -------
        CredentialCheck
            Validation result including validity test.
        """
        # First validate completeness
        check = self.validate_credentials(
            exchange_type=exchange_type,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )

        if not check.is_complete:
            check.is_valid = False
            check.error = "Incomplete credentials"
            return check

        # Test credentials based on exchange type
        try:
            if exchange_type == ExchangeType.ALPACA:
                is_valid = await self._test_alpaca(api_key, api_secret or "", sandbox)
            elif exchange_type == ExchangeType.SOLANA:
                is_valid = await self._test_solana(api_key)
            else:
                # For other exchanges, just mark as untested
                check.is_valid = None
                check.warnings.append(
                    f"Credential testing not implemented for {exchange_type.value}"
                )
                return check

            check.is_valid = is_valid
            if not is_valid:
                check.error = "Credential validation failed"

        except Exception as exc:
            check.is_valid = False
            check.error = str(exc)

        return check

    # ----- Exchange-specific test methods -----

    async def _test_alpaca(
        self, api_key: str, api_secret: str, sandbox: bool
    ) -> bool:
        """Test Alpaca credentials by fetching account info.

        Parameters
        ----------
        api_key:
            Alpaca API key.
        api_secret:
            Alpaca API secret.
        sandbox:
            Use paper trading.

        Returns
        -------
        bool
        """
        try:
            from alpaca.trading.client import TradingClient  # type: ignore[import-untyped]

            client = TradingClient(
                api_key=api_key,
                secret_key=api_secret,
                paper=sandbox,
            )
            account = client.get_account()
            return account is not None
        except ImportError:
            logger.warning("alpaca-py not installed, cannot test Alpaca credentials")
            return False
        except Exception as exc:
            logger.debug("Alpaca credential test failed: %s", exc)
            return False

    async def _test_solana(self, private_key: str) -> bool:
        """Test Solana credentials by checking SOL balance.

        Parameters
        ----------
        private_key:
            Base58-encoded private key.

        Returns
        -------
        bool
        """
        try:
            from quant_nanggroe.exchange.solana.wallet import SolanaWallet

            wallet = SolanaWallet(private_key_bs58=private_key)
            balance = await wallet.get_sol_balance()
            return balance >= 0
        except Exception as exc:
            logger.debug("Solana credential test failed: %s", exc)
            return False

    def get_required_fields(self, exchange_type: ExchangeType) -> List[str]:
        """Get the list of required credential fields for an exchange.

        Parameters
        ----------
        exchange_type:
            Target exchange type.

        Returns
        -------
        list of str
            Required field names.
        """
        pattern = _EXCHANGE_KEY_PATTERNS.get(exchange_type, {})
        fields = ["api_key"]

        if pattern.get("requires_secret", True):
            fields.append("api_secret")

        if pattern.get("requires_passphrase", False):
            fields.append("passphrase")

        return fields

    def __repr__(self) -> str:
        return f"CredentialInference(supported={len(_EXCHANGE_KEY_PATTERNS)} exchanges)"
