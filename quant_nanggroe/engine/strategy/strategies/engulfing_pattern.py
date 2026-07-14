from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class EngulfingPatternStrategy(BaseStrategy):
    """Bullish/bearish engulfing — current body fully engulfs previous."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="EngulfingPattern", params=params)
        self.lookback_trend: int = int(self.params.get("lookback_trend", 5))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback_trend + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        o, c = data["open"], data["close"]
        prev_body = abs(c.iloc[-2] - o.iloc[-2])
        cur_body = abs(c.iloc[-1] - o.iloc[-1])
        prev_bull = c.iloc[-2] > o.iloc[-2]
        cur_bull = c.iloc[-1] > o.iloc[-1]
        prev_high = max(o.iloc[-2], c.iloc[-2])
        prev_low = min(o.iloc[-2], c.iloc[-2])
        cur_high = max(o.iloc[-1], c.iloc[-1])
        cur_low = min(o.iloc[-1], c.iloc[-1])

        if cur_body > prev_body and cur_low < prev_low and cur_high > prev_high:
            if not prev_bull and cur_bull:
                return Signal(
                    symbol=self.name, signal_type=SignalType.BUY, confidence=0.7,
                    price=round(float(c.iloc[-1]), 6), source_agent=self.name,
                    source_strategy=self.name, reasoning="Bullish engulfing",
                    evidence={}, factors=["candlestick", "engulfing"],
                )
            if prev_bull and not cur_bull:
                return Signal(
                    symbol=self.name, signal_type=SignalType.SELL, confidence=0.7,
                    price=round(float(c.iloc[-1]), 6), source_agent=self.name,
                    source_strategy=self.name, reasoning="Bearish engulfing",
                    evidence={}, factors=["candlestick", "engulfing"],
                )
        return None
