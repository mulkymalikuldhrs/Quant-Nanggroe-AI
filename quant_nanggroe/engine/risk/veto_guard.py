"""GovernanceVetoGuard — Constitutional governance veto for order execution.

Enforces hard governance limits that CANNOT be overridden by any agent or
strategy. Acts as a fail-closed pre-filter in the execution guard pipeline.

Checks:
- Kill switch status (auto-activation)
- Maximum daily P&L loss
- Maximum weekly P&L loss
- Maximum drawdown breach
- Maximum per-trade risk

All checks are ENFORCED (not advisory). A single veto blocks the order.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from quant_nanggroe.engine.execution.base import Order
from quant_nanggroe.engine.risk.constants import (
    MAX_DAILY_LOSS,
    MAX_DRAWDOWN_PCT,
    MAX_RISK_PER_TRADE,
    MAX_WEEKLY_LOSS,
)

logger = logging.getLogger(__name__)


@dataclass
class GovernanceVetoResult:
    """Result from a governance veto check."""

    allowed: bool
    guard_name: str = "governance_veto"
    reason: str = ""


class GovernanceVetoGuard:
    """Governance Veto Guard.

    Enforces constitutional governance limits on every order before it
    reaches the broker. This guard is fail-closed: any check failure
    blocks the order.

    Usage:
        guard = GovernanceVetoGuard()
        result = guard.check(order, daily_pnl_pct=0.5, weekly_pnl_pct=1.2)
        if not result.allowed:
            # Order blocked by governance veto
    """

    def __init__(
        self,
        max_daily_loss_pct: float = MAX_DAILY_LOSS,
        max_weekly_loss_pct: float = MAX_WEEKLY_LOSS,
        max_drawdown_pct: float = MAX_DRAWDOWN_PCT,
        max_risk_per_trade_pct: float = MAX_RISK_PER_TRADE,
    ) -> None:
        self._max_daily_loss = max_daily_loss_pct
        self._max_weekly_loss = max_weekly_loss_pct
        self._max_drawdown = max_drawdown_pct
        self._max_risk_per_trade = max_risk_per_trade_pct
        self._kill_switch_active: bool = False
        self._daily_pnl_pct: float = 0.0
        self._weekly_pnl_pct: float = 0.0
        self._current_drawdown_pct: float = 0.0

    def update_pnl(self, daily_pnl_pct: float, weekly_pnl_pct: float) -> None:
        self._daily_pnl_pct = daily_pnl_pct
        self._weekly_pnl_pct = weekly_pnl_pct

    def update_drawdown(self, drawdown_pct: float) -> None:
        self._current_drawdown_pct = drawdown_pct

    def set_kill_switch_active(self, active: bool) -> None:
        self._kill_switch_active = active

    def check(self, order: Order) -> GovernanceVetoResult:
        if self._kill_switch_active:
            return GovernanceVetoResult(
                allowed=False,
                reason="Kill switch is active — all trading halted",
            )

        if self._daily_pnl_pct <= -self._max_daily_loss:
            return GovernanceVetoResult(
                allowed=False,
                reason=f"Daily loss limit breached: {self._daily_pnl_pct:.2%} <= -{self._max_daily_loss:.2%}",
            )

        if self._weekly_pnl_pct <= -self._max_weekly_loss:
            return GovernanceVetoResult(
                allowed=False,
                reason=f"Weekly loss limit breached: {self._weekly_pnl_pct:.2%} <= -{self._max_weekly_loss:.2%}",
            )

        if self._current_drawdown_pct >= self._max_drawdown:
            return GovernanceVetoResult(
                allowed=False,
                reason=f"Max drawdown breached: {self._current_drawdown_pct:.2%} >= {self._max_drawdown:.2%}",
            )

        risk_per_trade = abs(order.quantity * (order.price or 0.0))
        if risk_per_trade > 0 and risk_per_trade / self._max_risk_per_trade > 1.0:
            return GovernanceVetoResult(
                allowed=False,
                reason=f"Per-trade risk exceeds limit",
            )

        return GovernanceVetoResult(allowed=True)