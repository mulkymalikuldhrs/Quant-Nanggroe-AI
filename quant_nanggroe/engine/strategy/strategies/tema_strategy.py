from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class TEMAStrategy(BaseStrategy):
    """T E M A trading strategy.

    Detects the t e m a candlestick pattern by computing
    technical indicators and generating trading signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="TEMAStrategy", params=params)
        self.period: int = int(self.params.get("period", 20))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period * 5 + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < self.period * 5:
            return None
        c = data["close"]
        ema1 = self.compute_ema(c, self.period)
        ema2 = self.compute_ema(ema1, self.period)
        ema3 = self.compute_ema(ema2, self.period)
        tema = 3 * ema1 - 3 * ema2 + ema3
        if np.isnan(tema.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if price > tema.iloc[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Price above TEMA", evidence={"tema": round(float(tema.iloc[-1]), 4)},
                factors=["technical", "tema"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
            reasoning="Price below TEMA", evidence={"tema": round(float(tema.iloc[-1]), 4)},
            factors=["technical", "tema"])

    def __str__(self) -> str:
        return f"TEMAStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

