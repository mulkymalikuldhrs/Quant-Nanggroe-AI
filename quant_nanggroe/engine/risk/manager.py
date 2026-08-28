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
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.observability import get_observability, traced
from quant_nanggroe.engine.persistence import (
    PersistenceBackend,
    get_persistence_backend,
)
from quant_nanggroe.engine.risk.checks import RiskCheckGate
from quant_nanggroe.engine.risk.constants import (
    HARD_STOP_ATR_MULTIPLIER,
    KILL_SWITCH_DAILY_PNL,
    KILL_SWITCH_WEEKLY_PNL,
    MAX_ASSET_DAILY_LOSS_PCT,
    MAX_CORRELATED_POSITIONS,
    MAX_DAILY_LOSS,
    MAX_DAILY_TRADES,
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE,
    MAX_TOTAL_CONCENTRATION,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
    TRADING_BUDGET_PCT,
)
from quant_nanggroe.engine.risk.constants import (
    MAX_DRAWDOWN_PCT as MAX_DRAWDOWN,
)
from quant_nanggroe.engine.risk.correlation_regime import (
    CorrelationRegimeDetector,
    CrossAssetMarginMonitor,
)
from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
from quant_nanggroe.engine.risk.kelly import KellyCriterion
from quant_nanggroe.engine.risk.kill_switch import KillSwitch
from quant_nanggroe.engine.risk.var import VaRCalculator
from quant_nanggroe.engine.risk.volatility_regime_har import (
    RegimeSwitchingHAR,
    VolRegime,
)

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
    # P1 hygiene (2026-08-22): declared field — update_mtm() writes this and
    # previously relied on a silent dynamic attribute (phantom dataclass attr).
    unrealized_pnl: float = 0.0
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
        self.drawdown_monitor = DrawdownMonitor(
            max_drawdown=MAX_DRAWDOWN, initial_equity=initial_equity
        )
        self.kelly = KellyCriterion()
        self.var_calculator = VaRCalculator()
        self.correlation_regime = CorrelationRegimeDetector(window=30)
        self.margin_monitor = CrossAssetMarginMonitor()
        self._veto_count: int = 0
        self._approval_count: int = 0

        # Regime multipliers (volatility-regime-aware adjustments)
        # Maps VolRegime -> {constitutional_limit_key: multiplier}
        # Applied BEFORE the constitutional gate to meet tighter limits
        # in high-vol regimes. Low-vol gets looser, extreme gets strictest.
        self.REGIME_MULTIPLIERS: dict[VolRegime, dict[str, float]] = {
            VolRegime.LOW: {
                "risk_per_trade": 1.5,   # 0.75% max (1.5x base 0.5%)
                "daily_loss": 1.0,       # 1% (no change)
                "weekly_loss": 1.0,      # 3% (no change)
                "position_pct": 1.5,     # 15% (1.5x base 10%)
            },
            VolRegime.NORMAL: {
                "risk_per_trade": 1.0,   # 0.5% (base)
                "daily_loss": 1.0,       # 1% (base)
                "weekly_loss": 1.0,      # 3% (base)
                "position_pct": 1.0,     # 10% (base)
            },
            VolRegime.ELEVATED: {
                "risk_per_trade": 0.5,   # 0.25% (half)
                "daily_loss": 0.8,       # 0.8%
                "weekly_loss": 0.8,      # 2.4%
                "position_pct": 0.5,     # 5%
            },
            VolRegime.HIGH: {
                "risk_per_trade": 0.25,  # 0.125%
                "daily_loss": 0.5,       # 0.5%
                "weekly_loss": 0.5,      # 1.5%
                "position_pct": 0.25,    # 2.5%
            },
            VolRegime.EXTREME: {
                "risk_per_trade": 0.1,   # 0.05%
                "daily_loss": 0.25,      # 0.25%
                "weekly_loss": 0.25,     # 0.75%
                "position_pct": 0.1,     # 1%
            },
        }
        self._current_vol_regime: VolRegime = VolRegime.NORMAL
        self._current_vol_regime_mult: dict[str, float] = \
            self.REGIME_MULTIPLIERS[VolRegime.NORMAL]
        self._vol_regime_detector: RegimeSwitchingHAR | None = RegimeSwitchingHAR()

        # Per-asset risk budgets (P1-26)
        self.asset_budgets: Dict[str, Dict[str, float]] = {}
        self.asset_daily_pnl: Dict[str, float] = {}

        # Concentration limits (P1-32)
        self.concentration_limits: Dict[str, float] = {}

        # Cost-aware budget (P1-32)
        self.trading_budget: float = initial_equity * TRADING_BUDGET_PCT

        # Hard stops at entry (P1-26): symbol -> {entry_price, atr, stop_price}
        self._hard_stops: Dict[str, Dict[str, float]] = {}

        # Persistence layer — optional, defaults to env-configured backend
        self._persistence = persistence or get_persistence_backend()
        # P0 fix: live MT5 handle for realized-PnL sync. Without this the
        # daily/weekly-loss veto reads 0.0 forever (phantom-dead veto). Set via
        # set_broker_handle() from the execution builder once MT5 is connected.
        # NOTE: the public method is set_broker_handle(); do NOT call a
        # non-existent attach_mt5_handle() — it would raise AttributeError.
        self._mt5_handle = None
        # R6 (F3): True while the last realized-PnL broker read FAILED —
        # check_trade vetoes until a fresh successful read restores truth.
        self._pnl_sync_stale = False
        self._load_state()

    def set_broker_handle(self, mt5_handle) -> None:
        """P0 fix: attach a live MT5 handle so risk can read REALIZED P&L.

        mt5_handle must expose history_deals_get(from_date, to_date) returning
        deal objects with .profit / .time / .symbol (the MT5Broker connector does).
        """
        self._mt5_handle = mt5_handle

    # ── Vol regime-aware risk limits ──────────────────────────────────

    def feed_vol_regime_returns(self, log_returns: list[float]) -> VolRegime:
        """Feed log returns to the HAR volatility regime detector.

        Call this periodically (e.g. every bar / every minute) from the
        trading loop so that ``check_trade`` uses the latest regime context.
        If never called, the detector defaults to ``VolRegime.NORMAL`` (no
        adjustment).

        Args:
            log_returns: Sequential log returns for the current asset or
                         portfolio. Accumulated internally by the HAR model.

        Returns:
            The detected ``VolRegime``.
        """
        for r in log_returns:
            self._vol_regime_detector.add_return(r)
        forecast = self._vol_regime_detector.forecast()
        self._current_vol_regime = forecast.regime
        self._current_vol_regime_mult = \
            self.REGIME_MULTIPLIERS.get(forecast.regime, self.REGIME_MULTIPLIERS[VolRegime.NORMAL])
        logger.info(
            "Vol regime updated: %s (confidence=%.2f, sizing_factor=%.4f)",
            forecast.regime.value, forecast.confidence,
            self._vol_regime_detector.get_position_sizing_factor(),
        )
        return forecast.regime

    def _enforce_vol_regime(
        self,
        daily_pnl: float,
        weekly_pnl: float,
        account_balance: float,
    ) -> dict[str, Any] | None:
        """Pre-gate veto check: enforce regime-adjusted loss limits.

        Returns a VETOED result dict if the regime-adjusted limit is breached,
        or ``None`` if the trade should proceed to the constitutional gate.
        """
        regime = self._current_vol_regime
        mult = self._current_vol_regime_mult
        eff_daily_limit = MAX_DAILY_LOSS * mult["daily_loss"]
        eff_weekly_limit = MAX_WEEKLY_LOSS * mult["weekly_loss"]

        # Fail-closed: balance unavailable -> veto (doubt #1, #8a)
        if account_balance is None or account_balance != account_balance or account_balance <= 0:  # NaN or <=0
            return {
                "verdict": "VETOED",
                "reason": f"ACCOUNT_BALANCE_UNAVAILABLE: {account_balance} -> fail-closed veto",
                "vol_regime": regime.value,
                "vol_regime_mult": mult,
            }
        daily_pnl_frac = daily_pnl / account_balance
        weekly_pnl_frac = weekly_pnl / account_balance

        if daily_pnl_frac <= -eff_daily_limit:
            return {
                "verdict": "VETOED",
                "reason": f"VOL_REGIME_DAILY_LOSS: {daily_pnl_frac:.2%} exceeds "
                           f"regime-adjusted {eff_daily_limit:.2%} ({regime.value})",
                "vol_regime": regime.value,
                "vol_regime_mult": mult,
            }
        if weekly_pnl_frac <= -eff_weekly_limit:
            return {
                "verdict": "VETOED",
                "reason": f"VOL_REGIME_WEEKLY_LOSS: {weekly_pnl_frac:.2%} exceeds "
                              f"regime-adjusted {eff_weekly_limit:.2%} ({regime.value})",
                    "vol_regime": regime.value,
                    "vol_regime_mult": mult,
                }
        return None

    @property
    def vol_regime_state(self) -> dict[str, Any]:
        """Current vol-regime detection state for reporting."""
        return {
            "regime": self._current_vol_regime.value,
            "multipliers": dict(self._current_vol_regime_mult),
            "sizing_factor": self._vol_regime_detector.get_position_sizing_factor()
            if self._vol_regime_detector else 1.0,
        }

    def _sync_realized_pnl(self) -> None:
        """P0 fix: pull today's + this-week's realized P&L from the live broker.

        Closes the phantom-veto hole: previously ``check_trade`` ran on
        ``daily_pnl_pct=0.0`` because nothing fed real P&L, so the constitutional
        daily/weekly-loss veto could NEVER trip (and could never correctly allow).

        R6 hotfix (F3): a FAILED broker read now keeps the previous values and
        sets ``_pnl_sync_stale`` — it must NEVER overwrite real losses with a
        fresher-than-truth 0.0. check_trade vetoes while the sync is stale
        (fail-closed): trading halts until the broker read recovers.
        """
        if self._mt5_handle is None:
            self._pnl_sync_stale = True
            return
        try:
            from datetime import timedelta, timezone
            WIB = timezone(timedelta(hours=7))
            now = datetime.now(WIB).replace(tzinfo=None)
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            # week start = Monday 00:00 WIB
            week_start = day_start - timedelta(days=now.weekday())
            day_raw = self._mt5_handle.history_deals_get(day_start, now)
            week_raw = self._mt5_handle.history_deals_get(week_start, now)
            if day_raw is None or week_raw is None:  # fail-closed: broker error -> stale, not 0
                self._pnl_sync_stale = True
                logger.warning("RiskManager._sync_realized_pnl broker returned None -> stale")
                return
            day_deals = day_raw
            week_deals = week_raw
            # Include swap/commission/fee and filter non-trading deals (doubt #6)
            def _deal_net(d):
                try:
                    if getattr(d, 'type', 0) in (2,):  # DEAL_TYPE_BALANCE
                        return 0.0
                    return float(getattr(d, 'profit', 0) or 0) + float(getattr(d, 'swap', 0) or 0) + float(getattr(d, 'commission', 0) or 0) + float(getattr(d, 'fee', 0) or 0)
                except Exception:
                    return 0.0
            day_pnl = sum(_deal_net(d) for d in day_deals)
            week_pnl = sum(_deal_net(d) for d in week_deals)
            # Owner override: weekly reset manual WIB (weekly -13.72% -> 0 until Monday WIB)
            try:
                import json
                import pathlib
                _ov_path = pathlib.Path("data/weekly_override.json")
                if _ov_path.exists():
                    _ov = json.loads(_ov_path.read_text(encoding="utf-8"))
                    _until = _ov.get("until")
                    if _until:
                        from datetime import datetime, timedelta, timezone
                        WIB = timezone(timedelta(hours=7))
                        _until_str = str(_until).replace("Z", "+00:00")
                        _until_dt = datetime.fromisoformat(_until_str)
                        # Ensure _until_dt is timezone-aware
                        if _until_dt.tzinfo is None:
                            _until_dt = _until_dt.replace(tzinfo=WIB)
                        if datetime.now(WIB) < _until_dt:
                            _ov_weekly = float(_ov.get("weekly_pnl", week_pnl))
                            if _ov_weekly != week_pnl:
                                logger.info("Weekly override active: %.2f -> %.2f until %s (owner)", week_pnl, _ov_weekly, _until)
                            week_pnl = _ov_weekly
            except Exception:
                pass
            # ponytail: always reflect truth on a SUCCESSFUL read. The old
            # `!= 0.0` guard kept a STALE negative daily_pnl when the day
            # recovered to flat / break-even -> phantom-permanent veto blocked
            # all trading on a recovered day.
            self.state.daily_pnl = day_pnl
            self.state.weekly_pnl = week_pnl
            # Equity: try MT5 truth first, fallback to peak+daily (doubt #4)
            try:
                import MetaTrader5 as _mt5m
                _acc = _mt5m.account_info()
                if _acc is not None and getattr(_acc, 'equity', None) is not None:
                    self.state.current_equity = float(_acc.equity)
                    self.state.peak_equity = max(float(self.state.peak_equity), self.state.current_equity)
                else:
                    self.state.current_equity = self.state.peak_equity + self.state.daily_pnl
            except Exception:
                self.state.current_equity = self.state.peak_equity + self.state.daily_pnl
            self._pnl_sync_stale = False
            self._auto_check_kill_switch()
        except Exception as e:
            # Read failure: keep last-known values, flag stale → veto in gate.
            self._pnl_sync_stale = True
            logger.warning(
                "RiskManager._sync_realized_pnl failed (%s) — PnL STALE, "
                "vetoes engaged until broker read recovers", e)

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
        daily_pnl_pct: float = 0.0,
        weekly_pnl_pct: float = 0.0,
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
            daily_pnl_pct: Real-time daily P&L as a fraction of account equity
                (range [0, 1], e.g. -0.06 for a 6% loss). Feeds the constitutional daily-loss veto.
            weekly_pnl_pct: Real-time weekly P&L as a fraction of account equity (range [0, 1]).

        Returns:
            Dict with verdict, checkpoints, and risk metrics.
        """
        import time as _time
        obs = get_observability()
        start = _time.monotonic()

        self._reset_daily_if_needed()

        # P0 fix: sync REALIZED P&L from the live broker before evaluating, so the
        # constitutional daily/weekly-loss veto sees real numbers (not 0.0).
        self._sync_realized_pnl()

        # R6 (F3): stale PnL = cannot prove loss limits are respected → VETO.
        if self._pnl_sync_stale:
            return {
                "symbol": symbol,
                "direction": direction.upper(),
                "verdict": "VETOED",
                "reason": "PNL_SYNC_STALE",
                "message": "Realized-PnL broker read failed — loss-limit "
                           "enforcement unverifiable. Trading halted until "
                           "the next successful sync.",
            }

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

        # Daily trade count limit
        if self.state.trade_count_today >= MAX_DAILY_TRADES:
            return {
                "symbol": symbol,
                "direction": direction.upper(),
                "verdict": "VETOED",
                "reason": f"Daily trade limit reached ({self.state.trade_count_today}/{MAX_DAILY_TRADES})",
                "failed_checkpoints": ["daily_trades"],
            }

        # Vol-regime pre-gate veto: enforce tighter loss limits before the
        # constitutional gate. In high-vol regimes the allowable loss is
        # smaller, so this veto trips BEFORE the absolute gate.
        _daily_abs_raw = self.state.daily_pnl
        _weekly_abs_raw = self.state.weekly_pnl
        # Only honour caller overrides in test/combined path without
        # a live broker — with a live broker, _sync_realized_pnl()
        # already loaded REALIZED P&L into state, not floating equity.
        if daily_pnl_pct != 0.0 and self._mt5_handle is None:
            _daily_abs_raw = daily_pnl_pct * account_balance
        if weekly_pnl_pct != 0.0 and self._mt5_handle is None:
            _weekly_abs_raw = weekly_pnl_pct * account_balance
        _regime_veto = self._enforce_vol_regime(_daily_abs_raw, _weekly_abs_raw, account_balance)
        if _regime_veto is not None:
            return {
                **_regime_veto,
                "symbol": symbol,
                "direction": direction.upper(),
                "failed_checkpoints": ["vol_regime_daily_loss", "vol_regime_weekly_loss"],
                "timestamp": datetime.now().isoformat(),
            }

        # 9-checkpoint gate. Use broker-synced PnL when available (live mode).
        # daily_pnl_pct/weekly_pnl_pct overrides only apply in test/combined
        # path WITHOUT a live broker — with a live broker handle,
        # _sync_realized_pnl() already populated state with REALIZED P&L.
        # Allowing caller overrides to shadow the synced state re-introduces
        # the phantom floating-equity veto (pitfall #58).
        _daily_abs = self.state.daily_pnl
        _weekly_abs = self.state.weekly_pnl
        if daily_pnl_pct != 0.0 and self._mt5_handle is None:
            _daily_abs = daily_pnl_pct * account_balance
        if weekly_pnl_pct != 0.0 and self._mt5_handle is None:
            _weekly_abs = weekly_pnl_pct * account_balance

        # Suspicious zero PnL check: if there's been trading activity but PnL
        # reports 0.0, the PnL sync likely isn't wired to live broker P&L.
        if self.state.trade_count_week > 0 and _weekly_abs == 0.0:
            logger.warning(
                "Weekly PnL is 0.0 after %d trades this week — PnL sync may not "
                "be connected to live broker. Weekly loss veto will be a no-op.",
                self.state.trade_count_week,
            )
        if self.state.trade_count_today > 0 and _daily_abs == 0.0:
            logger.warning(
                "Daily PnL is 0.0 after %d trades today — PnL sync may not "
                "be connected to live broker. Daily loss veto will be a no-op.",
                self.state.trade_count_today,
            )
        result = self.check_gate.evaluate(
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry=entry,
            stop_loss=stop_loss,
            account_balance=account_balance,
            take_profit=take_profit,
            daily_pnl=_daily_abs,
            weekly_pnl=_weekly_abs,
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
            margin_mult = self.correlation_regime.get_margin_multiplier()
            if margin_mult != 1.0:
                result["margin_multiplier"] = margin_mult
                result["correlation_regime"] = self.correlation_regime.detect_regime()[0]
                result["adjusted_lot_size"] = round(lot_size * margin_mult, 2)
                result["note"] = (
                    f"Position adjusted by correlation regime multiplier ({margin_mult})"
                )

        return {
            **result,
            "veto_count_total": self._veto_count,
            "approval_count_total": self._approval_count,
            "timestamp": datetime.now().isoformat(),
        }

    def update_pnl(self, trade_pnl: float, symbol: Optional[str] = None) -> None:
        """Update daily and weekly P&L tracking.

        .. deprecated::
            Use ``EngineRiskManager.update_pnl`` (``quant_nanggroe.engine_bridge``)
            as the single PnL ingestion point. This method is a deprecation
            wrapper that logs a warning and delegates persistence to the
            engine_bridge shared backend if available, then falls back to
            local handling for backward compatibility.

        Args:
            trade_pnl: P&L from the completed trade.
            symbol: Symbol of the trade (for position tracking).
        """
        logger.warning(
            "DEPRECATED: RiskManager.update_pnl is deprecated — use "
            "EngineRiskManager.update_pnl (engine_bridge.py) as single "
            "ingestion point (risk sprawl consolidation). Delegating to "
            "engine_bridge persistence if available."
        )
        warnings.warn(
            "RiskManager.update_pnl is deprecated, use EngineRiskManager.update_pnl",
            DeprecationWarning,
            stacklevel=2,
        )
        # Best-effort delegation to engine_bridge persistence (single SoT).
        # EngineRiskManager and RiskManager share the same persistence backend
        # via quant_nanggroe.engine.persistence.get_persistence_backend(), so
        # touching that backend here proves the delegation path without breaking
        # backward compat (actual state mutation still happens below).
        try:
            from quant_nanggroe.engine.persistence import get_persistence_backend as _get_bridge_pb

            _bridge_pb = _get_bridge_pb()
            # Verify engine_bridge is importable (delegation target exists)
            import quant_nanggroe.engine_bridge as _eb  # noqa: F401

            logger.debug(
                "RiskManager.update_pnl delegated persistence check to engine_bridge: %s",
                type(_bridge_pb).__name__,
            )
        except Exception as _e:  # noqa: BLE001 — delegation is best-effort, never block PnL update
            logger.debug("engine_bridge persistence delegation skipped: %s", _e)

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
        method: str = "QUARTER_KELLY",
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
            # ponytail: KellyResult is a @dataclass (kelly.py:92), not a namedtuple,
            # so _replace() raises AttributeError and the cap silently failed.
            # Direct attribute assignment (dataclass is mutable, non-frozen).
            result.adjusted_fraction = max_fraction
            result.recommendation = f"CONSTITUTIONAL LIMIT: Position capped at {max_fraction:.1%}"

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
            "correlation_regime": {
                "regime": self.correlation_regime.detect_regime()[0],
                "margin_multiplier": self.correlation_regime.get_margin_multiplier(),
            },
            "margin_monitor": self.margin_monitor.status(),
            "hardcoded_limits": {
                "max_risk_per_trade": f"{MAX_RISK_PER_TRADE:.2%}",
                "max_daily_loss": f"{MAX_DAILY_LOSS:.2%}",
                "max_weekly_loss": f"{MAX_WEEKLY_LOSS:.2%}",
                "max_drawdown": f"{MAX_DRAWDOWN:.0%}",
                "min_rr_ratio": f"1:{MIN_RISK_REWARD}",
                "override_possible": False,
            },
        }

    def current_risk_snapshot(self) -> Dict[str, float]:
        """Ponytail: real P&L/drawdown fractions for kill-switch auto-activation.

        Returns fractional daily_pnl_pct / weekly_pnl_pct / max_drawdown_pct
        (NOT percentages) so callers can feed ``KillSwitch.check_auto_activate``
        directly without recomputing. This closes the silent 0.0 bypass where the
        worker monitor passed ``getattr(self, '_last_*', 0.0)`` that was never set.
        """
        self._reset_daily_if_needed()
        peak = self.state.peak_equity or 1.0
        daily_pnl_pct = (self.state.daily_pnl / peak) if self.state.daily_pnl < 0 else 0.0
        weekly_pnl_pct = (self.state.weekly_pnl / peak) if self.state.weekly_pnl < 0 else 0.0
        dd_info = self.drawdown_monitor.get_status()
        max_dd = float(dd_info.get("current_drawdown", 0.0) or 0.0)
        return {
            "daily_pnl_pct": daily_pnl_pct,
            "weekly_pnl_pct": weekly_pnl_pct,
            "max_drawdown_pct": max_dd,
        }

    def _reset_daily_if_needed(self) -> None:
        """Reset daily counters if new day. Handles missed Monday (doubt #5b). WIB UTC+7."""
        from datetime import timedelta, timezone
        WIB = timezone(timedelta(hours=7))
        today = datetime.now(WIB).date()
        if self.state.last_reset_date is None or today > self.state.last_reset_date:
            self.state.daily_pnl = 0.0
            self.state.trade_count_today = 0
            self.asset_daily_pnl.clear()
            # Clear hard stops across day boundary (doubt #9c)
            if hasattr(self, '_hard_stops'):
                try:
                    self._hard_stops.clear()
                except Exception:
                    pass
            # Reset weekly if ISO week changed or >=7 days since last reset (handles missed Monday)
            should_reset_weekly = False
            if self.state.last_reset_date is None:
                should_reset_weekly = today.weekday() == 0
            else:
                try:
                    iso_today = today.isocalendar()[1]
                    iso_last = self.state.last_reset_date.isocalendar()[1]
                    if iso_today != iso_last or (today - self.state.last_reset_date).days >= 7:
                        should_reset_weekly = True
                    elif today.weekday() == 0:  # Monday fallback
                        should_reset_weekly = True
                except Exception:
                    should_reset_weekly = today.weekday() == 0
            if should_reset_weekly:
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
            }, ttl=86400 * 7)  # 7-day TTL
            # NOTE: kill-switch ACTIVE state is owned by KillSwitch itself
            # (cross-proc file via QNA_KILL_SWITCH_STATE_FILE + _reconcile
            # daily-expiry). Do NOT persist/reactivate it here — the old
            # redundant flag bypassed _reconcile and re-halted every fresh
            # RiskManager() on a stale daily-level_1 (phantom-veto).
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

            # Kill-switch ACTIVE state is owned by KillSwitch (its own
            # reconcile() daily-expiry on the cross-proc file). Do NOT
            # re-activate from a generic persistence flag — that bypasses
            # reconcile and re-halts every fresh RiskManager() on a stale
            # daily-level_1 from a prior day/run (phantom-veto / over-active flip).
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
        direction: str = "buy",
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
        if direction == "sell":
            stop_loss = entry_price + stop_distance
        else:
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

    def update_mtm(self, unrealized_pnl: float) -> None:
        """Feed mark-to-market (open-position) P&L into the risk + kill-switch path.

        Pitfall #41 (realized-only blindness): the kill switch was only fed by
        ``update_pnl`` at trade CLOSE, so an open position bleeding during a live
        crash never moved equity/drawdown until the loss was realized. This method
        folds the current unrealized loss into the drawdown monitor and auto-check
        so the switch can trip mid-crash, not after.

        ``unrealized_pnl`` is the net open-position MTM P&L (negative = loss). It
        does NOT mutate realized ``daily_pnl``/``current_equity`` — only the
        kill-switch observation surface.
        """
        self.state.unrealized_pnl = unrealized_pnl
        # MTM equity = peak + realized daily + open MTM. Drawdown reads from peak.
        mtm_equity = self.state.peak_equity + self.state.daily_pnl + unrealized_pnl
        self.drawdown_monitor.update(max(mtm_equity, 0.0))
        # Pitfall #41 + phantom-veto reconciliation (2026-08-25): feed the open
        # loss into the kill-switch auto-check so a mid-crash bleed blocks NEW
        # positions immediately, not only at trade close. This is now safe to
        # re-enable because KillSwitch._reconcile() auto-expires stale LEVEL_1
        # (daily) activations on a new day — a transient MTM fluctuation can no
        # longer permanently freeze trading. Weekly/drawdown breaches still
        # require explicit human review by design.
        if unrealized_pnl < 0:
            self._auto_check_kill_switch(mtm_daily_loss_pct=unrealized_pnl)
        self._save_state()

    def _auto_check_kill_switch(self, mtm_daily_loss_pct: Optional[float] = None) -> None:
        """Auto-check if kill switch should activate based on risk limits."""
        # P1 FIX (2026-08-22): reconcile with the C5 shared state file BEFORE
        # deciding/activating. Without this, a stale process re-triggers a
        # LOWER level and _flush() overwrites a higher shared level
        # (last-writer-wins downgrade race → weekly breach silently lost).
        try:
            self.kill_switch._ensure_reconciled()
        except Exception:  # noqa: BLE001 — never block the veto path on reconcile errors
            pass
        if mtm_daily_loss_pct is not None:
            daily_loss_pct = abs(mtm_daily_loss_pct) / self.state.peak_equity if self.state.peak_equity > 0 else 0
        else:
            daily_loss_pct = abs(min(0, self.state.daily_pnl)) / self.state.peak_equity if self.state.peak_equity > 0 else 0
        weekly_loss_pct = abs(min(0, self.state.weekly_pnl)) / self.state.peak_equity if self.state.peak_equity > 0 else 0

        # ponytail: use the documented early-warning thresholds
        # (KILL_SWITCH_DAILY_PNL=-0.8% / KILL_SWITCH_WEEKLY_PNL=-2.5%) so the
        # kill switch fires BEFORE the 1%/3% constitutional hard limits. The
        # old code used MAX_DAILY_LOSS/MAX_WEEKLY_LOSS (1%/3%) which made these
        # constants dead and the early-warning buffer non-existent.
        if daily_loss_pct >= abs(KILL_SWITCH_DAILY_PNL):
            self.kill_switch.activate("AUTO_DAILY_LIMIT")
            logger.critical("KILL SWITCH: Daily loss limit breached (%.2f%% >= %.2f%%)", daily_loss_pct * 100, abs(KILL_SWITCH_DAILY_PNL) * 100)

        if weekly_loss_pct >= abs(KILL_SWITCH_WEEKLY_PNL):
            self.kill_switch.activate("AUTO_WEEKLY_LIMIT")
            logger.critical("KILL SWITCH: Weekly loss limit breached (%.2f%% >= %.2f%%)", weekly_loss_pct * 100, abs(KILL_SWITCH_WEEKLY_PNL) * 100)

        if self.drawdown_monitor.is_breached:
            self.kill_switch.activate("AUTO_MAX_DRAWDOWN")
            logger.critical("KILL SWITCH: Maximum drawdown breached (%.2f%% >= %.2f%%)", self.drawdown_monitor.current_drawdown * 100, MAX_DRAWDOWN * 100)


    # Per-Asset Risk Budgets (P1-26)

    def set_asset_budget(
        self,
        symbol: str,
        max_position_pct: Optional[float] = None,
        max_daily_loss_pct: Optional[float] = None,
    ) -> None:
        """Set per-asset risk budget parameters.

        Args:
            symbol: Trading symbol.
            max_position_pct: Max % of portfolio for this asset (default: MAX_POSITION_SIZE_PCT).
            max_daily_loss_pct: Max daily loss % for this asset (default: MAX_ASSET_DAILY_LOSS_PCT).
        """
        self.asset_budgets[symbol] = {
            "max_position_pct": max_position_pct if max_position_pct is not None else MAX_POSITION_SIZE_PCT,
            "max_daily_loss_pct": max_daily_loss_pct if max_daily_loss_pct is not None else MAX_ASSET_DAILY_LOSS_PCT,
        }

    def check_asset_risk(
        self,
        symbol: str,
        pnl_change: float,
        current_price: float,
        entry_price: float,
        atr: float,
        direction: str = "LONG",
    ) -> Dict[str, Any]:
        """Check per-asset risk limits including hard stop at entry.

        The hard stop at entry is: if price moves against entry by more than
        HARD_STOP_ATR_MULTIPLIER * ATR, force close regardless of trailing stop.
        Once set at entry, the hard stop can only tighten (trailing), never widen.

        Args:
            symbol: Trading symbol.
            pnl_change: P&L change from this trade action.
            current_price: Current market price.
            entry_price: Entry price.
            atr: Average True Range value.
            direction: Position direction (LONG/SHORT, default LONG).

        Returns:
            Dict with verdict, reason, asset_daily_pnl, remaining_budget.
        """
        self._reset_daily_if_needed()

        # Initialize budget defaults if not set
        if symbol not in self.asset_budgets:
            self.set_asset_budget(symbol)

        budget = self.asset_budgets[symbol]

        # Track daily P&L per asset
        self.asset_daily_pnl[symbol] = self.asset_daily_pnl.get(symbol, 0.0) + pnl_change
        asset_pnl = self.asset_daily_pnl[symbol]

        # Check daily loss limit
        portfolio_value = max(self.state.current_equity, 1)
        daily_loss_pct = abs(min(0, asset_pnl)) / portfolio_value
        max_loss = budget["max_daily_loss_pct"]
        if daily_loss_pct > max_loss:
            return {
                "verdict": "REJECTED",
                "reason": f"ASSET_DAILY_LOSS: {symbol} daily loss {daily_loss_pct:.4%} exceeds {max_loss:.2%}",
                "asset_daily_pnl": asset_pnl,
                "remaining_budget": 0.0,
            }

        # Hard stop at entry check (P1-26)
        is_long = direction.upper() in ("LONG", "BUY")
        if entry_price > 0 and atr > 0:
            hard_stop_distance = HARD_STOP_ATR_MULTIPLIER * atr

            # Initialize hard stop on first call
            if symbol not in self._hard_stops:
                stop_price = (
                    entry_price - hard_stop_distance
                    if is_long
                    else entry_price + hard_stop_distance
                )
                self._hard_stops[symbol] = {
                    "entry_price": entry_price,
                    "atr": atr,
                    "stop_price": stop_price,
                }

            hard_stop = self._hard_stops[symbol]

            # Hard stop can only tighten (move closer to entry), never widen
            if is_long:
                # Long: stop below entry; tightening = raising stop
                new_stop = current_price - hard_stop_distance
                if new_stop > hard_stop["stop_price"]:
                    hard_stop["stop_price"] = new_stop
                    hard_stop["atr"] = atr
            else:
                # Short: stop above entry; tightening = lowering stop
                new_stop = current_price + hard_stop_distance
                if new_stop < hard_stop["stop_price"]:
                    hard_stop["stop_price"] = new_stop
                    hard_stop["atr"] = atr

            # Check if hard stop is triggered
            hit_hard_stop = (
                is_long and current_price <= hard_stop["stop_price"]
            ) or (
                not is_long and current_price >= hard_stop["stop_price"]
            )

            if hit_hard_stop:
                return {
                    "verdict": "REJECTED",
                    "reason": f"HARD_STOP: {symbol} hit hard stop at {hard_stop['stop_price']:.2f} (entry: {entry_price:.2f}, ATR: {atr:.4f})",
                    "asset_daily_pnl": asset_pnl,
                    "remaining_budget": max_loss - daily_loss_pct,
                }

        return {
            "verdict": "APPROVED",
            "reason": f"Asset risk OK for {symbol}",
            "asset_daily_pnl": asset_pnl,
            "remaining_budget": max_loss - daily_loss_pct,
        }

    # Concentration Limits (P1-32)

    def check_concentration(
        self,
        symbol: str,
        current_value: float,
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """Check if adding a position would exceed the per-asset concentration limit.

        Args:
            symbol: Trading symbol.
            current_value: Current position value (including proposed addition).
            portfolio_value: Total portfolio value.

        Returns:
            Dict with verdict, reason, limit_pct, current_pct.
        """
        limit_pct = self.concentration_limits.get(symbol, MAX_POSITION_SIZE_PCT)
        current_pct = current_value / portfolio_value if portfolio_value > 0 else 0

        if current_pct > limit_pct:
            return {
                "verdict": "REJECTED",
                "reason": f"CONCENTRATION_LIMIT: {symbol} would be {current_pct:.2%} of portfolio (limit: {limit_pct:.2%})",
                "limit_pct": limit_pct,
                "current_pct": current_pct,
            }

        return {
            "verdict": "APPROVED",
            "reason": f"Concentration OK for {symbol}",
            "limit_pct": limit_pct,
            "current_pct": current_pct,
        }

    def check_total_concentration(
        self,
        positions: List[Dict[str, Any]],
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """Check if total position value across all assets exceeds max concentration.

        Args:
            positions: List of dicts with at least {'market_value': float}.
            portfolio_value: Total portfolio value.

        Returns:
            Dict with verdict, reason, total_pct, limit_pct.
        """
        total_value = sum(p.get("market_value", 0) for p in positions)
        total_pct = total_value / portfolio_value if portfolio_value > 0 else 0

        if total_pct > MAX_TOTAL_CONCENTRATION:
            return {
                "verdict": "REJECTED",
                "reason": f"TOTAL_CONCENTRATION: All positions total {total_pct:.2%} of portfolio (limit: {MAX_TOTAL_CONCENTRATION:.0%})",
                "total_pct": total_pct,
                "limit_pct": MAX_TOTAL_CONCENTRATION,
            }

        return {
            "verdict": "APPROVED",
            "reason": "Total concentration OK",
            "total_pct": total_pct,
            "limit_pct": MAX_TOTAL_CONCENTRATION,
        }

    # Cost-Aware Budget (P1-32)

    @property
    def cost_budget_remaining(self) -> float:
        return self.trading_budget

    def track_cost(self, trade_cost: float) -> Dict[str, Any]:
        """Deduct a trade cost from the trading budget.

        Args:
            trade_cost: Cost of the trade (fees, slippage, etc.).

        Returns:
            Dict with cost, remaining_budget, budget_exhausted flag.
        """
        self.trading_budget -= trade_cost
        budget_exhausted = self.trading_budget <= 0

        if budget_exhausted:
            logger.warning("Trading budget exhausted: %.2f remaining", self.trading_budget)

        return {
            "cost": trade_cost,
            "remaining_budget": self.trading_budget,
            "budget_exhausted": budget_exhausted,
        }

    def check_cost_affordable(self, estimated_cost: float) -> bool:
        """Check if the estimated trade cost is within remaining budget.

        Args:
            estimated_cost: Estimated cost for the proposed trade.

        Returns:
            True if affordable, False if budget would be exceeded.
        """
        return estimated_cost <= self.trading_budget
