from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ThreeBlackCrowsStrategy(BaseStrategy):
    """Three Black Crows trading strategy.

    Detects the three black crows candlestick pattern by computing
    technical indicators and generating trading signals.
    """



    def __init__(self, params=None):
        super().__init__(name="ThreeBlackCrowsStrategy", params=params)
    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return 10

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 3:
            return None
        o, c = data["open"], data["close"]
        bears = all(c.iloc[-i] < o.iloc[-i] for i in range(1, 4))
        lower_closes = all(c.iloc[-i] < c.iloc[-i-1] for i in range(1, 3))
        if bears and lower_closes:
            return Signal(
                symbol=self.name, signal_type=SignalType.SELL, confidence=0.7,
                price=round(float(c.iloc[-1]), 6), source_agent=self.name,
                source_strategy=self.name, reasoning="Three black crows",
                evidence={}, factors=["candlestick", "three_black_crows"],
            )
        return None

    def __str__(self) -> str:
        return f"ThreeBlackCrowsStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

