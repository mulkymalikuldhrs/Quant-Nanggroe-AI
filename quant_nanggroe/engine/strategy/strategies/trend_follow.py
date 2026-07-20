"""Trend-following strategy using dual SMA crossover with ADX confirmation.

Implements strategy #31 from Kakushadze (2015) — Dual Moving Average Crossover:
- Fast/slow SMA crossover (+DI / -DI in the original) for trend direction
- ADX > threshold to confirm trend strength
- Trailing ATR stop loss
- Best suited for trending regimes (bull/bear)

References:
    - Kakushadze, Z. (2015). "151 Trading Strategies." Algorithmic Finance.
    - Wilder, J.W. (1978). New Concepts in Technical Trading Systems.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class TrendFollowStrategy(BaseStrategy):
    """Dual MA crossover trend-follow with ADX confirmation and trailing ATR stop.

    Signal format: float in [-1, 1] embedded via SignalType + confidence.
       > 0 → BUY,  < 0 → SELL,  0 → no position.

    Parameters:
        fast_period: Fast SMA period (default 50).
        slow_period: Slow SMA period (default 200).
        adx_period: ADX lookback period (default 14).
        adx_threshold: Minimum ADX to confirm trend (default 25).
        atr_period: ATR lookback for trailing stop (default 14).
        atr_stop_mult: ATR multiplier for stop distance (default 3.0).
        entry_threshold: Minimum signal to enter (default 0.1).
        transaction_cost_bps: One-way cost in basis points (default 10.0).
        min_trade_interval_bars: Min bars between trades (default 5).
        symbol: Trading symbol for Signal (default "ASSET").
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="TrendFollow", params=params)
        self.fast_period: int = int(self.params.get("fast_period", 50))
        self.slow_period: int = int(self.params.get("slow_period", 200))
        self.adx_period: int = int(self.params.get("adx_period", 14))
        self.adx_threshold: float = float(self.params.get("adx_threshold", 25.0))
        self.atr_period: int = int(self.params.get("atr_period", 14))
        self.atr_stop_mult: float = float(self.params.get("atr_stop_mult", 3.0))
        self.entry_threshold: float = float(self.params.get("entry_threshold", 0.1))
        self.transaction_cost_bps: float = float(self.params.get("transaction_cost_bps", 10.0))
        self.min_trade_interval_bars: int = int(self.params.get("min_trade_interval_bars", 5))
        self.symbol: str = str(self.params.get("symbol", "ASSET"))

        self._last_trade_bar: int = -self.min_trade_interval_bars
        self._current_position: float = 0.0
        self._last_entry_price: Optional[float] = None

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.slow_period + self.adx_period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        close = data["close"]
        high = data["high"]
        low = data["low"]
        price = float(close.iloc[-1])
        bars = len(data)

        raw = self._compute_raw_signal(data)
        if abs(raw) < self.entry_threshold:
            raw = 0.0

        if bars - self._last_trade_bar < self.min_trade_interval_bars:
            return None

        if abs(raw - self._current_position) < 0.01 and not (raw == 0.0 and self._current_position != 0.0):
            return None

        self._last_trade_bar = bars

        if raw == 0.0 and self._current_position != 0.0:
            self._last_entry_price = None
            return self._exit_signal(price)

        if raw != 0.0:
            self._last_entry_price = price
            return self._entry_signal(raw, price, data)

        return None

    def _compute_raw_signal(self, data: pd.DataFrame) -> float:
        """Compute raw trend signal in [-1, 1] using dual SMA + ADX."""
        close = data["close"]
        high = data["high"]
        low = data["low"]

        fast_sma = self.compute_sma(close, self.fast_period)
        slow_sma = self.compute_sma(close, self.slow_period)

        if np.isnan(fast_sma.iloc[-1]) or np.isnan(slow_sma.iloc[-1]):
            return 0.0

        adx = self._compute_adx(high, low, close)
        if np.isnan(adx):
            return 0.0

        if adx < self.adx_threshold:
            return 0.0

        cur_fast = float(fast_sma.iloc[-1])
        cur_slow = float(slow_sma.iloc[-1])
        prev_fast = float(fast_sma.iloc[-2]) if len(fast_sma) >= 2 else cur_fast
        prev_slow = float(slow_sma.iloc[-2]) if len(slow_sma) >= 2 else cur_slow

        cur_diff = cur_fast - cur_slow
        prev_diff = prev_fast - prev_slow

        crossover_up = prev_diff <= 0 < cur_diff
        crossover_down = prev_diff >= 0 > cur_diff

        if crossover_up:
            return 1.0
        if crossover_down:
            return -1.0
        if cur_diff > 0:
            return 0.5
        if cur_diff < 0:
            return -0.5
        return 0.0

    def _compute_adx(self, high: pd.Series, low: pd.Series, close: pd.Series) -> float:
        """Compute ADX (Average Directional Index) at last bar."""
        period = self.adx_period
        if len(high) < period + 2:
            return np.nan

        up_move = high.diff()
        down_move = low.diff()

        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=period, min_periods=period).mean()

        plus_di = 100.0 * plus_dm.rolling(window=period, min_periods=period).mean() / (atr + 1e-10)
        minus_di = 100.0 * minus_dm.rolling(window=period, min_periods=period).mean() / (atr + 1e-10)

        dx = 100.0 * (plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-10)
        adx = dx.rolling(window=period, min_periods=period).mean()

        if len(adx) < 1 or np.isnan(adx.iloc[-1]):
            return np.nan
        return float(adx.iloc[-1])

    def _entry_signal(self, target: float, price: float, data: pd.DataFrame) -> Signal:
        direction = SignalType.BUY if target > 0 else SignalType.SELL
        confidence = min(abs(target), 1.0)
        self._current_position = target

        atr = self.compute_atr(data["high"], data["low"], data["close"], self.atr_period)
        stop_loss = None
        if len(atr) > 0 and not np.isnan(atr.iloc[-1]):
            atr_val = float(atr.iloc[-1])
            stop_distance = atr_val * self.atr_stop_mult
            if target > 0:
                stop_loss = round(price - stop_distance, 6)
            else:
                stop_loss = round(price + stop_distance, 6)

        return Signal(
            symbol=self.symbol,
            signal_type=direction,
            confidence=round(confidence, 4),
            price=round(price, 6),
            stop_loss=stop_loss,
                source_agent=self.name,
                source_strategy=self.name,
            reasoning=(
                f"TrendFollow[{self.fast_period}/{self.slow_period}] "
                f"{'LONG' if target > 0 else 'SHORT'} "
                f"target={target:.3f}"
            ),
            evidence={
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
                "target_signal": round(float(target), 4),
                "transaction_cost_bps": self.transaction_cost_bps,
            },
            factors=["trend_follow", "ma_crossover"],
        )

    def _exit_signal(self, price: float) -> Signal:
        exit_type = (
            SignalType.CLOSE_LONG if self._current_position > 0 else SignalType.CLOSE_SHORT
        )
        prior = self._current_position
        self._current_position = 0.0
        return Signal(
            symbol=self.symbol,
            signal_type=exit_type,
            confidence=0.7,
            price=round(price, 6),
                source_agent=self.name,
                source_strategy=self.name,
            reasoning=f"TrendFollow EXIT (prior={prior:.3f})",
            evidence={"prior_position": round(float(prior), 4)},
            factors=["trend_follow", "exit"],
        )
