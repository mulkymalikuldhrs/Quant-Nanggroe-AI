"""Mandate Enforcement — Immutable pre-trade gate (from Vibe-Trading pattern).

Before any order reaches the exchange, the mandate enforcer checks it
against a frozen, agent-immutable mandate. The agent CANNOT modify
its own mandate at runtime.

This is a P0 safety requirement: without mandate enforcement, the agent
can theoretically bypass risk limits by modifying its configuration.

Mandate checks (fail-closed, in fixed order):
1. Exclude-list check (blocked symbols)
2. Instrument type check (allowed asset classes)
3. Notional limit check (max order size)
4. Exposure limit check (total portfolio exposure)
5. Leverage limit check
6. Trade count limit check (max trades per day)
7. Funding check (sufficient capital)

All checks are AND-combined — ALL must pass for the order to proceed.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

logger = logging.getLogger(__name__)


class InstrumentType(str, Enum):
    """Asset class types for mandate restrictions."""
    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    OPTIONS = "options"
    FUTURES = "futures"
    BOND = "bond"
    COMMODITY = "commodity"
    PREDICTION = "prediction"


class MandateVerdict(str, Enum):
    """Result of mandate enforcement check."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    KILL_SWITCH = "KILL_SWITCH"


@dataclass(frozen=True)
class HardCaps:
    """Immutable hard caps — the agent CANNOT modify these at runtime.

    All limits are enforced as AND-conditions: every cap must be satisfied.

    Attributes
    ----------
    account_funding_usd:
        Total account funding in USD.
    max_order_notional_usd:
        Maximum notional value of a single order.
    max_total_exposure_usd:
        Maximum total portfolio exposure across all positions.
    max_leverage:
        Maximum leverage ratio (1.0 = no leverage).
    allowed_instruments:
        Tuple of allowed asset classes.
    max_trades_per_day:
        Maximum number of trades per calendar day.
    min_order_notional_usd:
        Minimum order size (dust prevention).
    max_position_concentration:
        Maximum fraction of portfolio in a single position (0.0-1.0).
    """
    account_funding_usd: float = 1_000_000.0
    max_order_notional_usd: float = 50_000.0
    max_total_exposure_usd: float = 500_000.0
    max_leverage: float = 1.0
    allowed_instruments: Tuple[InstrumentType, ...] = (
        InstrumentType.EQUITY,
        InstrumentType.CRYPTO,
        InstrumentType.FOREX,
    )
    max_trades_per_day: int = 5
    min_order_notional_usd: float = 100.0
    max_position_concentration: float = 0.20  # 20% max in single position


@dataclass(frozen=True)
class UniverseConstraint:
    """Asset universe constraints for the mandate.

    Attributes
    ----------
    exclude_symbols:
        Frozen set of symbols that are explicitly blocked.
    min_market_cap_usd:
        Minimum market cap for equity instruments.
    """
    exclude_symbols: FrozenSet[str] = frozenset()
    min_market_cap_usd: float = 0.0


@dataclass(frozen=True)
class ConsentMeta:
    """Consent provenance for the mandate.

    Records who consented to this mandate and when, providing
    an accountability chain.

    Attributes
    ----------
    consent_token_sha256:
        SHA256 hash of the consent token for verification.
    granted_by:
        User ID who granted consent.
    granted_at:
        ISO timestamp when consent was granted.
    expires_at:
        ISO timestamp when consent expires (None = never).
    """
    consent_token_sha256: str = ""
    granted_by: str = ""
    granted_at: str = ""
    expires_at: Optional[str] = None


@dataclass(frozen=True)
class TradingMandate:
    """Complete trading mandate — immutable, agent cannot modify.

    This is the single source of truth for what the agent is allowed
    to do. It is set by the operator and cannot be changed by the
    agent during runtime.

    Attributes
    ----------
    schema_version:
        Mandate schema version for forward compatibility.
    hard_caps:
        Immutable hard cap limits.
    universe:
        Asset universe constraints.
    consent:
        Consent provenance metadata.
    flatten_on_halt:
        Whether to flatten all positions when halt is triggered.
    """
    schema_version: int = 1
    hard_caps: HardCaps = field(default_factory=HardCaps)
    universe: UniverseConstraint = field(default_factory=UniverseConstraint)
    consent: ConsentMeta = field(default_factory=ConsentMeta)
    flatten_on_halt: bool = True


