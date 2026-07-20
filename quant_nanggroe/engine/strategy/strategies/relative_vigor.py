from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class RelativeVigorStrategy(BaseStrategy):
    """Relative Vigor Index — momentum via close vs open."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="RelativeVigor", params=params)
        self.period: int = int(self.params.get("period", 10))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        o, c = data["open"], data["close"]
        num = c - o
        den = c.shift(1) - o.shift(1)
        rvi_num = (num + 2 * num.shift(1) + 2 * num.shift(2) + num.shift(3)) / 6
        rvi_den = (den + 2 * den.shift(1) + 2 * den.shift(2) + den.shift(3)) / 6
        rvi = rvi_num.rolling(self.period).mean() / (rvi_den.rolling(self.period).mean().abs() + 1e-10)
        sig = rvi.rolling(4).mean()
        if np.isnan(rvi.iloc[-1]) or np.isnan(sig.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if rvi.iloc[-1] > sig.iloc[-1] and rvi.iloc[-2] <= sig.iloc[-2]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="RVI bullish crossover",
                evidence={"rvi": round(float(rvi.iloc[-1]), 4)}, factors=["technical", "rvi"])
        if rvi.iloc[-1] < sig.iloc[-1] and rvi.iloc[-2] >= sig.iloc[-2]:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="RVI bearish crossover",
                evidence={"rvi": round(float(rvi.iloc[-1]), 4)}, factors=["technical", "rvi"])
        return None
