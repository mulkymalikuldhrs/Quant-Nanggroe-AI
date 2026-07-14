from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class DojiPatternStrategy(BaseStrategy):
    """Doji trading strategy.

    Detects the doji candlestick pattern on the most recent completed candle(s) and generates
    reversal signals based on prior trend context.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="DojiPattern", params=params)
        self.body_threshold: float = float(self.params.get("body_threshold", 0.05))
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
        candle_range = h - l
        doji = body < (candle_range * self.body_threshold) & (candle_range > 0)
        if not doji.iloc[-1]:
            return None
        trend = (c.iloc[-1] - c.iloc[-self.lookback_trend]) / c.iloc[-self.lookback_trend]
        sig = -1.0 if trend > 0 else 1.0
        return Signal(
            symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
            confidence=0.4, price=round(float(c.iloc[-1]), 6),
            source_agent=self.name, source_strategy=self.name,
            reasoning=f"Doji after {'uptrend' if trend > 0 else 'downtrend'}, reversal expected",
            evidence={"trend_pct": round(float(trend * 100), 2)}, factors=["candlestick", "doji"],
        )

    def __str__(self) -> str:
        return f"DojiPatternStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

