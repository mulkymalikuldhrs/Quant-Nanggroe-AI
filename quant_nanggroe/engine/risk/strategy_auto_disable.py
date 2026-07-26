"""Auto-disable strategies when trailing Sharpe drops below threshold.

Monitors per-strategy trailing Sharpe ratios and automatically
marks strategies as disabled when performance degrades. Integrates
with the kill switch system (LEVEL_1 equivalent per strategy).

References:
    - kill_switch.py: KillSwitch class with LEVEL_1/2/3, on_activate callbacks
    - strategy_lifecycle.py: StrategyLifecycleManager with ACTIVE/HIBERNATING/KILLED
    - utils/math.py: compute_sharpe_ratio() helper

Usage::

    from quant_nanggroe.engine.risk.strategy_auto_disable import AutoDisableManager
    import pandas as pd

    mgr = AutoDisableManager(sharpe_window=30)
    pnl_series = pd.Series([...])  # daily P&L values
    still_active = mgr.update("MyStrategy", pnl_series)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.risk.kill_switch import KillSwitch

logger = logging.getLogger(__name__)

DEFAULT_SHARPE_WINDOW: int = 30
DEFAULT_THRESHOLD: float = 0.3
DEFAULT_CONFIRM_WINDOW: int = 30
DEFAULT_STATE_PATH: str = "data/strategy_auto_disable_state.json"
DEFAULT_PAPER_MODE: bool = False


class StrategyPerformance:
    """Internal state for a single strategy's performance tracking."""

    def __init__(self, name: str):
        self.name: str = name
        self.disabled: bool = False
        self.disabled_at: Optional[str] = None
        self.disabled_reason: str = ""
        self.consecutive_above_threshold: int = 0
        self.total_updates: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "disabled": self.disabled,
            "disabled_at": self.disabled_at,
            "disabled_reason": self.disabled_reason,
            "consecutive_above_threshold": self.consecutive_above_threshold,
            "total_updates": self.total_updates,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StrategyPerformance:
        perf = cls(data["name"])
        perf.disabled = data["disabled"]
        perf.disabled_at = data.get("disabled_at")
        perf.disabled_reason = data.get("disabled_reason", "")
        perf.consecutive_above_threshold = data.get("consecutive_above_threshold", 0)
        perf.total_updates = data.get("total_updates", 0)
        return perf


