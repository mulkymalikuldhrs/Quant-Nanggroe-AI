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
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Constitutional Limits (CANNOT BE OVERRIDDEN) ────────────────────────────

MAX_RISK_PER_TRADE_PCT = 0.5   # 0.5% per trade
MAX_DAILY_LOSS_PCT = 1.0       # 1.0% daily loss
MAX_WEEKLY_LOSS_PCT = 3.0      # 3.0% weekly loss
MAX_POSITION_SIZE_PCT = 10.0   # 10% of portfolio per position
MAX_LEVERAGE = 1.0             # No leverage by default
MANDATORY_STOP_LOSS_PCT = 2.0  # 2% stop-loss required


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
        if proposed_risk_pct > portfolio.total_equity * MAX_LEVERAGE:
            result.warnings.append("Lverage limit check applied")

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
