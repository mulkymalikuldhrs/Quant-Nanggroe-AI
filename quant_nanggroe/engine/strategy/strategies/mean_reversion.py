"""Mean reversion strategy with transaction costs, frequency controls, and multiple variants.

Implements three mean reversion approaches:
1. Z-score — entry/exit on rolling z-score thresholds
2. Bollinger Band — entry when price crosses band boundaries (Kakushadze #15)
3. Ornstein-Uhlenbeck — position sizing via half-life estimation

Transaction costs and trade frequency controls prevent overtrading.
Half-life is estimated per call rather than pre-computed, so walk-forward
validation re-fits the OU parameters on each fold's training window.

References:
    - Kakushadze, Z. (2015). "151 Trading Strategies." Algorithmic Finance.
    - Avellaneda, M. & Lee, J.H. (2010). "Statistical Arbitrage in the US
      Equities Market." Quantitative Finance, 10(7), 761-782.
    - De Prado, M. (2018). Advances in Financial Machine Learning. Wiley.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion with configurable variant and trade frequency controls.

    Parameters
    ----------
    strategy_type : str
        ``"zscore"``, ``"bollinger"``, or ``"ou"`` (default ``"zscore"``).
    lookback : int
        Rolling window for mean / std calculation (default 20).
    entry_threshold : float
        Z-score or band threshold for entry (default 2.0).
    exit_threshold : float
        Z-score or band threshold for exit (default 0.5).
    bollinger_std : float
        Standard deviations for Bollinger Bands (default 2.0).
    atr_stop_mult : float
        ATR multiplier for stop-loss (default 1.5, Kakushadze #15).
    min_signal_strength : float
        Minimum absolute signal value to generate a trade (default 0.1).
    transaction_cost_bps : float
        One-way transaction cost in basis points (default 10.0 = 0.1%).
    min_trade_interval_bars : int
        Minimum bars between consecutive trades (default 5).
    """

    def __init__(self, params: Optional[dict] = None):
        super().__init__(name="MeanReversion", params=params)
        self.strategy_type: str = self.params.get("strategy_type", "zscore")
        self.lookback: int = self.params.get("lookback", 20)
        self.entry_threshold: float = self.params.get("entry_threshold", 2.0)
        self.exit_threshold: float = self.params.get("exit_threshold", 0.5)
        self.bollinger_std: float = self.params.get("bollinger_std", 2.0)
        self.atr_stop_mult: float = self.params.get("atr_stop_mult", 1.5)
        self.min_signal_strength: float = self.params.get("min_signal_strength", 0.1)
        self.transaction_cost_bps: float = self.params.get("transaction_cost_bps", 10.0)
        self.min_trade_interval_bars: int = self.params.get("min_trade_interval_bars", 5)

        # Internal state — reset on fresh init
        self._last_trade_bar: int = -self.min_trade_interval_bars
        self._current_position: float = 0.0  # net target in [-1, 1]

    def required_columns(self) -> List[str]:
        return ["close", "high", "low"]

    def warmup_period(self) -> int:
        return self.lookback + 1

    # ------------------------------------------------------------------
    # OU half-life estimation  (re-fits every call — walk-forward safe)
    # ------------------------------------------------------------------

    @staticmethod
    def estimate_half_life(series: pd.Series) -> float:
        """OU half-life via OLS: X_{t+1} - X_t = alpha + beta * X_t + eps.

        Returns bars-to-half-mean-reversion or ``inf`` if not mean-reverting.

        .. math:: \\text{half-life} = -\\ln(2) / \\beta,\\quad \\beta < 0
        """
        if len(series) < 10:
            return np.inf
        lagged = series.shift(1).dropna()
        delta = series.diff().dropna()
        common = lagged.index.intersection(delta.index)
        if len(common) < 5:
            return np.inf
        try:
            slope, *_ = scipy_stats.linregress(
                lagged.loc[common].values, delta.loc[common].values
            )
        except (ValueError, np.linalg.LinAlgError):
            return np.inf
        if slope >= 0:
            return np.inf
        return max(-np.log(2) / slope, 1.0)

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        close = data["close"]
        price = float(close.iloc[-1])
        bars = len(data)

        target = self._compute_target(close)

        if abs(target) < self.min_signal_strength:
            target = 0.0

        # Trade frequency gate: enough bars since last trade?
        if bars - self._last_trade_bar < self.min_trade_interval_bars:
            return None

        # No meaningful change from current position
        if abs(target - self._current_position) < 0.01:
            return None

        self._last_trade_bar = bars

        if target == 0.0 and self._current_position != 0.0:
            return self._exit_signal(price)
        if target != 0.0:
            return self._entry_signal(target, price, data)
        return None

    def _compute_target(self, close: pd.Series) -> float:
        """Dispatch to variant. Returns target position in [-1, 1]."""
        if self.strategy_type == "zscore":
            return self._zscore_target(close)
        if self.strategy_type == "bollinger":
            return self._bollinger_target(close)
        if self.strategy_type == "ou":
            return self._ou_target(close)
        logger.warning("Unknown strategy_type '%s'", self.strategy_type)
        return 0.0

    # ------------------------------------------------------------------
    # Variant implementations  —  each returns target in [-1, 1]
    # ------------------------------------------------------------------

    def _zscore_target(self, close: pd.Series) -> float:
        zs = self.compute_zscore(close, self.lookback)
        z = float(zs.iloc[-1])
        if np.isnan(z):
            return 0.0
        if z > self.entry_threshold:
            return -min(z / self.entry_threshold, 1.0)
        if z < -self.entry_threshold:
            return min(-z / self.entry_threshold, 1.0)
        return 0.0  # ponytail: between thresholds — no action

    def _bollinger_target(self, close: pd.Series) -> float:
        upper, _middle, lower = self.compute_bollinger_bands(
            close, self.lookback, self.bollinger_std
        )
        p = float(close.iloc[-1])
        lv = float(lower.iloc[-1])
        uv = float(upper.iloc[-1])
        if np.isnan(lv) or np.isnan(uv):
            return 0.0
        if p < lv:
            return min((lv - p) / (lv + 1e-10) * 10, 1.0)
        if p > uv:
            return -min((p - uv) / (uv + 1e-10) * 10, 1.0)
        return 0.0  # ponytail: inside bands — no action

    def _ou_target(self, close: pd.Series) -> float:
        zs = self.compute_zscore(close, self.lookback)
        z = float(zs.iloc[-1])
        if np.isnan(z):
            return 0.0
        hl = self.estimate_half_life(close)
        if hl == np.inf:
            return 0.0
        size_mult = min(self.lookback / max(hl, 1.0), 2.0)
        if z > self.entry_threshold:
            return -min(z / self.entry_threshold * size_mult, 1.0)
        if z < -self.entry_threshold:
            return min(-z / self.entry_threshold * size_mult, 1.0)
        return 0.0

    # ------------------------------------------------------------------
    # Signal construction helpers
    # ------------------------------------------------------------------

    def _entry_signal(self, target: float, price: float, data: Optional[pd.DataFrame] = None) -> Signal:
        direction = SignalType.BUY if target > 0 else SignalType.SELL
        confidence = min(abs(target), 1.0)
        self._current_position = target

        stop_loss = None
        if data is not None and "low" in data.columns and "high" in data.columns:
            atr = self.compute_atr(data["high"], data["low"], data["close"], period=14)
            if len(atr) > 0 and not np.isnan(atr.iloc[-1]):
                atr_val = float(atr.iloc[-1])
                stop_distance = atr_val * self.atr_stop_mult
                if target > 0:
                    stop_loss = round(price - stop_distance, 6)
                else:
                    stop_loss = round(price + stop_distance, 6)

        return Signal(
            symbol=self.name,
            signal_type=direction,
            confidence=round(confidence, 4),
            price=round(price, 6),
            stop_loss=stop_loss,
                source_agent=self.name,
                source_strategy=self.name,
            reasoning=(
                f"MeanReversion[{self.strategy_type}] "
                f"{'LONG' if target > 0 else 'SHORT'} "
                f"signal={target:.3f}, cost={self.transaction_cost_bps:.0f}bps"
            ),
            evidence={
                "strategy_type": self.strategy_type,
                "target_signal": round(float(target), 4),
                "transaction_cost_bps": self.transaction_cost_bps,
            },
            factors=["mean_reversion", self.strategy_type],
        )

    def _exit_signal(self, price: float) -> Signal:
        exit_type = (
            SignalType.CLOSE_LONG
            if self._current_position > 0
            else SignalType.CLOSE_SHORT
        )
        prior = self._current_position
        self._current_position = 0.0
        return Signal(
            symbol=self.name,
            signal_type=exit_type,
            confidence=0.7,
            price=round(price, 6),
                source_agent=self.name,
                source_strategy=self.name,
            reasoning=f"MeanReversion[{self.strategy_type}] EXIT flat",
            evidence={
                "prior_position": round(float(prior), 4),
                "transaction_cost_bps": self.transaction_cost_bps,
            },
            factors=["mean_reversion", self.strategy_type],
        )
