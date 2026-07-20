"""Fibonacci Arc strategy."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class FibonacciArcStrategy(BaseStrategy):
    """Fibonacci arcs for curved support/resistance levels.

    Draws arcs at 38.2%, 50%, 61.8% radii from a trend line.
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="FibonacciArc", params=params)
        self.lookback: int = int(self.params.get("lookback", 60))
        self.arc_levels: List[float] = self.params.get("arc_levels", [0.382, 0.5, 0.618])

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        high = data["high"]
        low = data["low"]
        close = data["close"]
        price = float(close.iloc[-1])

        lookback = min(self.lookback, len(data))
        swing_high = float(high.iloc[-lookback:].max())
        swing_low = float(low.iloc[-lookback:].min())
        trend_range = swing_high - swing_low
        if trend_range == 0:
            return None

        mid = (swing_high + swing_low) / 2.0
        dist_from_mid = abs(price - mid) / (trend_range / 2.0)

        for level in self.arc_levels:
            if abs(dist_from_mid - level) < 0.05:
                sig = 1.0 if price < mid else -1.0
                return Signal(
                    symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                    confidence=0.6, price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                    reasoning=f"Price at Fibonacci arc {level:.1%}",
                    evidence={"arc_level": level, "dist_from_mid": round(dist_from_mid, 4)},
                    factors=["fibonacci", "arc"],
                )
        return None
