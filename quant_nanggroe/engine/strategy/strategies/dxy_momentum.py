from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class DXYMomentumStrategy(BaseStrategy):
    """D X Y Momentum trading strategy.

    Detects the d x y momentum candlestick pattern by tracking
    dollar momentum regime for macro FX positioning.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="DXYMomentum", params=params)
        self.lookback: int = int(self.params.get("lookback", 63))
        self.threshold: float = float(self.params.get("threshold", 0.03))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        ret = float(c.iloc[-1]) / float(c.iloc[-self.lookback]) - 1.0
        price = float(c.iloc[-1])
        if ret > self.threshold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=min(ret / 0.1, 1.0),
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"DXY momentum bullish: {ret:.2%}",
                evidence={"momentum": round(float(ret), 4)}, factors=["macro", "dxy"])
        if ret < -self.threshold:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=min(abs(ret) / 0.1, 1.0),
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"DXY momentum bearish: {ret:.2%}",
                evidence={"momentum": round(float(ret), 4)}, factors=["macro", "dxy"])
        return None

    def __str__(self) -> str:
        return f"DXYMomentumStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

