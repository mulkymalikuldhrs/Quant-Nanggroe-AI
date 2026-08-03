"""Drawdown Monitoring — Max DD, CVaR, Risk of Ruin.

Implements drawdown monitoring and analysis with constitutional
maximum drawdown enforcement.

Key metrics:
- Maximum Drawdown: Largest peak-to-trough decline
- Current Drawdown: Current decline from peak
- CVaR-based Drawdown: Expected drawdown in tail scenarios
- Risk of Ruin: Probability of reaching drawdown limit
- Recovery Time: Estimated time to recover from drawdown

The maximum drawdown limit (10%) is a CONSTITUTIONAL limit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from quant_nanggroe.engine.risk.constants import MAX_DRAWDOWN_PCT as MAX_DRAWDOWN
from quant_nanggroe.engine.risk.constants import STARTING_CAPITAL

logger = logging.getLogger(__name__)


@dataclass
class DrawdownInfo:
    """Drawdown analysis result."""

    current_drawdown: float
    max_drawdown: float
    drawdown_duration: int  # Bars since peak
    recovery_factor: float  # Current equity / peak equity
    is_breached: bool  # Whether constitutional limit is breached


class DrawdownMonitor:
    """Drawdown Monitor with Constitutional Limit.

    Tracks equity drawdowns and enforces the maximum drawdown
    constitutional limit (10%). When breached, signals for
    kill switch activation.

    Usage:
        monitor = DrawdownMonitor(max_drawdown=0.10)
        monitor.update(equity_value)
        if monitor.is_breached:
            # Halt trading
    """

    def __init__(
        self,
        max_drawdown: float = MAX_DRAWDOWN,
        initial_equity: float = STARTING_CAPITAL,
    ) -> None:
        """Initialize drawdown monitor.

        Args:
            max_drawdown: Maximum allowed drawdown (0.10 = 10%).
            initial_equity: Starting equity value.
        """
        self._max_dd = min(max_drawdown, MAX_DRAWDOWN)  # Can't exceed constitutional limit
        self._peak = initial_equity
        self._current_equity = initial_equity
        self._bars_since_peak = 0
        self._max_dd_observed = 0.0
        self._equity_history: List[float] = [initial_equity]
        self._dd_history: List[float] = [0.0]

    @property
    def current_drawdown(self) -> float:
        """Current drawdown as a fraction (0.0 = no drawdown, 0.10 = 10% DD)."""
        if self._peak <= 0:
            return 0.0
        return (self._peak - self._current_equity) / self._peak

    @property
    def max_drawdown_observed(self) -> float:
        """Maximum drawdown observed since monitoring started."""
        return self._max_dd_observed

    @property
    def is_breached(self) -> bool:
        """Whether the constitutional drawdown limit is breached."""
        return self.current_drawdown >= self._max_dd

    def update(self, equity: float) -> DrawdownInfo:
        """Update monitor with new equity value.

        Args:
            equity: Current portfolio equity.

        Returns:
            DrawdownInfo with current drawdown status.
        """
        self._current_equity = equity
        self._equity_history.append(equity)

        if equity > self._peak:
            self._peak = equity
            self._bars_since_peak = 0
        else:
            self._bars_since_peak += 1

        dd = self.current_drawdown
        self._dd_history.append(dd)

        if dd > self._max_dd_observed:
            self._max_dd_observed = dd

        if self.is_breached:
            logger.critical(
                "DRAWDOWN BREACHED: %.2f%% >= %.2f%% (constitutional limit)",
                dd * 100, self._max_dd * 100,
            )

        return DrawdownInfo(
            current_drawdown=dd,
            max_drawdown=self._max_dd_observed,
            drawdown_duration=self._bars_since_peak,
            recovery_factor=equity / self._peak if self._peak > 0 else 0.0,
            is_breached=self.is_breached,
        )

    def get_status(self) -> Dict:
        """Get current drawdown status."""
        return {
            "current_drawdown": f"{self.current_drawdown:.4f}",
            "max_drawdown_observed": f"{self._max_dd_observed:.4f}",
            "constitutional_limit": f"{self._max_dd:.4f}",
            "drawdown_breached": self.is_breached,
            "bars_since_peak": self._bars_since_peak,
            "recovery_factor": f"{self._current_equity / self._peak:.4f}" if self._peak > 0 else "0.0000",
        }

    def calculate_cvar_drawdown(
        self,
        equity_series: pd.Series,
        confidence_level: float = 0.95,
    ) -> float:
        """Calculate CVaR-based drawdown estimate.

        Instead of just the worst historical drawdown, this
        estimates the expected drawdown in the worst (1-α) scenarios.

        Args:
            equity_series: Historical equity curve.
            confidence_level: Confidence level for CVaR.

        Returns:
            CVaR drawdown estimate.
        """
        returns = equity_series.pct_change().dropna()
        if len(returns) == 0:
            return 0.0

        var = returns.quantile(1 - confidence_level)
        tail = returns[returns <= var]

        if len(tail) == 0:
            return abs(var)

        cvar = tail.mean()
        # Compound the CVaR over a reasonable drawdown horizon
        horizon = max(5, int(len(returns) * 0.05))  # 5% of history
        cvar_dd = 1 - (1 + cvar) ** horizon

        return abs(cvar_dd)

    @staticmethod
    def calculate_risk_of_ruin(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        max_drawdown_limit: float = MAX_DRAWDOWN,
    ) -> float:
        """Calculate probability of reaching the drawdown limit.

        Uses the gambler's ruin formula adapted for trading.

        Args:
            win_rate: Probability of winning trade.
            avg_win: Average win amount.
            avg_loss: Average loss amount.
            max_drawdown_limit: Maximum drawdown before ruin.

        Returns:
            Probability of ruin (0-1).
        """
        if avg_loss <= 0:
            return 0.0

        b = avg_win / avg_loss
        p = win_rate
        q = 1.0 - p

        if b * p <= q:
            return 1.0  # Negative expectancy → certain ruin

        try:
            # Risk of ruin approximation
            r = q / (b * p)
            # Scale by drawdown limit
            units = max_drawdown_limit / (avg_loss / 1.0)  # Number of losing trades to ruin
            return min(1.0, r ** units)
        except (ValueError, ZeroDivisionError):
            return 1.0

    @staticmethod
    def estimate_recovery_time(
        current_drawdown: float,
        avg_annual_return: float = 0.10,
    ) -> float:
        """Estimate time to recover from drawdown.

        Args:
            current_drawdown: Current drawdown as fraction.
            avg_annual_return: Expected annual return.

        Returns:
            Estimated recovery time in years.
        """
        if current_drawdown <= 0 or avg_annual_return <= 0:
            return 0.0

        recovery_factor = 1.0 / (1.0 - current_drawdown)
        import math
        return math.log(recovery_factor) / math.log(1 + avg_annual_return)
