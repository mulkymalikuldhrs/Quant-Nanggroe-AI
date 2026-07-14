from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class WilliamsRStrategy(BaseStrategy):
    """Williams R trading strategy.

    Detects the williams r candlestick pattern by computing
    technical indicators and generating trading signals.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="WilliamsR", params=params)
        self.period: int = int(self.params.get("period", 14))
        self.ob: float = float(self.params.get("ob", -20.0))
        self.os: float = float(self.params.get("os", -80.0))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        hh = data["high"].rolling(self.period).max()
        ll = data["low"].rolling(self.period).min()
        wr = -100 * (hh - data["close"]) / (hh - ll + 1e-10)
        val = float(wr.iloc[-1]) if not np.isnan(wr.iloc[-1]) else 0.0
        price = float(data["close"].iloc[-1])
        if val > self.ob:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Williams %R {val:.0f} overbought", evidence={"williams_r": round(val, 2)},
                factors=["technical", "williams_r"])
        if val < self.os:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Williams %R {val:.0f} oversold", evidence={"williams_r": round(val, 2)},
                factors=["technical", "williams_r"])
        return None

    def __str__(self) -> str:
        return f"WilliamsRStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

