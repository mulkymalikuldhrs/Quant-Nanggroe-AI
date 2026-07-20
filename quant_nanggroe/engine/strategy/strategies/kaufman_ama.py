from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class KaufmanAMAStrategy(BaseStrategy):
    """Kaufman Adaptive Moving Average — trend with noise filter."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="KaufmanAMA", params=params)
        self.period: int = int(self.params.get("period", 10))
        self.fast: int = int(self.params.get("fast", 2))
        self.slow: int = int(self.params.get("slow", 30))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period + self.slow + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < self.period + self.slow:
            return None
        c = data["close"].values
        n = len(c)
        ama = np.empty(n)
        ama[:self.period] = c[:self.period]
        for i in range(self.period, n):
            if i < self.period:
                continue
            change = abs(c[i] - c[i - self.period])
            volatility = np.sum(np.abs(np.diff(c[i - self.period:i + 1])))
            er = change / (volatility + 1e-10)
            sc = (er * (2.0 / (self.fast + 1) - 2.0 / (self.slow + 1)) + 2.0 / (self.slow + 1)) ** 2
            ama[i] = ama[i - 1] + sc * (c[i] - ama[i - 1])
        price = float(c[-1])
        if price > ama[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Price above Kaufman AMA", evidence={"ama": round(float(ama[-1]), 4)},
                factors=["technical", "kaufman_ama"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
            reasoning="Price below Kaufman AMA", evidence={"ama": round(float(ama[-1]), 4)},
            factors=["technical", "kaufman_ama"])
