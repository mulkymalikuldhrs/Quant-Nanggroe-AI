from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class DEMAStrategy(BaseStrategy):
    """D E M A trading strategy.

    Detects the d e m a candlestick pattern by computing
    technical indicators and generating trading signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="DEMAStrategy", params=params)
        self.period: int = int(self.params.get("period", 20))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period * 3 + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < self.period * 3:
            return None
        c = data["close"]
        ema1 = self.compute_ema(c, self.period)
        ema2 = self.compute_ema(ema1, self.period)
        dema = 2 * ema1 - ema2
        if np.isnan(dema.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if price > dema.iloc[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Price above DEMA", evidence={"dema": round(float(dema.iloc[-1]), 4)},
                factors=["technical", "dema"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name, source_strategy=self.name,
            reasoning="Price below DEMA", evidence={"dema": round(float(dema.iloc[-1]), 4)},
            factors=["technical", "dema"])

    def __str__(self) -> str:
        return f"DEMAStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

