"""Trading Guards Pipeline — Pre-trade validation pipeline for the exchange layer.

Provides a composable guard pipeline that validates orders before submission
to an exchange. Each guard checks a specific condition and returns a
Pass/Fail result with a reason.

Guards
------
- **WhitelistGuard**: Only trade whitelisted symbols
- **CooldownGuard**: Minimum time between trades on same symbol
- **MaxPositionGuard**: Maximum position size enforcement
- **GuardPipeline**: Compose and run all guards in sequence

All guard decisions are logged for audit purposes.

Usage
-----
.. code-block:: python

    pipeline = GuardPipeline()
    pipeline.add_guard(WhitelistGuard(allowed_symbols=["BTC/USDT", "ETH/USDT"]))
    pipeline.add_guard(CooldownGuard(seconds=60))
    pipeline.add_guard(MaxPositionGuard(max_pct=0.10))

    result = pipeline.check(order)
    if result.passed:
        # Submit order
    else:
        # Log reason
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from quant_nanggroe.exchange.base import OrderError  # ponytail: fail-closed wraps guard exceptions as OrderError
from quant_nanggroe.types.orders import Order, OrderSide

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guard result types
# ---------------------------------------------------------------------------

class GuardVerdict(str, Enum):
    """Result verdict from a guard check."""

    PASS = "pass"
    FAIL = "fail"


class GuardResult(BaseModel):
    """Result from a single guard check.

    Attributes:
        verdict: Whether the order passed or failed.
        guard_name: Name of the guard that produced this result.
        reason: Human-readable reason (empty on pass).
        details: Additional details about the decision.
    """

    verdict: GuardVerdict
    guard_name: str
    reason: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Whether the order passed this guard."""
        return self.verdict == GuardVerdict.PASS

    model_config = {"from_attributes": True}


class PipelineResult(BaseModel):
    """Aggregated result from running all guards in a pipeline.

    Attributes:
        passed: Whether all guards passed.
        results: Individual guard results in execution order.
        failed_guards: Names of guards that failed.
        reasons: Concatenated failure reasons.
    """

    passed: bool
    results: List[GuardResult] = Field(default_factory=list)
    failed_guards: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Abstract guard base
# ---------------------------------------------------------------------------

