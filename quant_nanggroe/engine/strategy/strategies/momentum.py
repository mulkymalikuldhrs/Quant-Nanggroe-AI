"""Momentum Strategy.

Four variants: time-series, dual momentum, MA crossover, and MACD.
Includes transaction cost modeling and trade frequency gates.

References:
    - Jegadeesh & Titman (1993). Returns to Buying Winners and Selling Losers.
      Journal of Finance, 48(1), 65-91.
    - Moskowitz, Ooi & Pedersen (2012). Time Series Momentum.
      Journal of Financial Economics, 104(2), 228-250.
    - Antonacci, G. (2014). Dual Momentum Investing. McGraw-Hill.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """Multi-variant momentum strategy with cost and frequency controls.

    Signal format: float in [-1, 1] embedded via SignalType + confidence.
       > 0 → BUY,  < 0 → SELL,  0 → no position.

    Parameters:
        strategy_type: "ts_momentum", "dual_momentum", "ma_crossover", "macd"
        lookback: TS momentum lookback (default 126, ~6 months daily)
        fast_lookback: Fast MA period for dual/ma_crossover/macd (default 20)
        slow_lookback: Slow MA period for dual/ma_crossover/macd (default 50)
        entry_threshold: Minimum |signal| to open a position (default 0.05)
        exit_threshold: |signal| below this forces flat (default 0.01)
        transaction_cost_bps: One-way cost in basis points (default 10.0)
        min_trade_interval_bars: Minimum bars between trades (default 5)
        signal_smoothing: SMA window on raw signal to reduce whipsaws (default 3)
        symbol: Trading symbol for Signal generation (default "ASSET")
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="Momentum", params=params)
        self.strategy_type: str = self.params.get("strategy_type", "ts_momentum")
        self.lookback: int = self.params.get("lookback", 126)
        self.fast_lookback: int = self.params.get("fast_lookback", 20)
        self.slow_lookback: int = self.params.get("slow_lookback", 50)
        self.entry_threshold: float = self.params.get("entry_threshold", 0.05)
        self.exit_threshold: float = self.params.get("exit_threshold", 0.01)
        self.transaction_cost_bps: float = self.params.get("transaction_cost_bps", 10.0)
        self.min_trade_interval_bars: int = self.params.get("min_trade_interval_bars", 5)
        self.signal_smoothing: int = self.params.get("signal_smoothing", 3)
        self.symbol: str = self.params.get("symbol", "ASSET")

        self._last_trade_bar: int = -self.min_trade_interval_bars  # ponytail: first trade always allowed
        self._signal_buffer: List[float] = []  # ponytail: FIFO for SMA smoothing

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return max(self.lookback, self.slow_lookback) + self.signal_smoothing + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate momentum signal.

        Steps:
          1. Compute raw signal from the active variant ([-1, 1]).
          2. Smooth via SMA of last N values.
          3. Reject if minimum trade interval not met.
          4. Map smoothed signal to SignalType + confidence.
          5. Deduct transaction cost from confidence.
        """
        if not self.validate_data(data):
            return None

        raw = self._compute_raw_signal(data)
        smoothed = self._smooth(raw)

        if not self._can_trade(data):
            return None

        result = self._classify(smoothed)
        if result is None:
            return None

        signal_type, confidence = result
        current_price = data["close"].iloc[-1]
        cost_penalty = self.transaction_cost_bps / 10000.0
        net_confidence = max(0.0, confidence - cost_penalty)

        self._last_trade_bar = len(data) - 1

        return Signal(
            symbol=self.symbol,
            signal_type=signal_type,
            confidence=round(float(net_confidence), 4),
            price=round(float(current_price), 6),
            source_agent=self.name,
            source_strategy=self.name,
            reasoning=(
                f"Momentum {signal_type.value} ({self.strategy_type}): "
                f"raw={raw:.4f} smoothed={smoothed:.4f} "
                f"cost_penalty={cost_penalty:.4f}"
            ),
            evidence={
                "strategy_type": self.strategy_type,
                "raw_signal": round(float(raw), 4),
                "smoothed_signal": round(float(smoothed), 4),
                "transaction_cost_bps": self.transaction_cost_bps,
            },
            factors=["momentum", self.strategy_type],
        )

    # ------------------------------------------------------------------
    # Variant router
    # ------------------------------------------------------------------

    def _compute_raw_signal(self, data: pd.DataFrame) -> float:
        """Return raw momentum signal in [-1, 1]; 0 = no conviction."""
        if self.strategy_type == "ts_momentum":
            return self._ts_momentum(data)
        elif self.strategy_type == "dual_momentum":
            return self._dual_momentum(data)
        elif self.strategy_type == "ma_crossover":
            return self._ma_crossover(data)
        elif self.strategy_type == "macd":
            return self._macd(data)
        logger.warning("Unknown strategy_type=%s, returning 0", self.strategy_type)
        return 0.0

    # ------------------------------------------------------------------
    # Time-series momentum  (Moskowitz, Ooi & Pedersen 2012)
    # ------------------------------------------------------------------

    def _ts_momentum(self, data: pd.DataFrame) -> float:
        """Buy when return > entry_threshold, sell when < -entry_threshold."""
        close = data["close"]
        ret = close.iloc[-1] / close.iloc[-self.lookback - 1] - 1.0

        if abs(ret) < self.exit_threshold:
            return 0.0
        if ret > self.entry_threshold:
            return 1.0
        if ret < -self.entry_threshold:
            return -1.0
        # ponytail: decaying trend zone → proportional signal
        return float(np.clip(ret / self.entry_threshold, -1.0, 1.0))

    # ------------------------------------------------------------------
    # Dual momentum  (Antonacci 2014)
    # ------------------------------------------------------------------

    def _dual_momentum(self, data: pd.DataFrame) -> float:
        """Require both absolute (price vs slow MA) and relative (fast vs slow MA) aligment."""
        close = data["close"]
        slow_ma = self.compute_sma(close, self.slow_lookback)
        fast_ma = self.compute_sma(close, self.fast_lookback)

        if np.isnan(slow_ma.iloc[-1]) or np.isnan(fast_ma.iloc[-1]):
            return 0.0

        abs_mom = (close.iloc[-1] / slow_ma.iloc[-1]) - 1.0
        rel_mom = (fast_ma.iloc[-1] / slow_ma.iloc[-1]) - 1.0

        if abs_mom > 0 and rel_mom > 0:
            score = (abs_mom + rel_mom) / self.entry_threshold
            return float(min(score, 1.0))
        if abs_mom < 0 and rel_mom < 0:
            score = (abs_mom + rel_mom) / self.entry_threshold
            return float(max(score, -1.0))
        return 0.0

    # ------------------------------------------------------------------
    # MA crossover
    # ------------------------------------------------------------------

    def _ma_crossover(self, data: pd.DataFrame) -> float:
        """+1 when fast MA crosses above slow MA, -1 when crosses below."""
        close = data["close"]
        fast_ma = self.compute_sma(close, self.fast_lookback)
        slow_ma = self.compute_sma(close, self.slow_lookback)

        if len(fast_ma) < 2 or np.isnan(fast_ma.iloc[-1]) or np.isnan(slow_ma.iloc[-1]):
            return 0.0

        cur = float(fast_ma.iloc[-1] - slow_ma.iloc[-1])
        prev = float(fast_ma.iloc[-2] - slow_ma.iloc[-2])

        if prev <= 0 < cur:
            return 1.0
        if prev >= 0 > cur:
            return -1.0
        if cur > 0:
            return 0.5
        if cur < 0:
            return -0.5
        return 0.0

    # ------------------------------------------------------------------
    # MACD
    # ------------------------------------------------------------------

    def _macd(self, data: pd.DataFrame) -> float:
        """Signal direction from MACD histogram sign and crossover."""
        close = data["close"]
        macd_line, _, histogram = self.compute_macd(
            close, self.fast_lookback, self.slow_lookback, signal_period=9
        )

        if len(macd_line) < 2 or np.isnan(macd_line.iloc[-1]):
            return 0.0

        cur_h = float(histogram.iloc[-1])
        prev_h = float(histogram.iloc[-2])
        denom = abs(macd_line.iloc[-1]) + 1e-10

        if prev_h <= 0 < cur_h:       # crossover up
            return float(min(cur_h / denom, 1.0))
        if prev_h >= 0 > cur_h:       # crossover down
            return float(-min(abs(cur_h) / denom, 1.0))
        if cur_h > 0:                 # continuation up
            return float(min(cur_h / denom * 0.5, 0.5))
        if cur_h < 0:                 # continuation down
            return float(-min(abs(cur_h) / denom * 0.5, 0.5))
        return 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _smooth(self, raw: float) -> float:
        """Simple FIFO SMA to reduce whipsaw signals."""
        self._signal_buffer.append(raw)
        if len(self._signal_buffer) > self.signal_smoothing:
            self._signal_buffer.pop(0)
        return float(np.mean(self._signal_buffer))

    def _can_trade(self, data: pd.DataFrame) -> bool:
        """Enforce minimum gap between consecutive trades."""
        bars_since_last = (len(data) - 1) - self._last_trade_bar
        return bars_since_last >= self.min_trade_interval_bars

    def _classify(self, signal: float) -> Optional[tuple]:
        """Map smoothed signal to (SignalType, confidence) or None if flat."""
        if abs(signal) < 1e-10:
            return None
        confidence = min(abs(signal), 1.0)
        if signal > 0:
            return (SignalType.BUY, confidence)
        return (SignalType.SELL, confidence)
