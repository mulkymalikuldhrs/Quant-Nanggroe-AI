from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class CamarillaPivotStrategy(BaseStrategy):
    """Camarilla Pivot trading strategy.

    Detects the camarilla pivot candlestick pattern by calculating
    support/resistance levels from recent price action and
    generating reversal signals at key levels.
    """



    def __init__(self, params=None):
        super().__init__(name="CamarillaPivotStrategy", params=params)
    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h = float(data["high"].iloc[-2])
        l = float(data["low"].iloc[-2])
        c = float(data["close"].iloc[-2])
        r = h - l
        h8 = c + r * 1.0030
        l8 = c - r * 1.0030
        price = float(data["close"].iloc[-1])
        if price >= h8:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Price at Camarilla H8 {h8:.4f}", evidence={"h8": round(h8, 4), "l8": round(l8, 4), "range": round(r, 4)},
                factors=["technical", "camarilla"])
        if price <= l8:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Price at Camarilla L8 {l8:.4f}", evidence={"h8": round(h8, 4), "l8": round(l8, 4), "range": round(r, 4)},
                factors=["technical", "camarilla"])
        return None

    def __str__(self) -> str:
        return f"CamarillaPivotStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

