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
from quant_nanggroe.engine.risk.trailing_stop import TrailingStopManager
from quant_nanggroe.engine.persistence import (
    PersistenceBackend,
    get_persistence_backend,
)
from quant_nanggroe.engine.observability import get_observability, traced

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

    def __init__(
        self,
        initial_equity: float = 1_000_000.0,
        persistence: Optional[PersistenceBackend] = None,
    ) -> None:
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
        self.trailing_stop = TrailingStopManager()
        self._veto_count: int = 0
        self._approval_count: int = 0

        # Persistence layer — optional, defaults to env-configured backend
        self._persistence = persistence or get_persistence_backend()
        self._load_state()

    @traced("check_trade", attributes={"component": "risk", "operation": "check_trade"})
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
        import time as _time
        obs = get_observability()
        start = _time.monotonic()

        self._reset_daily_if_needed()

        # First check kill switch
        if self.kill_switch.is_active:
            obs.metrics.risk_check_duration_seconds.record(
                _time.monotonic() - start,
                {"check_name": "kill_switch", "verdict": "VETOED"},
            )
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

        # Record observability metrics
        obs.metrics.risk_check_duration_seconds.record(
            _time.monotonic() - start,
            {"check_name": "full_gate", "verdict": verdict},
        )
        obs.metrics.trades_total.add(
            1,
            {"symbol": symbol, "direction": direction.upper(), "verdict": verdict},
        )

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

        # Persist state after update (including kill switch changes)
        self._save_state()

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
        if result.adjusted_fraction > max_fraction:
            result = result._replace(
                adjusted_fraction=max_fraction,
                recommendation=f"CONSTITUTIONAL LIMIT: Position capped at {max_fraction:.1%}",
            )

        position_size = account_balance * result.adjusted_fraction

        return {
            "optimal_fraction": result.optimal_fraction,
            "adjusted_fraction": result.adjusted_fraction,
            "position_size": round(position_size, 2),
            "expected_growth": result.expected_growth,
            "risk_of_ruin": result.risk_of_ruin,
            "recommendation": result.recommendation,
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
            self._save_state()

    # ── Persistence ─────────────────────────────────────────────────────

    def _save_state(self) -> None:
        """Persist risk state to the configured backend."""
        try:
            self._persistence.set_many({
                "risk:daily_pnl": self.state.daily_pnl,
                "risk:weekly_pnl": self.state.weekly_pnl,
                "risk:trade_count_today": self.state.trade_count_today,
                "risk:trade_count_week": self.state.trade_count_week,
                "risk:peak_equity": self.state.peak_equity,
                "risk:current_equity": self.state.current_equity,
                "risk:last_reset_date": (
                    self.state.last_reset_date.isoformat()
                    if self.state.last_reset_date else None
                ),
                "risk:active_positions": self.state.active_positions,
                "risk:veto_count": self._veto_count,
                "risk:approval_count": self._approval_count,
                "risk:kill_switch_active": self.kill_switch.is_active,
                "risk:kill_switch_reason": self.kill_switch.status().get("activation_reason"),
                "risk:kill_switch_activated_at": self.kill_switch.status().get("activated_at"),
            }, ttl=86400 * 7)  # 7-day TTL
        except Exception as e:
            logger.warning("Failed to persist risk state: %s", e)

    def _load_state(self) -> None:
        """Load risk state from the configured backend."""
        try:
            daily_pnl = self._persistence.get("risk:daily_pnl")
            if daily_pnl is not None:
                self.state.daily_pnl = float(daily_pnl)

            weekly_pnl = self._persistence.get("risk:weekly_pnl")
            if weekly_pnl is not None:
                self.state.weekly_pnl = float(weekly_pnl)

            trade_count_today = self._persistence.get("risk:trade_count_today")
            if trade_count_today is not None:
                self.state.trade_count_today = int(trade_count_today)

            trade_count_week = self._persistence.get("risk:trade_count_week")
            if trade_count_week is not None:
                self.state.trade_count_week = int(trade_count_week)

            peak_equity = self._persistence.get("risk:peak_equity")
            if peak_equity is not None:
                self.state.peak_equity = float(peak_equity)

            current_equity = self._persistence.get("risk:current_equity")
            if current_equity is not None:
                self.state.current_equity = float(current_equity)

            last_reset_date = self._persistence.get("risk:last_reset_date")
            if last_reset_date is not None and last_reset_date:
                self.state.last_reset_date = date.fromisoformat(last_reset_date)

            active_positions = self._persistence.get("risk:active_positions")
            if active_positions is not None:
                self.state.active_positions = list(active_positions)

            veto_count = self._persistence.get("risk:veto_count")
            if veto_count is not None:
                self._veto_count = int(veto_count)

            approval_count = self._persistence.get("risk:approval_count")
            if approval_count is not None:
                self._approval_count = int(approval_count)

            # Restore kill switch state
            kill_switch_active = self._persistence.get("risk:kill_switch_active")
            if kill_switch_active:
                reason = self._persistence.get("risk:kill_switch_reason") or "PERSISTED_STATE"
                self.kill_switch.activate(reason)

            # Reset daily counters if the persisted state is from a previous day
            self._reset_daily_if_needed()

            logger.info(
                "Risk state loaded from persistence: daily_pnl=%.2f, weekly_pnl=%.2f, trades_today=%d",
                self.state.daily_pnl, self.state.weekly_pnl, self.state.trade_count_today,
            )
        except Exception as e:
            logger.warning("Failed to load risk state from persistence: %s", e)

    # ── Stress Testing (from ai-hedge-fund) ────────────────────────────

    def stress_test(
        self,
        returns: pd.Series,
        scenarios: Optional[Dict[str, tuple]] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Run stress tests on portfolio.

        Applies historical-like scenarios to the current return distribution
        to estimate VaR and CVaR under stressed conditions.

        Args:
            returns: Historical returns series.
            scenarios: Dict of {scenario_name: (return_change, vol_change)}.
                return_change is a multiplier on annualized return.
                vol_change is a multiplier on annualized volatility.

        Returns:
            Dict of scenario results with stressed VaR, CVaR, and Sharpe.
        """
        if scenarios is None:
            scenarios = {
                "2008_Crisis": (-0.40, 2.0),
                "COVID_Crash": (-0.30, 1.5),
                "Rate_Hike": (-0.15, 1.2),
                "Tech_Crash": (-0.25, 1.5),
                "Recovery": (0.20, 0.8),
                "Bull_Market": (0.30, 0.9),
            }

        results: Dict[str, Dict[str, float]] = {}
        base_return = returns.mean() * 252
        base_vol = returns.std() * np.sqrt(252)
        risk_free_rate = 0.02

        for scenario, (ret_change, vol_change) in scenarios.items():
            stressed_return = base_return * ret_change
            stressed_vol = base_vol * vol_change

            # Parametric VaR and CVaR under stressed conditions
            from scipy import stats as sp_stats

            var_95 = stressed_return - 1.645 * stressed_vol
            cvar_95 = stressed_return - stressed_vol * sp_stats.norm.pdf(1.645) / 0.05

            results[scenario] = {
                "expected_return": stressed_return,
                "volatility": stressed_vol,
                "var_95": var_95,
                "cvar_95": cvar_95,
                "sharpe_ratio": (
                    (stressed_return - risk_free_rate) / stressed_vol
                    if stressed_vol > 0
                    else 0.0
                ),
            }

        return results

    # ── Advanced Position Sizing (from ai-hedge-fund) ────────────────

    def optimal_f_position_size(
        self,
        returns: pd.Series,
        target_volatility: float = 0.10,
        lookback: int = 252,
    ) -> float:
        """Calculate position size to target volatility.

        Uses volatility targeting approach: scales position up or down
        so that the resulting portfolio has the desired volatility level.

        Args:
            returns: Historical returns series.
            target_volatility: Target annual volatility.
            lookback: Lookback period in days.

        Returns:
            Position size as fraction of portfolio (0.1 to 3.0).
        """
        recent_returns = returns.tail(lookback)
        current_vol = recent_returns.std() * np.sqrt(252)

        if current_vol == 0:
            return 1.0

        # Scale position to target volatility
        position_size = target_volatility / current_vol

        # Bound position
        position_size = max(0.1, min(position_size, 3.0))

        return position_size

    def atr_position_size(
        self,
        entry_price: float,
        atr: float,
        account_balance: float,
        risk_per_trade: float = 0.02,
        max_risk_per_trade: float = 0.05,
    ) -> Dict[str, Any]:
        """Calculate position size using ATR (Average True Range).

        Uses a 2-ATR stop distance and scales the position so that
        the dollar risk equals the specified risk_per_trade fraction.

        Args:
            entry_price: Entry price.
            atr: Average True Range value.
            account_balance: Account balance.
            risk_per_trade: Fraction of account to risk per trade.
            max_risk_per_trade: Maximum risk per trade.

        Returns:
            Dict with position_size, stop_loss, and risk_amount.
        """
        # Calculate risk amount (capped at constitutional limit)
        effective_risk = min(risk_per_trade, max_risk_per_trade, MAX_RISK_PER_TRADE)
        risk_amount = account_balance * effective_risk

        # Calculate stop loss distance (2 ATR)
        stop_distance = 2 * atr

        if stop_distance <= 0:
            return {"position_size": 0, "stop_loss": 0, "risk_amount": 0}

        position_size = risk_amount / stop_distance
        stop_loss = entry_price - stop_distance

        return {
            "position_size": position_size,
            "stop_loss": stop_loss,
            "risk_amount": risk_amount,
            "effective_risk_pct": effective_risk,
        }

    def calculate_position_size_with_var(
        self,
        returns: np.ndarray,
        portfolio_value: float,
        max_var_pct: float = 0.02,
        confidence: float = 0.95,
    ) -> float:
        """Calculate position size based on VaR limit.

        Scales the position so that the VaR at the given confidence level
        does not exceed max_var_pct of the portfolio value.

        Args:
            returns: Historical returns array.
            portfolio_value: Current portfolio value.
            max_var_pct: Maximum VaR as percentage of portfolio.
            confidence: VaR confidence level.

        Returns:
            Position size as fraction of portfolio (0.0 to 1.0).
        """
        var_result = self.var_calculator.calculate(
            returns, confidence_level=confidence, portfolio_value=portfolio_value
        )

        if var_result.var_value <= 0:
            return 1.0

        var_pct = var_result.var_value / portfolio_value
        position_size = min(1.0, max_var_pct / var_pct)

        return position_size

    def check_trailing_stops(self, positions: dict) -> list:
        """Check trailing stops for all open positions.

        Args:
            positions: Dict of {symbol: current_price}.

        Returns:
            List of symbols that triggered trailing stop and should be closed.
        """
        triggered = []
        for symbol, current_price in positions.items():
            self.trailing_stop.add_position(symbol, current_price)
            result = self.trailing_stop.update(symbol, current_price)
            if result is not None:
                triggered.append(result)
        return triggered

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
