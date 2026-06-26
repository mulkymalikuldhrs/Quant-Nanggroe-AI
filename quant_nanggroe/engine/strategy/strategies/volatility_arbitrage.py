"""Volatility arbitrage using rolling, EWMA and GARCH(1,1) vol estimates.

Compares short-term to long-term vol via a z-scored vol ratio and
generates mean-reversion signals on vol.

References:
    - Bollerslev (1986). J. Econometrics, 31(3), 307-327.
    - J.P. Morgan (1996). RiskMetrics -- Technical Document. 4th ed.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

try:
    from scipy.optimize import minimize
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

logger = logging.getLogger(__name__)

_LAM = 0.94  # ponytail: RiskMetrics EWMA lambda


class VolatilityArbitrageStrategy(BaseStrategy):
    """Vol arbitrage via vol-ratio z-score.  Shorts vol when z > entry,
    longs vol when z < -entry.

    Parameters
    ----------
    vol_lookback : int  (20)
        Short-term vol estimation window.
    vol_long_lookback : int  (60)
        Long-term vol rolling window.
    entry_threshold : float  (2.0)
        Z-score entry threshold.
    exit_threshold : float  (0.5)
        Z-score exit threshold.
    vol_estimation : str  ("ewma")
        ``"historical"``, ``"ewma"``, or ``"garch"``.
    transaction_cost_bps : float  (10.0)
        One-way cost in basis points.
    min_trade_interval_bars : int  (5)
        Minimum bars between consecutive trades.
    """

    def __init__(self, params: Optional[dict] = None):
        super().__init__(name="VolatilityArbitrage", params=params)
        self.vol_lookback: int = self.params.get("vol_lookback", 20)
        self.vol_long_lookback: int = self.params.get("vol_long_lookback", 60)
        self.entry_threshold: float = self.params.get("entry_threshold", 2.0)
        self.exit_threshold: float = self.params.get("exit_threshold", 0.5)
        self.vol_estimation: str = self.params.get("vol_estimation", "ewma")
        self.transaction_cost_bps: float = self.params.get("transaction_cost_bps", 10.0)
        self.min_trade_interval_bars: int = self.params.get("min_trade_interval_bars", 5)
        self._last_trade_bar: int = -self.min_trade_interval_bars
        self._current_position: float = 0.0

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.vol_long_lookback + 1

    # --- Vol estimation -------------------------------------------------------

    def _compute_vol_series(self, log_returns: pd.Series) -> pd.Series:
        method = self.vol_estimation
        if method == "historical":
            return log_returns.rolling(self.vol_lookback, min_periods=self.vol_lookback).std()
        if method == "ewma":
            return np.sqrt(log_returns.pow(2).ewm(alpha=1 - _LAM, adjust=False).mean())
        if method == "garch":
            return self._garch_vol(log_returns)
        logger.warning("Unknown vol_estimation '%s', falling back to EWMA", method)
        return np.sqrt(log_returns.pow(2).ewm(alpha=1 - _LAM, adjust=False).mean())

    def _garch_vol(self, log_returns: pd.Series) -> pd.Series:
        """GARCH(1,1) conditional vol via MLE + forward pass.
        Falls back to EWMA when scipy unavailable or optimisation fails.
        """
        if not _HAS_SCIPY or len(log_returns) < 20:
            return np.sqrt(log_returns.pow(2).ewm(alpha=1 - _LAM, adjust=False).mean())

        vals = log_returns.values.astype(np.float64)
        T = len(vals)
        var0 = float(np.var(vals, ddof=1))

        def neg_ll(params: np.ndarray) -> float:
            o, a, b = params
            if o <= 0 or a < 0 or b < 0 or (a + b) >= 1:
                return 1e10
            s2 = np.empty(T)
            s2[0] = var0
            for t in range(1, T):
                s2[t] = o + a * vals[t - 1] ** 2 + b * s2[t - 1]
                if s2[t] <= 0:
                    return 1e10
            return float(0.5 * np.sum(np.log(2 * np.pi * s2) + vals ** 2 / s2))

        try:
            result = minimize(neg_ll, [var0 * 0.1, 0.1, 0.85],
                              method="L-BFGS-B",
                              bounds=[(1e-8, None), (1e-8, 0.999), (1e-8, 0.999)],
                              options={"maxiter": 500})
            omega, alpha, beta = result.x
        except Exception:
            return np.sqrt(log_returns.pow(2).ewm(alpha=1 - _LAM, adjust=False).mean())  # ponytail

        cond_var = np.empty(T)
        cond_var[0] = var0
        for t in range(1, T):
            cond_var[t] = omega + alpha * vals[t - 1] ** 2 + beta * cond_var[t - 1]
        return pd.Series(np.sqrt(cond_var), index=log_returns.index)

    # --- Signal generation ----------------------------------------------------

    def _compute_target(self, data: pd.DataFrame) -> float:
        close = data["close"]
        log_ret = np.log(close / close.shift(1)).dropna()
        if len(log_ret) < self.vol_long_lookback + self.vol_lookback:
            return 0.0

        vol = self._compute_vol_series(log_ret)
        hist_vol = vol.rolling(self.vol_long_lookback, min_periods=self.vol_long_lookback).mean()
        ratio = vol / (hist_vol + 1e-10)
        rmean = ratio.rolling(self.vol_long_lookback, min_periods=self.vol_long_lookback).mean()
        rstd = ratio.rolling(self.vol_long_lookback, min_periods=self.vol_long_lookback).std()
        z = float(((ratio - rmean) / (rstd + 1e-10)).iloc[-1])
        if np.isnan(z):
            return 0.0

        et, xt = self.entry_threshold, self.exit_threshold
        if z > et:
            return -min((z - xt) / (et - xt + 1e-10), 1.0)
        if z < -et:
            return min((-z - xt) / (et - xt + 1e-10), 1.0)
        if abs(z) < xt:
            return 0.0
        return 0.0  # ponytail: buffer zone, no signal

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        bars, price = len(data), float(data["close"].iloc[-1])
        target = self._compute_target(data)
        if bars - self._last_trade_bar < self.min_trade_interval_bars:
            return None
        if abs(target - self._current_position) < 0.01:
            return None
        self._last_trade_bar = bars
        if target == 0.0 and self._current_position != 0.0:
            return self._build_exit(price)
        if target != 0.0:
            return self._build_entry(target, price)
        return None

    # --- Signal builders ------------------------------------------------------

    def _build_entry(self, target: float, price: float) -> Signal:
        is_long = target > 0
        confidence = min(abs(target), 1.0)
        self._current_position = target
        return Signal(
            symbol=self.name,
            signal_type=SignalType.BUY if is_long else SignalType.SELL,
            confidence=round(confidence, 4),
            price=round(price, 6),
            source_agent=self.name,
            source_strategy=self.name,
            reasoning=(
                f"VolArb[{self.vol_estimation}] "
                f"{'LONG VOL' if is_long else 'SHORT VOL'} "
                f"target={target:.3f}, cost={self.transaction_cost_bps:.0f}bps"
            ),
            evidence={
                "vol_estimation": self.vol_estimation,
                "target_signal": round(float(target), 4),
                "transaction_cost_bps": self.transaction_cost_bps,
            },
            factors=["volatility_arbitrage", self.vol_estimation],
        )

    def _build_exit(self, price: float) -> Signal:
        exit_type = SignalType.CLOSE_LONG if self._current_position > 0 else SignalType.CLOSE_SHORT
        prior = self._current_position
        self._current_position = 0.0
        return Signal(
            symbol=self.name,
            signal_type=exit_type,
            confidence=0.7,
            price=round(price, 6),
            source_agent=self.name,
            source_strategy=self.name,
            reasoning=f"VolArb[{self.vol_estimation}] EXIT flat",
            evidence={"prior_position": round(float(prior), 4),
                       "transaction_cost_bps": self.transaction_cost_bps},
            factors=["volatility_arbitrage", self.vol_estimation],
        )
