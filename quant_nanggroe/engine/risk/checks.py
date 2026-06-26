"""Constitutional risk guard for the AI-MultiColony finance module.

Implements hardcoded risk limits inspired by HermesQuantOS's
constitutional trading rules:

* 0.5% maximum risk per trade
* 1.0% maximum daily loss
* 3.0% maximum weekly loss
* Position sizing based on volatility and risk budget
* Mandatory stop-loss on all positions

These limits are constitutional – they cannot be overridden by
any agent or configuration.

NOTE: All risk constants are imported from quant_nanggroe.engine.risk.constants
which is the SINGLE SOURCE OF TRUTH for constitutional limits.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

# ── Import from the SINGLE SOURCE OF TRUTH ──────────────────────────────────
from quant_nanggroe.engine.risk.constants import (
    MAX_RISK_PER_TRADE as _MAX_RISK_PER_TRADE_FRAC,     # 0.005 (fraction)
    MAX_DAILY_LOSS as _MAX_DAILY_LOSS_FRAC,               # 0.01 (fraction)
    MAX_WEEKLY_LOSS as _MAX_WEEKLY_LOSS_FRAC,             # 0.03 (fraction)
    MAX_POSITION_SIZE_PCT as _MAX_POSITION_SIZE_FRAC,     # 0.10 (fraction)
    MAX_LEVERAGE as _MAX_LEVERAGE,                         # 3.0
)

# Convert fractions to percentages for this module's API (backward compat)
MAX_RISK_PER_TRADE_PCT: float = _MAX_RISK_PER_TRADE_FRAC * 100   # 0.5%
MAX_DAILY_LOSS_PCT: float = _MAX_DAILY_LOSS_FRAC * 100           # 1.0%
MAX_WEEKLY_LOSS_PCT: float = _MAX_WEEKLY_LOSS_FRAC * 100         # 3.0%
MAX_POSITION_SIZE_PCT: float = _MAX_POSITION_SIZE_FRAC * 100     # 10.0%
MANDATORY_STOP_LOSS_PCT: float = 2.0  # 2% stop-loss required (operational, not constitutional)

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class RiskLevel(str, Enum):
    """Risk assessment level."""
    SAFE = "safe"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"
    BREACH = "breach"


class TradeAction(str, Enum):
    """Proposed trade action."""
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    HOLD = "hold"


# ── Models ───────────────────────────────────────────────────────────────────


class RiskCheckResult(BaseModel):
    """Result from a risk check."""
    model_config = ConfigDict(frozen=False)

    check_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    approved: bool = False
    risk_level: RiskLevel = RiskLevel.SAFE
    proposed_risk_pct: float = 0.0
    max_allowed_risk_pct: float = MAX_RISK_PER_TRADE_PCT
    remaining_daily_budget_pct: float = MAX_DAILY_LOSS_PCT
    remaining_weekly_budget_pct: float = MAX_WEEKLY_LOSS_PCT
    position_size_adjusted: bool = False
    stop_loss_required: float = MANDATORY_STOP_LOSS_PCT
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioSnapshot(BaseModel):
    """Snapshot of current portfolio state."""
    model_config = ConfigDict(frozen=False)

    total_equity: float = 100000.0
    cash: float = 100000.0
    positions: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    max_drawdown_pct: float = 0.0
    unrealized_pnl: float = 0.0

    @property
    def daily_pnl_pct(self) -> float:
        """Daily P&L as percentage of equity."""
        return (self.daily_pnl / self.total_equity * 100) if self.total_equity > 0 else 0.0

    @property
    def weekly_pnl_pct(self) -> float:
        """Weekly P&L as percentage of equity."""
        return (self.weekly_pnl / self.total_equity * 100) if self.total_equity > 0 else 0.0

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def total_position_value(self) -> float:
        return sum(
            pos.get("quantity", 0) * pos.get("current_price", 0)
            for pos in self.positions.values()
        )


class TradeRequest(BaseModel):
    """A proposed trade request."""
    model_config = ConfigDict(frozen=False)

    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    symbol: str = ""
    action: TradeAction = TradeAction.BUY
    quantity: float = 0.0
    price: float = 0.0
    stop_loss_pct: float = MANDATORY_STOP_LOSS_PCT
    take_profit_pct: float = 0.0
    risk_pct: float = 0.0  # Risk as % of portfolio
    strategy: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def notional_value(self) -> float:
        return abs(self.quantity * self.price)


# ── Risk Guard ───────────────────────────────────────────────────────────────


class ConstitutionalRiskGuard:
    """Constitutional risk guard with hardcoded limits.

    All limits are enforced as constitutional constraints that
    cannot be overridden.  Every trade must pass through this
    guard before execution.

    Usage::

        guard = ConstitutionalRiskGuard()
        result = guard.check_trade(
            request=TradeRequest(symbol="AAPL", action=TradeAction.BUY,
                                quantity=10, price=185.0),
            portfolio=PortfolioSnapshot(total_equity=100000),
        )
        if result.approved:
            # Execute trade
            pass
    """

    def __init__(self):
        self._daily_losses: Dict[str, float] = {}  # date_str → loss_pct
        self._weekly_losses: Dict[str, float] = {}  # week_str → loss_pct
        self._check_count: int = 0
        self._approved_count: int = 0
        self._rejected_count: int = 0
        self._adjustment_count: int = 0

    def check_trade(
        self,
        request: TradeRequest,
        portfolio: PortfolioSnapshot,
    ) -> RiskCheckResult:
        """Check a proposed trade against constitutional risk limits.

        Parameters
        ----------
        request:
            The proposed trade.
        portfolio:
            Current portfolio snapshot.

        Returns
        -------
        RiskCheckResult
            Risk assessment with approval status.
        """
        self._check_count += 1
        result = RiskCheckResult()

        # Calculate proposed risk
        if portfolio.total_equity > 0 and request.notional_value > 0:
            proposed_risk_pct = (request.notional_value / portfolio.total_equity) * 100
        else:
            proposed_risk_pct = 0.0
        result.proposed_risk_pct = proposed_risk_pct

        # Check 1: Per-trade risk limit
        if proposed_risk_pct > MAX_POSITION_SIZE_PCT:
            result.warnings.append(
                f"Position size {proposed_risk_pct:.2f}% exceeds max {MAX_POSITION_SIZE_PCT}%"
            )
            # Adjust position size
            adjusted_value = portfolio.total_equity * (MAX_POSITION_SIZE_PCT / 100)
            if request.price > 0:
                adjusted_qty = adjusted_value / request.price
                request.quantity = adjusted_qty
                result.position_size_adjusted = True
                self._adjustment_count += 1
                result.warnings.append(
                    f"Position size adjusted to {adjusted_qty:.2f} shares"
                )
            proposed_risk_pct = MAX_POSITION_SIZE_PCT

        # Check 2: Risk per trade
        if request.risk_pct > MAX_RISK_PER_TRADE_PCT:
            result.reasons.append(
                f"Trade risk {request.risk_pct:.2f}% exceeds max {MAX_RISK_PER_TRADE_PCT}%"
            )
            result.risk_level = RiskLevel.BREACH
            result.approved = False
            self._rejected_count += 1
            return result

        # Check 3: Daily loss budget
        daily_used = abs(min(0, portfolio.daily_pnl_pct))
        remaining_daily = MAX_DAILY_LOSS_PCT - daily_used
        result.remaining_daily_budget_pct = max(0, remaining_daily)

        if remaining_daily <= 0:
            result.reasons.append(
                f"Daily loss budget exhausted ({daily_used:.2f}% used of {MAX_DAILY_LOSS_PCT}%)"
            )
            result.risk_level = RiskLevel.BREACH
            result.approved = False
            self._rejected_count += 1
            return result

        # Check 4: Weekly loss budget
        weekly_used = abs(min(0, portfolio.weekly_pnl_pct))
        remaining_weekly = MAX_WEEKLY_LOSS_PCT - weekly_used
        result.remaining_weekly_budget_pct = max(0, remaining_weekly)

        if remaining_weekly <= 0:
            result.reasons.append(
                f"Weekly loss budget exhausted ({weekly_used:.2f}% used of {MAX_WEEKLY_LOSS_PCT}%)"
            )
            result.risk_level = RiskLevel.BREACH
            result.approved = False
            self._rejected_count += 1
            return result

        # Check 5: Mandatory stop-loss
        if request.action in (TradeAction.BUY, TradeAction.SELL):
            if request.stop_loss_pct <= 0 or request.stop_loss_pct > MANDATORY_STOP_LOSS_PCT:
                result.stop_loss_required = MANDATORY_STOP_LOSS_PCT
                result.warnings.append(
                    f"Stop-loss set to constitutional max {MANDATORY_STOP_LOSS_PCT}%"
                )
                request.stop_loss_pct = MANDATORY_STOP_LOSS_PCT

        # Check 6: Leverage
        if proposed_risk_pct > portfolio.total_equity * _MAX_LEVERAGE:
            result.warnings.append("Leverage limit check applied")

        # Determine overall risk level
        if proposed_risk_pct <= MAX_RISK_PER_TRADE_PCT * 0.5:
            result.risk_level = RiskLevel.SAFE
        elif proposed_risk_pct <= MAX_RISK_PER_TRADE_PCT:
            result.risk_level = RiskLevel.MODERATE
        elif proposed_risk_pct <= MAX_POSITION_SIZE_PCT * 0.5:
            result.risk_level = RiskLevel.ELEVATED
        elif proposed_risk_pct <= MAX_POSITION_SIZE_PCT:
            result.risk_level = RiskLevel.HIGH
        else:
            result.risk_level = RiskLevel.EXTREME

        # Approve if all checks passed
        result.approved = True
        self._approved_count += 1
        return result

    def evaluate(
        self,
        symbol: str = "",
        direction: str = "",
        lot_size: float = 0.0,
        entry: float = 0.0,
        stop_loss: float = 0.0,
        account_balance: float = 1_000_000.0,
        take_profit: Optional[float] = None,
        daily_pnl: float = 0.0,
        weekly_pnl: float = 0.0,
        trade_count_today: int = 0,
        active_positions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Flat-parameter evaluate (backward compat for RiskManager)."""
        active_positions = active_positions or []
        req = TradeRequest(
            symbol=symbol,
            action=TradeAction.BUY if direction.upper() in ("BUY", "LONG") else TradeAction.SELL,
            quantity=lot_size,
            price=entry,
            stop_loss_pct=stop_loss,
        )
        pf = PortfolioSnapshot(
            total_equity=account_balance,
            daily_pnl_pct=daily_pnl,
            weekly_pnl_pct=weekly_pnl,
        )
        result = self.check_trade(req, pf)
        failed = [w for w in result.warnings + result.reasons if w] if not result.approved else []
        return {
            "verdict": "APPROVED" if result.approved else "VETOED",
            "approved": result.approved,
            "risk_level": result.risk_level.value if result.risk_level else "unknown",
            "failed_checkpoints": failed if not result.approved else [],
            "warnings": result.warnings,
            "reasons": result.reasons,
            "proposed_risk_pct": result.proposed_risk_pct,
            "position_size_adjusted": result.position_size_adjusted,
            "remaining_daily_budget_pct": result.remaining_daily_budget_pct,
            "remaining_weekly_budget_pct": result.remaining_weekly_budget_pct,
        }

    def calculate_position_size(
        self,
        equity: float,
        entry_price: float,
        stop_loss_price: float,
        risk_pct: float = MAX_RISK_PER_TRADE_PCT,
    ) -> float:
        """Calculate position size based on risk budget.

        Parameters
        ----------
        equity:
            Total portfolio equity.
        entry_price:
            Entry price per unit.
        stop_loss_price:
            Stop-loss price per unit.
        risk_pct:
            Risk as percentage of equity.

        Returns
        -------
        float
            Position size in units.
        """
        if entry_price <= 0 or equity <= 0:
            return 0.0

        risk_amount = equity * (risk_pct / 100)
        risk_per_unit = abs(entry_price - stop_loss_price)

        if risk_per_unit <= 0:
            return 0.0

        position_size = risk_amount / risk_per_unit

        # Cap at max position size
        max_position_value = equity * (MAX_POSITION_SIZE_PCT / 100)
        max_position_size = max_position_value / entry_price

        return min(position_size, max_position_size)

    @property
    def stats(self) -> Dict[str, Any]:
        """Risk guard statistics."""
        return {
            "total_checks": self._check_count,
            "approved": self._approved_count,
            "rejected": self._rejected_count,
            "adjusted": self._adjustment_count,
            "approval_rate": self._approved_count / max(1, self._check_count),
            "constitutional_limits": {
                "max_risk_per_trade_pct": MAX_RISK_PER_TRADE_PCT,
                "max_daily_loss_pct": MAX_DAILY_LOSS_PCT,
                "max_weekly_loss_pct": MAX_WEEKLY_LOSS_PCT,
                "max_position_size_pct": MAX_POSITION_SIZE_PCT,
                "mandatory_stop_loss_pct": MANDATORY_STOP_LOSS_PCT,
            },
        }


# Backward-compat alias
RiskCheckGate = ConstitutionalRiskGuard
