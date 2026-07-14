from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class OBVStrategy(BaseStrategy):
    """O B V trading strategy.

    Detects the o b v candlestick pattern by computing
    technical indicators and generating trading signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="OBVStrategy", params=params)
        self.lookback: int = int(self.params.get("lookback", 20))

    def required_columns(self) -> List[str]:
        return ["close", "volume"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c, v = data["close"], data["volume"]
        direction = np.sign(c.diff()).fillna(0)
        obv = (direction * v).cumsum()
        obv_sma = obv.rolling(self.lookback).mean()
        price = float(c.iloc[-1])
        if np.isnan(obv_sma.iloc[-1]):
            return None
        if obv.iloc[-1] > obv_sma.iloc[-1] and c.iloc[-1] > c.iloc[-5]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="OBV bullish divergence", evidence={}, factors=["technical", "obv"])
        if obv.iloc[-1] < obv_sma.iloc[-1] and c.iloc[-1] < c.iloc[-5]:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="OBV bearish divergence", evidence={}, factors=["technical", "obv"])
        return None

    def __str__(self) -> str:
        return f"OBVStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

