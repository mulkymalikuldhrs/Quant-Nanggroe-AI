from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class WoodiePivotStrategy(BaseStrategy):
    """Woodie pivot points — different formula from classic."""


    def __init__(self, params=None):
        super().__init__(name="WoodiePivotStrategy", params=params)
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
        o = float(data["open"].iloc[-2])
        pp = (h + l + 2 * c) / 4
        r1 = 2 * pp - l
        s1 = 2 * pp - h
        price = float(data["close"].iloc[-1])
        if price < s1:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Woodie: price below S1 {s1:.4f}",
                evidence={"pivot": round(pp, 4), "s1": round(s1, 4), "r1": round(r1, 4)},
                factors=["technical", "woodie"])
        if price > r1:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Woodie: price above R1 {r1:.4f}",
                evidence={"pivot": round(pp, 4), "s1": round(s1, 4), "r1": round(r1, 4)},
                factors=["technical", "woodie"])
        return None
