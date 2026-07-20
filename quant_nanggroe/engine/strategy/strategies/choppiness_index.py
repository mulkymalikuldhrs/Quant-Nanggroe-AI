from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ChoppinessIndexStrategy(BaseStrategy):
    """Choppiness Index trading strategy.

    Detects the choppiness index candlestick pattern by computing
    technical indicators and generating trading signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ChoppinessIndex", params=params)
        self.period: int = int(self.params.get("period", 14))
        self.trend_threshold: float = float(self.params.get("trend_threshold", 38.0))
        self.choppy_threshold: float = float(self.params.get("choppy_threshold", 62.0))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr_sum = tr.rolling(self.period).sum()
        hh = h.rolling(self.period).max()
        ll = l.rolling(self.period).min()
        ci = 100 * np.log(atr_sum / (hh - ll + 1e-10)) / np.log(self.period)
        val = float(ci.iloc[-1]) if not np.isnan(ci.iloc[-1]) else 50.0
        price = float(c.iloc[-1])
        if val < self.trend_threshold:
            ret = float(c.iloc[-1]) / float(c.iloc[-int(self.period/2)]) - 1.0
            sig = 1.0 if ret > 0 else -1.0
            return Signal(symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                confidence=0.6, price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Choppiness {val:.0f} < {self.trend_threshold}: trending",
                evidence={"choppiness": round(val, 2)}, factors=["technical", "choppiness"])
        return None

    def __str__(self) -> str:
        return f"ChoppinessIndexStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

