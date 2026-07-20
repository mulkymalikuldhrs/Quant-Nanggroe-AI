from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class HullMAStrategy(BaseStrategy):
    """Hull Moving Average — lag-reduced moving average."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="HullMA", params=params)
        self.period: int = int(self.params.get("period", 20))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        half = int(self.period / 2)
        sqrt_per = int(np.sqrt(self.period))
        wma_half = c.rolling(half).apply(lambda x: np.average(x, weights=np.arange(1, len(x) + 1)), raw=True)
        wma_full = c.rolling(self.period).apply(lambda x: np.average(x, weights=np.arange(1, len(x) + 1)), raw=True)
        raw_hull = 2 * wma_half - wma_full
        hull = raw_hull.rolling(sqrt_per).apply(lambda x: np.average(x, weights=np.arange(1, len(x) + 1)), raw=True)
        if np.isnan(hull.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if price > hull.iloc[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Price above Hull MA", evidence={"hull": round(float(hull.iloc[-1]), 4)},
                factors=["technical", "hull_ma"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
            price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
            reasoning="Price below Hull MA", evidence={"hull": round(float(hull.iloc[-1]), 4)},
            factors=["technical", "hull_ma"])