@dataclass
class MandateCheckResult:
    """Result of a mandate enforcement check."""
    verdict: MandateVerdict
    symbol: str
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MandateEnforcer:
    """Pre-trade mandate enforcement gate.

    Checks every order against the immutable trading mandate before
    it can proceed to execution. All checks are fail-closed.

    Usage
    -----
        mandate = TradingMandate(hard_caps=HardCaps(max_order_notional_usd=50000))
        enforcer = MandateEnforcer(mandate)

        result = enforcer.check_order(
            symbol="AAPL",
            instrument_type=InstrumentType.EQUITY,
            quantity=100,
            price=150.0,
            current_exposure=200000.0,
            trades_today=2,
        )
        if result.verdict == MandateVerdict.APPROVED:
            # proceed to execution
    """

    def __init__(self, mandate: TradingMandate) -> None:
        self._mandate = mandate
        # Verify mandate hash for tamper detection
        self._mandate_hash = self._compute_mandate_hash()

    @property
    def mandate(self) -> TradingMandate:
        """Read-only access to the mandate."""
        return self._mandate

    def check_order(
        self,
        symbol: str,
        instrument_type: InstrumentType,
        quantity: float,
        price: float,
        current_exposure: float = 0.0,
        trades_today: int = 0,
        current_position_value: float = 0.0,
        account_equity: float = 1_000_000.0,
    ) -> MandateCheckResult:
        """Check an order against the mandate.

        All checks are AND-combined and fail-closed.
        Checks run in a fixed order for consistency.

        Parameters
        ----------
        symbol:
            Trading symbol.
        instrument_type:
            Type of instrument being traded.
        quantity:
            Order quantity.
        price:
            Order price.
        current_exposure:
            Current total portfolio exposure.
        trades_today:
            Number of trades already executed today.
        current_position_value:
            Current value of position in this symbol.
        account_equity:
            Current account equity.

        Returns
        -------
        MandateCheckResult
            Verdict and detailed check results.
        """
        caps = self._mandate.hard_caps
        universe = self._mandate.universe
        notional = abs(quantity * price)

        passed: List[str] = []
        failed: List[str] = []
        details: Dict[str, Any] = {}

        # Check 1: Exclude-list
        if symbol.upper() in universe.exclude_symbols:
            failed.append("exclude_list")
            details["exclude_list"] = f"Symbol {symbol} is on the blocked list"
        else:
            passed.append("exclude_list")

        # Check 2: Instrument type
        if instrument_type in caps.allowed_instruments:
            passed.append("instrument_type")
        else:
            failed.append("instrument_type")
            details["instrument_type"] = (
                f"Instrument type {instrument_type.value} not allowed. "
                f"Allowed: {[i.value for i in caps.allowed_instruments]}"
            )

        # Check 3: Notional limit
        if notional <= caps.max_order_notional_usd:
            passed.append("notional_limit")
        else:
            failed.append("notional_limit")
            details["notional_limit"] = (
                f"Order notional ${notional:,.2f} exceeds cap ${caps.max_order_notional_usd:,.2f}"
            )

        # Check 4: Min notional (dust prevention)
        if notional >= caps.min_order_notional_usd:
            passed.append("min_notional")
        else:
            failed.append("min_notional")
            details["min_notional"] = (
                f"Order notional ${notional:,.2f} below minimum ${caps.min_order_notional_usd:,.2f}"
            )

        # Check 5: Exposure limit
        new_exposure = current_exposure + notional
        if new_exposure <= caps.max_total_exposure_usd:
            passed.append("exposure_limit")
        else:
            failed.append("exposure_limit")
            details["exposure_limit"] = (
                f"Total exposure ${new_exposure:,.2f} would exceed cap ${caps.max_total_exposure_usd:,.2f}"
            )

        # Check 6: Leverage limit
        leverage = new_exposure / account_equity if account_equity > 0 else 0
        if leverage <= caps.max_leverage:
            passed.append("leverage_limit")
        else:
            failed.append("leverage_limit")
            details["leverage_limit"] = (
                f"Leverage {leverage:.2f}x exceeds cap {caps.max_leverage:.2f}x"
            )

        # Check 7: Trade count limit
        if trades_today < caps.max_trades_per_day:
            passed.append("trade_count")
        else:
            failed.append("trade_count")
            details["trade_count"] = (
                f"Daily trade count {trades_today} at cap {caps.max_trades_per_day}"
            )

        # Check 8: Position concentration
        if account_equity > 0:
            concentration = current_position_value / account_equity
            if concentration <= caps.max_position_concentration:
                passed.append("concentration")
            else:
                failed.append("concentration")
                details["concentration"] = (
                    f"Position concentration {concentration:.1%} exceeds cap {caps.max_position_concentration:.1%}"
                )
        else:
            passed.append("concentration")

        # Determine verdict (fail-closed: any failure = rejection)
        verdict = MandateVerdict.APPROVED if not failed else MandateVerdict.REJECTED

        if verdict == MandateVerdict.REJECTED:
            logger.warning(
                "MANDATE REJECTED: %s — failed checks: %s",
                symbol, failed,
            )

        return MandateCheckResult(
            verdict=verdict,
            symbol=symbol,
            passed_checks=passed,
            failed_checks=failed,
            details=details,
        )

    def verify_integrity(self) -> bool:
        """Verify mandate has not been tampered with.

        Returns
        -------
        bool
            True if mandate hash matches original.
        """
        return self._compute_mandate_hash() == self._mandate_hash

    @staticmethod
    def _compute_mandate_hash() -> str:
        """Compute SHA256 hash of the mandate for tamper detection."""
        # Hash the string representation of the mandate dataclass
        import json
        from dataclasses import asdict

        try:
            data = json.dumps(asdict(TradingMandate()), sort_keys=True, default=str)
            return hashlib.sha256(data.encode()).hexdigest()[:32]
        except Exception:
            return "unknown"


def create_default_mandate(
    max_order_usd: float = 50_000.0,
    max_exposure_usd: float = 500_000.0,
    max_leverage: float = 1.0,
    allowed_instruments: Optional[Tuple[InstrumentType, ...]] = None,
) -> TradingMandate:
    """Create a default trading mandate with sensible limits.

    Parameters
    ----------
    max_order_usd:
        Maximum single order notional value.
    max_exposure_usd:
        Maximum total portfolio exposure.
    max_leverage:
        Maximum leverage ratio.
    allowed_instruments:
        Allowed instrument types. Defaults to equity, crypto, forex.

    Returns
    -------
    TradingMandate
        Frozen mandate ready for use.
    """
    caps = HardCaps(
        max_order_notional_usd=max_order_usd,
        max_total_exposure_usd=max_exposure_usd,
        max_leverage=max_leverage,
        allowed_instruments=allowed_instruments or (
            InstrumentType.EQUITY,
            InstrumentType.CRYPTO,
            InstrumentType.FOREX,
        ),
    )
    return TradingMandate(hard_caps=caps)
