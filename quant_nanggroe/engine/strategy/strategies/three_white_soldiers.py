from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ThreeWhiteSoldiersStrategy(BaseStrategy):
    """Three White Soldiers trading strategy.

    Detects the three white soldiers candlestick pattern by computing
    technical indicators and generating trading signals.
    """



    def __init__(self, params=None):
        super().__init__(name="ThreeWhiteSoldiersStrategy", params=params)
    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return 10

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 3:
            return None
        o, c = data["open"], data["close"]
        bulls = all(c.iloc[-i] > o.iloc[-i] for i in range(1, 4))
        higher_closes = all(c.iloc[-i] > c.iloc[-i-1] for i in range(1, 3))
        if bulls and higher_closes:
            return Signal(
                symbol=self.name, signal_type=SignalType.BUY, confidence=0.7,
                price=round(float(c.iloc[-1]), 6), source_agent=self.name,
                source_strategy=self.name, reasoning="Three white soldiers",
                evidence={}, factors=["candlestick", "three_white_soldiers"],
            )
        return None

    def __str__(self) -> str:
        return f"ThreeWhiteSoldiersStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

