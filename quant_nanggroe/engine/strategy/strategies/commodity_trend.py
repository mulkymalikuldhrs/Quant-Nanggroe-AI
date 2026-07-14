from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class CommodityTrendStrategy(BaseStrategy):
    """Commodity Trend trading strategy.

    Detects the commodity trend candlestick pattern by computing
    technical indicators and generating trading signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="CommodityTrend", params=params)
        self.fast: int = int(self.params.get("fast", 20))
        self.slow: int = int(self.params.get("slow", 100))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.slow + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        fast_ma = self.compute_sma(c, self.fast)
        slow_ma = self.compute_sma(c, self.slow)
        if np.isnan(fast_ma.iloc[-1]) or np.isnan(slow_ma.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if fast_ma.iloc[-1] > slow_ma.iloc[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Commodity trend bullish", evidence={"fast_ma": round(float(fast_ma.iloc[-1]), 4), "slow_ma": round(float(slow_ma.iloc[-1]), 4)},
                factors=["macro", "commodity"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
            price=round(price, 6), source_agent=self.name, source_strategy=self.name,
            reasoning="Commodity trend bearish", evidence={"fast_ma": round(float(fast_ma.iloc[-1]), 4), "slow_ma": round(float(slow_ma.iloc[-1]), 4)},
            factors=["macro", "commodity"])

    def __str__(self) -> str:
        return f"CommodityTrendStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

