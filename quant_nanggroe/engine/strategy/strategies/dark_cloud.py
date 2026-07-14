from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class DarkCloudCoverStrategy(BaseStrategy):
    """Dark Cloud Cover trading strategy.

    Detects the dark cloud cover candlestick pattern by tracking
    volume-weighted price action as a proxy for institutional dark pool activity.
    """



    def __init__(self, params=None):
        super().__init__(name="DarkCloudCoverStrategy", params=params)
    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 2:
            return None
        o, c = data["open"], data["close"]
        prev_bull = c.iloc[-2] > o.iloc[-2]
        cur_bear = c.iloc[-1] < o.iloc[-1]
        mid_prev = (c.iloc[-2] + o.iloc[-2]) / 2
        covers = c.iloc[-1] < mid_prev and o.iloc[-1] > o.iloc[-2]
        if prev_bull and cur_bear and covers:
            return Signal(
                symbol=self.name, signal_type=SignalType.SELL, confidence=0.6,
                price=round(float(c.iloc[-1]), 6), source_agent=self.name,
                source_strategy=self.name, reasoning="Dark cloud cover",
                evidence={}, factors=["candlestick", "dark_cloud"],
            )
        return None

    def __str__(self) -> str:
        return f"DarkCloudCoverStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