class BaseGuard(ABC):
    """Abstract base class for trading guards.

    All guards must implement the :meth:`check` method, which takes an
    order and returns a :class:`GuardResult`. Guards should also
    implement :meth:`name` to identify themselves in logs and results.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this guard."""

    @abstractmethod
    def check(self, order: Order, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """Check whether an order passes this guard.

        Args:
            order: The order to validate.
            context: Optional context dict with additional info
                (e.g., current positions, portfolio value).

        Returns:
            :class:`GuardResult` with pass/fail verdict and reason.
        """


# ---------------------------------------------------------------------------
# Whitelist Guard
# ---------------------------------------------------------------------------

class WhitelistGuard(BaseGuard):
    """Only allow trades for whitelisted symbols.

    If no whitelist is set, all symbols are allowed (unless blocked).
    The blocked list takes precedence over the whitelist.

    Args:
        allowed_symbols: If set, only these symbols can be traded.
        blocked_symbols: These symbols are always blocked.
    """

    def __init__(
        self,
        allowed_symbols: Optional[List[str]] = None,
        blocked_symbols: Optional[List[str]] = None,
    ) -> None:
        self._allowed: Optional[Set[str]] = (
            set(s.upper() for s in allowed_symbols) if allowed_symbols else None
        )
        self._blocked: Set[str] = (
            set(s.upper() for s in blocked_symbols) if blocked_symbols else set()
        )

    @property
    def name(self) -> str:
        return "WhitelistGuard"

    def check(self, order: Order, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """Check if the order's symbol is allowed."""
        symbol_upper = order.symbol.upper()

        # Check blocked list first
        if symbol_upper in self._blocked:
            reason = f"Symbol {order.symbol} is on the blocked list"
            logger.info("WhitelistGuard: FAIL — %s", reason)
            return GuardResult(
                verdict=GuardVerdict.FAIL,
                guard_name=self.name,
                reason=reason,
                details={"symbol": order.symbol, "blocked": True},
            )

        # Check whitelist
        if self._allowed is not None and symbol_upper not in self._allowed:
            reason = f"Symbol {order.symbol} is not on the approved whitelist"
            logger.info("WhitelistGuard: FAIL — %s", reason)
            return GuardResult(
                verdict=GuardVerdict.FAIL,
                guard_name=self.name,
                reason=reason,
                details={"symbol": order.symbol, "whitelisted": False},
            )

        logger.debug("WhitelistGuard: PASS — %s", order.symbol)
        return GuardResult(
            verdict=GuardVerdict.PASS,
            guard_name=self.name,
            details={"symbol": order.symbol},
        )

    def add_symbol(self, symbol: str) -> None:
        """Add a symbol to the whitelist."""
        if self._allowed is not None:
            self._allowed.add(symbol.upper())

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from the whitelist."""
        if self._allowed is not None:
            self._allowed.discard(symbol.upper())

    def block_symbol(self, symbol: str) -> None:
        """Block a symbol."""
        self._blocked.add(symbol.upper())

    def unblock_symbol(self, symbol: str) -> None:
        """Unblock a symbol."""
        self._blocked.discard(symbol.upper())

    @property
    def allowed_symbols(self) -> Optional[Set[str]]:
        """Get the set of allowed symbols."""
        return self._allowed

    @property
    def blocked_symbols(self) -> Set[str]:
        """Get the set of blocked symbols."""
        return self._blocked


# ---------------------------------------------------------------------------
# Cooldown Guard
# ---------------------------------------------------------------------------

class CooldownGuard(BaseGuard):
    """Enforce minimum time between trades on the same symbol.

    Args:
        seconds: Minimum cooldown period in seconds.
        per_symbol: If True, cooldown is per-symbol. If False, global cooldown.
    """

    def __init__(
        self,
        seconds: float = 60.0,
        per_symbol: bool = True,
    ) -> None:
        self._cooldown_seconds = seconds
        self._per_symbol = per_symbol
        self._last_trade_time: Dict[str, float] = {}
        self._global_last_trade_time: float = 0.0

    @property
    def name(self) -> str:
        return "CooldownGuard"

    def check(self, order: Order, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """Check if the cooldown period has elapsed."""
        now = time.time()

        if self._per_symbol:
            last_time = self._last_trade_time.get(order.symbol, 0.0)
        else:
            last_time = self._global_last_trade_time

        elapsed = now - last_time

        if elapsed < self._cooldown_seconds:
            remaining = self._cooldown_seconds - elapsed
            reason = (
                f"Cooldown active for {order.symbol}: "
                f"{remaining:.1f}s remaining "
                f"(cooldown={self._cooldown_seconds}s)"
            )
            logger.info("CooldownGuard: FAIL — %s", reason)
            return GuardResult(
                verdict=GuardVerdict.FAIL,
                guard_name=self.name,
                reason=reason,
                details={
                    "symbol": order.symbol,
                    "cooldown_seconds": self._cooldown_seconds,
                    "remaining_seconds": round(remaining, 2),
                    "elapsed_seconds": round(elapsed, 2),
                },
            )

        logger.debug("CooldownGuard: PASS — %s (elapsed=%.1fs)", order.symbol, elapsed)
        return GuardResult(
            verdict=GuardVerdict.PASS,
            guard_name=self.name,
            details={"symbol": order.symbol, "elapsed_seconds": round(elapsed, 2)},
        )

    def record_trade(self, symbol: str) -> None:
        """Record that a trade was executed for a symbol.

        Call this after a trade is successfully placed.

        Args:
            symbol: Trading symbol.
        """
        now = time.time()
        self._last_trade_time[symbol] = now
        self._global_last_trade_time = now

    def get_cooldown_remaining(self, symbol: str) -> float:
        """Get remaining cooldown time for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Remaining seconds (0 if no cooldown active).
        """
        if self._per_symbol:
            last_time = self._last_trade_time.get(symbol, 0.0)
        else:
            last_time = self._global_last_trade_time

        elapsed = time.time() - last_time
        return max(0.0, self._cooldown_seconds - elapsed)

    def reset(self, symbol: Optional[str] = None) -> None:
        """Reset cooldown for a symbol or all symbols.

        Args:
            symbol: Symbol to reset, or None for all.
        """
        if symbol:
            self._last_trade_time.pop(symbol, None)
        else:
            self._last_trade_time.clear()
            self._global_last_trade_time = 0.0


# ---------------------------------------------------------------------------
# Max Position Guard
# ---------------------------------------------------------------------------

class MaxPositionGuard(BaseGuard):
    """Enforce maximum position size limits.

    Prevents position concentration by checking the notional value of
    the resulting position against a percentage of portfolio or an
    absolute notional limit.

    Args:
        max_pct: Maximum position as fraction of portfolio (0.10 = 10%).
        max_notional: Maximum absolute notional value for any single position.
        portfolio_value: Current portfolio value for percentage calculations.
    """

    def __init__(
        self,
        max_pct: float = 0.10,
        max_notional: Optional[float] = None,
        portfolio_value: float = 1_000_000.0,
    ) -> None:
        self._max_pct = max_pct
        self._max_notional = max_notional
        self._portfolio_value = portfolio_value
        self._current_positions: Dict[str, float] = {}  # symbol -> notional value

    @property
    def name(self) -> str:
        return "MaxPositionGuard"

    def check(self, order: Order, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """Check if the order would exceed position limits."""
        # Use context for current portfolio value if available
        portfolio_value = context.get("portfolio_value", self._portfolio_value) if context else self._portfolio_value
        current_positions = context.get("current_positions", self._current_positions) if context else self._current_positions

        price = order.price or 0.0
        order_notional = order.quantity * price
        current_notional = current_positions.get(order.symbol, 0.0)

        if order.side == OrderSide.BUY:
            new_notional = current_notional + order_notional
        else:
            new_notional = max(0.0, current_notional - order_notional)

        # Check percentage limit
        max_allowed = portfolio_value * self._max_pct
        if new_notional > max_allowed and portfolio_value > 0:
            reason = (
                f"Position would exceed {self._max_pct:.0%} of portfolio "
                f"({new_notional:.0f} > {max_allowed:.0f})"
            )
            logger.info("MaxPositionGuard: FAIL — %s", reason)
            return GuardResult(
                verdict=GuardVerdict.FAIL,
                guard_name=self.name,
                reason=reason,
                details={
                    "symbol": order.symbol,
                    "current_notional": current_notional,
                    "order_notional": order_notional,
                    "new_notional": new_notional,
                    "max_allowed": max_allowed,
                    "max_pct": self._max_pct,
                    "portfolio_value": portfolio_value,
                },
            )

        # Check notional limit
        if self._max_notional and new_notional > self._max_notional:
            reason = (
                f"Position would exceed max notional "
                f"({new_notional:.0f} > {self._max_notional:.0f})"
            )
            logger.info("MaxPositionGuard: FAIL — %s", reason)
            return GuardResult(
                verdict=GuardVerdict.FAIL,
                guard_name=self.name,
                reason=reason,
                details={
                    "symbol": order.symbol,
                    "new_notional": new_notional,
                    "max_notional": self._max_notional,
                },
            )

        logger.debug("MaxPositionGuard: PASS — %s (notional=%.0f)", order.symbol, new_notional)
        return GuardResult(
            verdict=GuardVerdict.PASS,
            guard_name=self.name,
            details={"symbol": order.symbol, "new_notional": new_notional},
        )

    def update_position(self, symbol: str, notional: float) -> None:
        """Update the tracked position notional value.

        Args:
            symbol: Trading symbol.
            notional: New position notional value.
        """
        self._current_positions[symbol] = notional

    def update_portfolio_value(self, value: float) -> None:
        """Update the total portfolio value.

        Args:
            value: New portfolio value.
        """
        self._portfolio_value = value

    def remove_position(self, symbol: str) -> None:
        """Remove a position from tracking.

        Args:
            symbol: Trading symbol.
        """
        self._current_positions.pop(symbol, None)


# ---------------------------------------------------------------------------
# Guard Pipeline
# ---------------------------------------------------------------------------

class GuardPipeline:
    """Composable pipeline that runs all guards in sequence.

    Guards are executed in the order they are added. If any guard fails,
    the pipeline stops and returns a failure result. All guard decisions
    are logged.

    Usage
    -----
    .. code-block:: python

        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard(allowed_symbols=["BTC/USDT"]))
        pipeline.add_guard(CooldownGuard(seconds=60))
        pipeline.add_guard(MaxPositionGuard(max_pct=0.10))

        result = pipeline.check(order)
        if not result.passed:
            print("Order rejected:", result.reasons)
    """

    def __init__(self, name: str = "default") -> None:
        """Initialize the pipeline.

        Args:
            name: Human-readable name for this pipeline.
        """
        self._name = name
        self._guards: List[BaseGuard] = []

    @property
    def name(self) -> str:
        """Pipeline name."""
        return self._name

    @property
    def guards(self) -> List[BaseGuard]:
        """List of guards in this pipeline."""
        return list(self._guards)

    def add_guard(self, guard: BaseGuard) -> None:
        """Add a guard to the pipeline.

        Args:
            guard: A :class:`BaseGuard` implementation.

        Raises:
            TypeError: If the guard is not a BaseGuard instance.
        """
        if not isinstance(guard, BaseGuard):
            raise TypeError(f"Expected BaseGuard instance, got {type(guard).__name__}")
        self._guards.append(guard)
        logger.info("GuardPipeline [%s]: Added guard: %s", self._name, guard.name)

    def remove_guard(self, guard_name: str) -> bool:
        """Remove a guard by name.

        Args:
            guard_name: Name of the guard to remove.

        Returns:
            True if a guard was removed, False otherwise.
        """
        for i, guard in enumerate(self._guards):
            if guard.name == guard_name:
                self._guards.pop(i)
                logger.info("GuardPipeline [%s]: Removed guard: %s", self._name, guard_name)
                return True
        return False

    def check(
        self,
        order: Order,
        context: Optional[Dict[str, Any]] = None,
        fail_fast: bool = True,
    ) -> PipelineResult:
        """Run all guards against an order.

        Args:
            order: The order to validate.
            context: Optional context dict with additional info.
            fail_fast: If True, stop on first failure. If False, run all guards.

        Returns:
            :class:`PipelineResult` with aggregated results.
        """
        results: List[GuardResult] = []
        failed_guards: List[str] = []
        reasons: List[str] = []
        all_passed = True

        for guard in self._guards:
            # ponytail: fail-closed — a guard that raises must reject the order,
            # never let its exception leak and (worse) fall through to PASS.
            try:
                result = guard.check(order, context)
            except OrderError:
                raise  # already a deliberate rejection
            except Exception as exc:  # noqa: BLE001 - any guard failure halts the trade
                logger.error("GuardPipeline [%s]: guard %s raised — FAIL (fail-closed)", self._name, guard.name)
                raise OrderError(
                    f"Guard {guard.name} raised {type(exc).__name__}: {exc}",
                    exchange=self._name,
                    original=exc,
                ) from exc
            results.append(result)

            if not result.passed:
                all_passed = False
                failed_guards.append(result.guard_name)
                if result.reason:
                    reasons.append(result.reason)

                if fail_fast:
                    break

        pipeline_result = PipelineResult(
            passed=all_passed,
            results=results,
            failed_guards=failed_guards,
            reasons=reasons,
        )

        if all_passed:
            logger.info(
                "GuardPipeline [%s]: PASS — %s (all %d guards passed)",
                self._name, order.symbol, len(results),
            )
        else:
            logger.warning(
                "GuardPipeline [%s]: FAIL — %s (failed: %s)",
                self._name, order.symbol, failed_guards,
            )

        return pipeline_result

    def check_single(
        self,
        guard_name: str,
        order: Order,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[GuardResult]:
        """Run a single guard by name.

        Args:
            guard_name: Name of the guard to run.
            order: The order to validate.
            context: Optional context dict.

        Returns:
            :class:`GuardResult` or None if the guard is not found.
        """
        for guard in self._guards:
            if guard.name == guard_name:
                return guard.check(order, context)
        return None

    def get_guard(self, guard_name: str) -> Optional[BaseGuard]:
        """Get a guard by name.

        Args:
            guard_name: Name of the guard.

        Returns:
            The guard instance, or None if not found.
        """
        for guard in self._guards:
            if guard.name == guard_name:
                return guard
        return None

    def clear(self) -> None:
        """Remove all guards from the pipeline."""
        self._guards.clear()
        logger.info("GuardPipeline [%s]: Cleared all guards", self._name)


# ---------------------------------------------------------------------------
# Default pipeline factory (env-driven)
# ---------------------------------------------------------------------------

def build_default_guard_pipeline(
    name: str = "exchange-default",
    allowed_symbols: Optional[List[str]] = None,
    blocked_symbols: Optional[List[str]] = None,
    cooldown_seconds: float = 60.0,
    max_position_pct: float = 0.25,
    max_notional: Optional[float] = None,
    portfolio_value: float = 1_000_000.0,
) -> GuardPipeline:
    """Build a fail-closed pre-trade guard pipeline from explicit args or env.

    Env overrides (only used when the corresponding arg is None):
        QNA_GUARD_ALLOWED   — comma-separated whitelist (e.g. "SOL/USDC,ETH/USDT")
        QNA_GUARD_BLOCKED   — comma-separated blocklist
        QNA_GUARD_COOLDOWN  — float seconds
        QNA_GUARD_MAX_PCT   — float fraction (0.25 = 25%)
        QNA_GUARD_MAX_NOTIONAL — float absolute cap

    Returns a :class:`GuardPipeline` with Whitelist, Cooldown, MaxPosition guards.
    The pipeline is fail-closed by construction: any guard FAIL or exception
    rejects the order (caller must check ``result.passed``).
    """
    import os

    if allowed_symbols is None and os.getenv("QNA_GUARD_ALLOWED"):
        allowed_symbols = [s.strip().upper() for s in os.getenv("QNA_GUARD_ALLOWED").split(",") if s.strip()]
    if blocked_symbols is None and os.getenv("QNA_GUARD_BLOCKED"):
        blocked_symbols = [s.strip().upper() for s in os.getenv("QNA_GUARD_BLOCKED").split(",") if s.strip()]
    if cooldown_seconds is None and os.getenv("QNA_GUARD_COOLDOWN"):
        cooldown_seconds = float(os.getenv("QNA_GUARD_COOLDOWN"))
    if max_position_pct is None and os.getenv("QNA_GUARD_MAX_PCT"):
        max_position_pct = float(os.getenv("QNA_GUARD_MAX_PCT"))
    if max_notional is None and os.getenv("QNA_GUARD_MAX_NOTIONAL"):
        max_notional = float(os.getenv("QNA_GUARD_MAX_NOTIONAL"))

    pipeline = GuardPipeline(name=name)
    pipeline.add_guard(WhitelistGuard(allowed_symbols=allowed_symbols, blocked_symbols=blocked_symbols))
    pipeline.add_guard(CooldownGuard(seconds=cooldown_seconds or 60.0))
    pipeline.add_guard(
        MaxPositionGuard(
            max_pct=max_position_pct or 0.25,
            max_notional=max_notional,
            portfolio_value=portfolio_value,
        )
    )
    return pipeline
