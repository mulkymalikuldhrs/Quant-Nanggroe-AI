from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class TRIXStrategy(BaseStrategy):
    """TRIX — triple-smoothed EMA percentage change."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="TRIXStrategy", params=params)
        self.period: int = int(self.params.get("period", 18))
        self.signal_period: int = int(self.params.get("signal_period", 9))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period * 4 + self.signal_period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < self.warmup_period():
            return None
        c = data["close"]
        e1 = self.compute_ema(c, self.period)
        e2 = self.compute_ema(e1, self.period)
        e3 = self.compute_ema(e2, self.period)
        trix = e3.pct_change() * 100
        sig = trix.rolling(self.signal_period).mean()
        if np.isnan(trix.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if trix.iloc[-1] > sig.iloc[-1] and trix.iloc[-2] <= sig.iloc[-2]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="TRIX bullish crossover",
                evidence={"trix": round(float(trix.iloc[-1]), 4), "sig": round(float(sig.iloc[-1]), 4)},
                factors=["technical", "trix"])
        if trix.iloc[-1] < sig.iloc[-1] and trix.iloc[-2] >= sig.iloc[-2]:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="TRIX bearish crossover",
                evidence={"trix": round(float(trix.iloc[-1]), 4), "sig": round(float(sig.iloc[-1]), 4)},
                factors=["technical", "trix"])
        return None
