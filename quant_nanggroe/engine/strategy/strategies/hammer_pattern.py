from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class HammerPatternStrategy(BaseStrategy):
    """Hammer trading strategy.

    Detects the hammer candlestick pattern on the most recent completed candle(s) and generates
    reversal signals based on prior trend context.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="HammerPattern", params=params)
        self.wick_ratio: float = float(self.params.get("wick_ratio", 2.0))
        self.lookback_trend: int = int(self.params.get("lookback_trend", 10))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback_trend + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        o, c, h, l = data["open"], data["close"], data["high"], data["low"]
        body = abs(c - o)
        lower_wick = o.min(c) - l
        upper_wick = h - o.max(c)
        hammer = (lower_wick > body * self.wick_ratio) & (upper_wick < body * 0.3)
        if not hammer.iloc[-1]:
            return None
        trend = (c.iloc[-1] - c.iloc[-self.lookback_trend]) / c.iloc[-self.lookback_trend]
        if trend >= 0:
            return None
        return Signal(
            symbol=self.name, signal_type=SignalType.BUY, confidence=0.6,
            price=round(float(c.iloc[-1]), 6), source_agent=self.name,
                source_strategy=self.name, reasoning="Hammer at downtrend bottom",
            evidence={"trend_pct": round(float(trend * 100), 2)}, factors=["candlestick", "hammer"],
        )

    def __str__(self) -> str:
        return f"HammerPatternStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

