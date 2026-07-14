from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class HaramiPatternStrategy(BaseStrategy):
    """Harami trading strategy.

    Detects the harami candlestick pattern on the most recent completed candle(s) and generates
    reversal signals based on prior trend context.
    """



    def __init__(self, params=None):
        super().__init__(name="HaramiPatternStrategy", params=params)
    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 2:
            return None
        o, c = data["open"], data["close"]
        prev_body = abs(c.iloc[-2] - o.iloc[-2])
        cur_body = abs(c.iloc[-1] - o.iloc[-1])
        if cur_body >= prev_body * 0.8:
            return None
        prev_high = max(o.iloc[-2], c.iloc[-2])
        prev_low = min(o.iloc[-2], c.iloc[-2])
        cur_high = max(o.iloc[-1], c.iloc[-1])
        cur_low = min(o.iloc[-1], c.iloc[-1])
        if cur_high < prev_high and cur_low > prev_low:
            sig = -1.0 if c.iloc[-2] > o.iloc[-2] else 1.0
            return Signal(
                symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                confidence=0.5, price=round(float(c.iloc[-1]), 6), source_agent=self.name,
                source_strategy=self.name, reasoning=f"Harami {'bullish' if sig > 0 else 'bearish'}",
                evidence={}, factors=["candlestick", "harami"],
            )
        return None

    def __str__(self) -> str:
        return f"HaramiPatternStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

