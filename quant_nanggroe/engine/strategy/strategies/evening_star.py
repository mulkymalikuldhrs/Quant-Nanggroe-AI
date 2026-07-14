from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class EveningStarStrategy(BaseStrategy):
    """Evening Star trading strategy.

    Detects the evening star candlestick pattern by computing
    technical indicators and generating trading signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="EveningStar", params=params)
        self.body_ratio: float = float(self.params.get("body_ratio", 0.3))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return 10

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 3:
            return None
        o, c = data["open"], data["close"]
        bodies = [abs(c.iloc[-3] - o.iloc[-3]), abs(c.iloc[-2] - o.iloc[-2]), abs(c.iloc[-1] - o.iloc[-1])]
        if bodies[1] > bodies[0] * self.body_ratio or bodies[1] > bodies[2] * self.body_ratio:
            return None
        first_bull = c.iloc[-3] > o.iloc[-3]
        second_small = bodies[1] < bodies[0] * 0.5 and bodies[1] < bodies[2] * 0.5
        third_bear = c.iloc[-1] < o.iloc[-1] and c.iloc[-1] < (c.iloc[-3] + o.iloc[-3]) / 2
        if first_bull and second_small and third_bear:
            return Signal(
                symbol=self.name, signal_type=SignalType.SELL, confidence=0.75,
                price=round(float(c.iloc[-1]), 6), source_agent=self.name,
                source_strategy=self.name, reasoning="Evening star pattern",
                evidence={}, factors=["candlestick", "evening_star"],
            )
        return None

    def __str__(self) -> str:
        return f"EveningStarStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