class AutoDisableManager:
    """Monitors trailing Sharpe per strategy and auto-disables when below threshold.

    Features:
        - Tracks trailing Sharpe per strategy over a configurable window
        - Disables strategy when trailing Sharpe < threshold (default: 0.3)
        - Re-enables after N consecutive days above threshold (default: 30)
        - Integrates with KillSwitch (LEVEL_1 equivalent per strategy)
        - Persists disabled state to JSON for restart survival
        - Returns True from update() if strategy is still active

    Usage::

        mgr = AutoDisableManager()
        # Feed daily P&L series for a strategy
        active = mgr.update("MeanReversion", daily_pnl_series)
        if not active:
            # Strategy was auto-disabled, skip trade execution
            pass

        # Check which strategies are disabled
        disabled = mgr.get_disabled_strategies()

        # Re-enable manually
        mgr.enable("MeanReversion")
    """

    def __init__(
        self,
        *,
        sharpe_window: int = DEFAULT_SHARPE_WINDOW,
        threshold: float = DEFAULT_THRESHOLD,
        confirm_window: int = DEFAULT_CONFIRM_WINDOW,
        state_path: str = DEFAULT_STATE_PATH,
        kill_switch: Optional[KillSwitch] = None,
        paper_mode: bool = DEFAULT_PAPER_MODE,
    ):
        self._sharpe_window: int = sharpe_window
        self._threshold: float = threshold
        self._confirm_window: int = confirm_window
        self._state_path: str = state_path
        self._kill_switch: KillSwitch = kill_switch or KillSwitch()
        self._paper_mode: bool = paper_mode

        self._strategies: Dict[str, StrategyPerformance] = {}

        self._load_state()

    # ── Public API ─────────────────────────────────────────────────────────

    def update(self, strategy_name: str, pnl_series: pd.Series) -> bool:
        """Update trailing Sharpe for a strategy.

        Args:
            strategy_name: Name of the strategy.
            pnl_series: Series of P&L values (daily returns ideally).

        Returns:
            True if the strategy is still active (not disabled).
        """
        if pnl_series is None or len(pnl_series) < self._sharpe_window:
            return True

        perf = self._strategies.setdefault(
            strategy_name, StrategyPerformance(strategy_name)
        )
        perf.total_updates += 1

        trailing_sharpe = self._compute_trailing_sharpe(pnl_series)

        if perf.disabled:
            self._check_re_enable(perf, trailing_sharpe)
        else:
            self._check_disable(perf, trailing_sharpe)

        return not perf.disabled

    def disable(
        self,
        strategy_name: str,
        reason: str = "Manual disable",
    ) -> bool:
        """Manually disable a strategy.

        Args:
            strategy_name: Name of the strategy to disable.
            reason: Reason for disabling.

        Returns:
            True if the strategy was newly disabled.
        """
        perf = self._strategies.setdefault(
            strategy_name, StrategyPerformance(strategy_name)
        )
        if perf.disabled:
            return False

        self._set_disabled(perf, reason)
        return True

    def enable(self, strategy_name: str, reason: str = "Manual re-enable") -> bool:
        """Manually re-enable a strategy.

        Args:
            strategy_name: Name of the strategy to enable.
            reason: Reason for re-enabling.

        Returns:
            True if the strategy was newly enabled.
        """
        perf = self._strategies.get(strategy_name)
        if perf is None or not perf.disabled:
            return False

        self._set_enabled(perf, reason)
        return True

    def is_disabled(self, strategy_name: str) -> bool:
        """Check if a strategy is currently disabled."""
        perf = self._strategies.get(strategy_name)
        return perf.disabled if perf is not None else False

    def get_disabled_strategies(self) -> List[str]:
        """Get list of currently disabled strategy names."""
        return [name for name, p in self._strategies.items() if p.disabled]

    def get_active_strategies(self) -> List[str]:
        """Get list of currently active (not disabled) strategy names."""
        return [name for name, p in self._strategies.items() if not p.disabled]

    def get_state(self) -> Dict[str, Dict[str, Any]]:
        """Get serialisable state of all tracked strategies."""
        return {
            name: perf.to_dict()
            for name, perf in self._strategies.items()
        }

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "sharpe_window": self._sharpe_window,
            "threshold": self._threshold,
            "confirm_window": self._confirm_window,
            "state_path": self._state_path,
            "paper_mode": self._paper_mode,
        }

    def save_state(self) -> None:
        """Persist disabled state to JSON."""
        path = Path(self._state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "config": self.get_config(),
            "strategies": self.get_state(),
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        logger.debug("Auto-disable state saved to %s", self._state_path)

    # ── Internal ──────────────────────────────────────────────────────────

    def _compute_trailing_sharpe(self, pnl_series: pd.Series) -> float:
        """Compute trailing annualized Sharpe from the last N values."""
        series = pnl_series.iloc[-self._sharpe_window:]
        mean = series.mean()
        std = series.std()
        if std == 0 or pd.isna(std):
            return 0.0
        return float(mean / std * np.sqrt(365))

    def _check_disable(self, perf: StrategyPerformance, trailing_sharpe: float) -> None:
        """Check if trailing Sharpe warrants disabling."""
        if trailing_sharpe >= self._threshold:
            return

        reason = (
            f"Trailing Sharpe {trailing_sharpe:.3f} < threshold "
            f"{self._threshold} over {self._sharpe_window}-day window"
        )
        self._set_disabled(perf, reason)

    def _check_re_enable(self, perf: StrategyPerformance, trailing_sharpe: float) -> None:
        """Check if trailing Sharpe has recovered enough to re-enable."""
        if trailing_sharpe >= self._threshold:
            perf.consecutive_above_threshold += 1
        else:
            perf.consecutive_above_threshold = 0

        if perf.consecutive_above_threshold >= self._confirm_window:
            reason = (
                f"Trailing Sharpe above {self._threshold} for "
                f"{perf.consecutive_above_threshold} consecutive updates"
            )
            self._set_enabled(perf, reason)

    def _set_disabled(self, perf: StrategyPerformance, reason: str) -> None:
        """Mark strategy as disabled (per-strategy, not global kill switch)."""
        perf.disabled = True
        perf.disabled_at = datetime.now(timezone.utc).isoformat()
        perf.disabled_reason = reason
        perf.consecutive_above_threshold = 0

        logger.warning(
            "Strategy '%s' AUTO-DISABLED: %s",
            perf.name,
            reason,
        )

        self.save_state()

    def _set_enabled(self, perf: StrategyPerformance, reason: str) -> None:
        """Mark strategy as enabled."""
        perf.disabled = False
        perf.disabled_at = None
        perf.disabled_reason = ""
        perf.consecutive_above_threshold = 0

        logger.info(
            "Strategy '%s' RE-ENABLED: %s",
            perf.name,
            reason,
        )

        self.save_state()

    def _load_state(self) -> None:
        """Load disabled state from JSON persistence."""
        path = Path(self._state_path)
        if not path.exists():
            return
        try:
            with open(path) as f:
                state = json.load(f)
            for name, data in state.get("strategies", {}).items():
                self._strategies[name] = StrategyPerformance.from_dict(data)
            logger.debug(
                "Loaded auto-disable state for %d strategies",
                len(self._strategies),
            )
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning("Failed to load auto-disable state: %s", e)
