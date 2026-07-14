"""Fibonacci Time strategy."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class FibonacciTimeStrategy(BaseStrategy):
    """Fibonacci time zones for cycle-based turning points.

    Counts bars forward from a swing extreme at Fib ratios.
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="FibonacciTime", params=params)
        self.lookback: int = int(self.params.get("lookback", 100))
        self.time_levels: List[int] = self.params.get("time_levels", [13, 21, 34, 55, 89])

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        price = float(close.iloc[-1])
        total_bars = len(data)

        # Find furthest swing extreme
        lookback = min(self.lookback, total_bars)
        swing_high_idx = data["high"].iloc[-lookback:].idxmax()
        swing_low_idx = data["low"].iloc[-lookback:].idxmin()
        bars_from_high = total_bars - data.index.get_loc(swing_high_idx) - 1
        bars_from_low = total_bars - data.index.get_loc(swing_low_idx) - 1

        for tl in self.time_levels:
            if bars_from_high == tl or bars_from_low == tl:
                sig = -1.0 if bars_from_high == tl else 1.0
                return Signal(
                    symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                    confidence=0.55, price=round(price, 6), source_agent=self.name,
                    source_strategy=self.name,
                    reasoning=f"Fibonacci time zone {tl} bars from extreme",
                    evidence={"time_level": tl, "bars_from_high": bars_from_high, "bars_from_low": bars_from_low},
                    factors=["fibonacci", "time"],
                )
        return None
