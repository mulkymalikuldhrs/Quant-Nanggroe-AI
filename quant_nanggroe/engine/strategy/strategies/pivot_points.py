from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class PivotPointsStrategy(BaseStrategy):
    """Classic pivot points for support/resistance levels."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="PivotPoints", params=params)
        self.lookback: int = int(self.params.get("lookback", 1))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return max(self.lookback + 1, 5)

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h = data["high"].iloc[-self.lookback-1:-1]
        l = data["low"].iloc[-self.lookback-1:-1]
        c = data["close"].iloc[-self.lookback-1:-1]
        hp, lp, cp = float(h.max()), float(l.min()), float(c.iloc[-1])
        pp = (hp + lp + cp) / 3
        r1 = 2 * pp - lp
        s1 = 2 * pp - hp
        price = float(data["close"].iloc[-1])
        if price < s1:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Price below pivot S1 {s1:.4f}", evidence={"pivot": round(pp, 4), "s1": round(s1, 4), "r1": round(r1, 4)},
                factors=["technical", "pivot_points"])
        if price > r1:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Price above pivot R1 {r1:.4f}", evidence={"pivot": round(pp, 4), "s1": round(s1, 4), "r1": round(r1, 4)},
                factors=["technical", "pivot_points"])
        return None

