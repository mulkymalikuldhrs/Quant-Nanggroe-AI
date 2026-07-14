"""Fibonacci Retracement strategy."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class FibonacciRetracementStrategy(BaseStrategy):
    """Fibonacci retracement levels for reversal entries.

    Identifies swing high/low, computes 0.236/0.382/0.5/0.618/0.786 levels.
    Buy when price pulls back to a major Fib level with bullish momentum.
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="FibonacciRetracement", params=params)
        self.lookback: int = int(self.params.get("lookback", 50))
        self.fib_levels: List[float] = self.params.get("fib_levels", [0.236, 0.382, 0.5, 0.618, 0.786])
        self.rsi_period: int = int(self.params.get("rsi_period", 14))
        self.rsi_oversold: float = float(self.params.get("rsi_oversold", 35.0))
        self.rsi_overbought: float = float(self.params.get("rsi_overbought", 65.0))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback + self.rsi_period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        high = data["high"]
        low = data["low"]
        price = float(close.iloc[-1])

        # Find swing high/low
        recent_high = float(high.iloc[-self.lookback:].max())
        recent_low = float(low.iloc[-self.lookback:].min())
        if recent_high == recent_low:
            return None

        diff = recent_high - recent_low
        rsi = self.compute_rsi(close, self.rsi_period)
        rsi_val = float(rsi.iloc[-1]) if len(rsi) > 0 and not np.isnan(rsi.iloc[-1]) else 50.0

        # Check retracement from high to low (downtrend pullback)
        retrace_from_low = (price - recent_low) / diff
        signal = 0.0
        reasoning = ""

        for level in self.fib_levels:
            if abs(retrace_from_low - level) < 0.03 and rsi_val < self.rsi_oversold:
                signal = 1.0
                reasoning = f"Bullish fib retracement at {level:.1%}, RSI={rsi_val:.0f}"
                break
            if abs(retrace_from_low - (1 - level)) < 0.03 and rsi_val > self.rsi_overbought:
                signal = -1.0
                reasoning = f"Bearish fib retracement at {1-level:.1%}, RSI={rsi_val:.0f}"
                break

        if signal == 0.0:
            return None

        return Signal(
            symbol=self.name, signal_type=SignalType.BUY if signal > 0 else SignalType.SELL,
            confidence=abs(signal), price=round(price, 6), source_agent=self.name,
            source_strategy=self.name, reasoning=reasoning,
            evidence={"fib_level": round(retrace_from_low, 4), "rsi": round(rsi_val, 2)},
            factors=["fibonacci", "retracement"],
        )
