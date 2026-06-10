"""Risk Manager with Constitutional Limits.

Implements the top-level risk manager that enforces CONSTITUTIONAL limits
that CANNOT be overridden by any agent. These limits are hardcoded constants
that provide the ultimate safety net for the trading system.

CONSTITUTIONAL LIMITS (HARDCODED — NO OVERRIDE POSSIBLE):
- Max 0.5% risk per trade
- Max 1% daily loss
- Max 3% weekly loss
- Max 10% maximum drawdown

Extracted from HermesQuantOS's Risk Officer with enhancements from ai-hedge-fund.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.risk.constants import (
    MAX_RISK_PER_TRADE,
    MAX_DAILY_LOSS,
    MAX_WEEKLY_LOSS,
    MAX_DRAWDOWN_PCT as MAX_DRAWDOWN,
    MIN_RISK_REWARD,
    MAX_CORRELATED_POSITIONS,
    MAX_DAILY_TRADES,
)
from quant_nanggroe.engine.risk.checks import RiskCheckGate
from quant_nanggroe.engine.risk.kill_switch import KillSwitch
from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
from quant_nanggroe.engine.risk.kelly import KellyCriterion
from quant_nanggroe.engine.risk.var import VaRCalculator

logger = logging.getLogger(__name__)

# Re-export constants for backward compatibility
__all__ = [
    "MAX_RISK_PER_TRADE", "MAX_DAILY_LOSS", "MAX_WEEKLY_LOSS",
    "MAX_DRAWDOWN", "MIN_RISK_REWARD", "MAX_CORRELATED_POSITIONS",
    "MAX_DAILY_TRADES", "RiskManager",
]


@dataclass
class RiskState:
    """Current risk state tracking.

    Tracks daily/weekly P&L, trade counts, and drawdown
    for constitutional limit enforcement.
    """

    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    trade_count_today: int = 0
    trade_count_week: int = 0
    active_positions: List[str] = field(default_factory=list)
    peak_equity: float = 0.0
    current_equity: float = 0.0
    last_reset_date: Optional[date] = None


class RiskManager:
    """Risk Manager with CONSTITUTIONAL limits.

    Enforces hardcoded risk limits that cannot be overridden.
    All trade proposals must pass through the 9-checkpoint gate
    before execution. If any constitutional limit is breached,
    the kill switch is automatically activated.

    Usage:
        rm = RiskManager()
        result = rm.check_trade(symbol="AAPL", direction="BUY", ...)
        if result["verdict"] == "APPROVED":
            # Execute trade
            size = rm.calculate_position_size(...)
    """

    def __init__(self, initial_equity: float = 1_000_000.0) -> None:
        self.state = RiskState(
            peak_equity=initial_equity,
            current_equity=initial_equity,
            last_reset_date=datetime.now().date(),
        )
        self.check_gate = RiskCheckGate()
        self.kill_switch = KillSwitch()
        self.drawdown_monitor = DrawdownMonitor(max_drawdown=MAX_DRAWDOWN)
        self.kelly = KellyCriterion()
        self.var_calculator = VaRCalculator()
        self._veto_count: int = 0
        self._approval_count: int = 0

    def check_trade(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        entry: float,
        stop_loss: float,
        account_balance: float = 1_000_000.0,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """9-checkpoint risk validation.

        Returns APPROVED or VETOED with detailed checkpoint results.
        No agent can override a VETO.

        Args:
            symbol: Trading symbol.
            direction: BUY/SELL/LONG/SHORT.
            lot_size: Proposed lot size.
            entry: Entry price.
            stop_loss: Stop loss price.
            account_balance: Current account balance.
            take_profit: Optional take profit price.

        Returns:
            Dict with verdict, checkpoints, and risk metrics.
        """
        self._reset_daily_if_needed()

        # First check kill switch
        if self.kill_switch.is_active:
            return {
                "symbol": symbol,
                "direction": direction.upper(),
                "verdict": "VETOED",
                "reason": "KILL_SWITCH_ACTIVE",
                "message": "All trading halted. Manual reset required after review.",
            }

        # Run 9-checkpoint gate
        result = self.check_gate.evaluate(
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry=entry,
            stop_loss=stop_loss,
            account_balance=account_balance,
            take_profit=take_profit,
            daily_pnl=self.state.daily_pnl,
            weekly_pnl=self.state.weekly_pnl,
            trade_count_today=self.state.trade_count_today,
            active_positions=self.state.active_positions,
        )

        verdict = result["verdict"]

        if verdict == "VETOED":
            self._veto_count += 1
            logger.warning("TRADE VETOED: %s %s — %s", symbol, direction, result.get("failed_checkpoints", []))
        else:
            self._approval_count += 1

        return {
            **result,
            "veto_count_total": self._veto_count,
            "approval_count_total": self._approval_count,
            "timestamp": datetime.now().isoformat(),
        }

    def update_pnl(self, trade_pnl: float, symbol: Optional[str] = None) -> None:
        """Update daily and weekly P&L tracking.

        Args:
            trade_pnl: P&L from the completed trade.
            symbol: Symbol of the trade (for position tracking).
        """
        self._reset_daily_if_needed()
        self.state.daily_pnl += trade_pnl
        self.state.weekly_pnl += trade_pnl
        self.state.trade_count_today += 1
        self.state.trade_count_week += 1

        # Update equity
        self.state.current_equity += trade_pnl
        self.state.peak_equity = max(self.state.peak_equity, self.state.current_equity)

        # Update drawdown monitor
        self.drawdown_monitor.update(self.state.current_equity)

        # Auto-check kill switch
        self._auto_check_kill_switch()

    def add_position(self, symbol: str) -> None:
        """Track a new open position."""
        if symbol not in self.state.active_positions:
            self.state.active_positions.append(symbol)

    def remove_position(self, symbol: str) -> None:
        """Remove a closed position."""
        if symbol in self.state.active_positions:
            self.state.active_positions.remove(symbol)

    def calculate_position_size(
        self,
        account_balance: float,
        risk_pct: float,
        stop_loss_pips: float,
        pip_value: float = 10.0,
    ) -> Dict[str, Any]:
        """Calculate proper position size based on risk parameters.

        Risk_pct is CAPPED at MAX_RISK_PER_TRADE regardless of input.

        Args:
            account_balance: Current account balance.
            risk_pct: Requested risk percentage.
            stop_loss_pips: Stop loss distance in pips.
            pip_value: Value per pip.

        Returns:
            Dict with position size and risk details.
        """
        # HARDCODED: Cap risk at maximum
        effective_risk = min(risk_pct, MAX_RISK_PER_TRADE)
        capped = risk_pct > MAX_RISK_PER_TRADE

        risk_amount = account_balance * effective_risk
        lot_size = risk_amount / (stop_loss_pips * pip_value) if stop_loss_pips > 0 else 0
        lot_size = max(0.01, round(lot_size * 100) / 100)

        return {
            "account_balance": account_balance,
            "requested_risk_pct": risk_pct,
            "effective_risk_pct": effective_risk,
            "capped": capped,
            "max_risk_hardcoded": MAX_RISK_PER_TRADE,
            "risk_amount": round(risk_amount, 2),
            "stop_loss_pips": stop_loss_pips,
            "lot_size": lot_size,
            "note": "Risk percentage capped at hardcoded maximum. No override possible.",
        }

    def calculate_kelly_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        account_balance: float,
        method: str = "HALF_KELLY",
    ) -> Dict[str, Any]:
        """Calculate position size using Kelly Criterion.

        Args:
            win_rate: Historical win rate (0-1).
            avg_win: Average winning trade amount.
            avg_loss: Average losing trade amount.
            account_balance: Current account balance.
            method: Kelly method (FULL_KELLY, HALF_KELLY, QUARTER_KELLY).

        Returns:
            Dict with Kelly calculation results.
        """
        from quant_nanggroe.engine.risk.kelly import KellyMethod, KellyParameters

        kelly_method = KellyMethod(method.upper())
        params = KellyParameters(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        result = self.kelly.calculate_kelly(params, kelly_method)

        # Enforce constitutional limit on position size
        max_fraction = MAX_RISK_PER_TRADE
        adjusted_fraction = result.adjusted_fraction
        recommendation = result.recommendation
        if adjusted_fraction > max_fraction:
            adjusted_fraction = max_fraction
            recommendation = f"CONSTITUTIONAL LIMIT: Position capped at {max_fraction:.1%}"

        position_size = account_balance * adjusted_fraction

        return {
            "optimal_fraction": result.optimal_fraction,
            "adjusted_fraction": adjusted_fraction,
            "position_size": round(position_size, 2),
            "expected_growth": result.expected_growth,
            "risk_of_ruin": result.risk_of_ruin,
            "recommendation": recommendation,
            "method": method,
        }

    def status(self) -> Dict[str, Any]:
        """Get current risk status."""
        self._reset_daily_if_needed()

        daily_loss_pct = abs(min(0, self.state.daily_pnl)) / self.state.peak_equity if self.state.peak_equity > 0 else 0
        weekly_loss_pct = abs(min(0, self.state.weekly_pnl)) / self.state.peak_equity if self.state.peak_equity > 0 else 0

        daily_status = "OK" if daily_loss_pct < MAX_DAILY_LOSS else "LIMIT_REACHED"
        weekly_status = "OK" if weekly_loss_pct < MAX_WEEKLY_LOSS else "LIMIT_REACHED"

        dd_info = self.drawdown_monitor.get_status()

        overall = "TRADING_ALLOWED"
        if daily_status == "LIMIT_REACHED" or weekly_status == "LIMIT_REACHED" or self.kill_switch.is_active or dd_info.get("drawdown_breached", False):
            overall = "TRADING_HALT"

        return {
            "overall_status": overall,
            "daily_pnl": self.state.daily_pnl,
            "weekly_pnl": self.state.weekly_pnl,
            "daily_loss_pct": f"{daily_loss_pct:.4f}",
            "weekly_loss_pct": f"{weekly_loss_pct:.4f}",
            "daily_limit": f"{MAX_DAILY_LOSS:.4f}",
            "weekly_limit": f"{MAX_WEEKLY_LOSS:.4f}",
            "daily_status": daily_status,
            "weekly_status": weekly_status,
            "trades_today": self.state.trade_count_today,
            "trades_week": self.state.trade_count_week,
            "active_positions": len(self.state.active_positions),
            "veto_count": self._veto_count,
            "approval_count": self._approval_count,
            "drawdown": dd_info,
            "kill_switch": self.kill_switch.status(),
            "hardcoded_limits": {
                "max_risk_per_trade": f"{MAX_RISK_PER_TRADE:.2%}",
                "max_daily_loss": f"{MAX_DAILY_LOSS:.2%}",
                "max_weekly_loss": f"{MAX_WEEKLY_LOSS:.2%}",
                "max_drawdown": f"{MAX_DRAWDOWN:.0%}",
                "min_rr_ratio": f"1:{MIN_RISK_REWARD}",
                "override_possible": False,
            },
        }

    def _reset_daily_if_needed(self) -> None:
        """Reset daily counters if new day."""
        today = datetime.now().date()
        if self.state.last_reset_date is None or today > self.state.last_reset_date:
            self.state.daily_pnl = 0.0
            self.state.trade_count_today = 0
            # Reset weekly on Monday
            if today.weekday() == 0:  # Monday
                self.state.weekly_pnl = 0.0
                self.state.trade_count_week = 0
            self.state.last_reset_date = today

    def _auto_check_kill_switch(self) -> None:
        """Auto-check if kill switch should activate based on risk limits."""
        daily_loss_pct = abs(min(0, self.state.daily_pnl)) / self.state.peak_equity if self.state.peak_equity > 0 else 0
        weekly_loss_pct = abs(min(0, self.state.weekly_pnl)) / self.state.peak_equity if self.state.peak_equity > 0 else 0

        if daily_loss_pct >= MAX_DAILY_LOSS:
            self.kill_switch.activate("AUTO_DAILY_LIMIT")
            logger.critical("KILL SWITCH: Daily loss limit breached (%.2f%% >= %.2f%%)", daily_loss_pct * 100, MAX_DAILY_LOSS * 100)

        if weekly_loss_pct >= MAX_WEEKLY_LOSS:
            self.kill_switch.activate("AUTO_WEEKLY_LIMIT")
            logger.critical("KILL SWITCH: Weekly loss limit breached (%.2f%% >= %.2f%%)", weekly_loss_pct * 100, MAX_WEEKLY_LOSS * 100)

        if self.drawdown_monitor.is_breached:
            self.kill_switch.activate("AUTO_MAX_DRAWDOWN")
            logger.critical("KILL SWITCH: Maximum drawdown breached (%.2f%% >= %.2f%%)", self.drawdown_monitor.current_drawdown * 100, MAX_DRAWDOWN * 100)
