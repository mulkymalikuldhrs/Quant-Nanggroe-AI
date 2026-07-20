from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class T3Strategy(BaseStrategy):
    """T3 moving average — smoother EMA variant."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="T3Strategy", params=params)
        self.period: int = int(self.params.get("period", 8))
        self.vfactor: float = float(self.params.get("vfactor", 0.7))

    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period * 6 + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < self.period * 6:
            return None
        c = data["close"]
        e1 = self._ema(c, self.period)
        e2 = self._ema(e1, self.period)
        e3 = self._ema(e2, self.period)
        e4 = self._ema(e3, self.period)
        e5 = self._ema(e4, self.period)
        e6 = self._ema(e5, self.period)
        c1 = -self.vfactor ** 3
        c2 = 3 * self.vfactor ** 2 + 3 * self.vfactor ** 3
        c3 = -6 * self.vfactor ** 2 - 3 * self.vfactor - 3 * self.vfactor ** 3
        c4 = 1 + 3 * self.vfactor + self.vfactor ** 3 + 3 * self.vfactor ** 2
        t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
        price = float(c.iloc[-1])
        if np.isnan(t3.iloc[-1]):
            return None
        if price > t3.iloc[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Price above T3 MA", evidence={"t3": round(float(t3.iloc[-1]), 4)},
                factors=["technical", "t3"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
            reasoning="Price below T3 MA", evidence={"t3": round(float(t3.iloc[-1]), 4)},
            factors=["technical", "t3"])
