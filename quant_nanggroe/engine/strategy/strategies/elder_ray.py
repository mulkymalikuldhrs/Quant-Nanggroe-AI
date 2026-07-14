from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ElderRayStrategy(BaseStrategy):
    """Elder Ray Index — bull/bear power."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ElderRay", params=params)
        self.period: int = int(self.params.get("period", 13))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        ema = self.compute_ema(data["close"], self.period)
        bull = data["high"] - ema
        bear = data["low"] - ema
        if np.isnan(bull.iloc[-1]):
            return None
        price = float(data["close"].iloc[-1])
        bv, bv2 = float(bull.iloc[-1]), float(bull.iloc[-2])
        bv_, bv2_ = float(bear.iloc[-1]), float(bear.iloc[-2])
        if bv > 0 and bv > bv2:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Elder Ray: bull power rising",
                evidence={"bull_power": round(bv, 4), "bear_power": round(bv_, 4)},
                factors=["technical", "elder_ray"])
        if bv_ < 0 and bv_ < bv2_:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Elder Ray: bear power falling",
                evidence={"bull_power": round(bv, 4), "bear_power": round(bv_, 4)},
                factors=["technical", "elder_ray"])
        return None
