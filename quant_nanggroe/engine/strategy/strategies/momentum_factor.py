from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MomentumFactorStrategy(BaseStrategy):
    """Momentum Factor trading strategy.

    Detects the momentum factor candlestick pattern by computing
    the relevant cross-sectional factor return and generating
    long/short signals based on factor score.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MomentumFactor", params=params)
        self.lookback: int = int(self.params.get("lookback", 126))
        self.top_pct: float = float(self.params.get("top_pct", 0.3))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        ret = float(close.iloc[-1]) / float(close.iloc[-self.lookback]) - 1.0
        price = float(close.iloc[-1])
        if ret > self.top_pct:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=min(ret * 2, 1.0),
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Momentum factor: return {ret:.2%}, long",
                evidence={"momentum_return": round(float(ret), 4)}, factors=["hedge_fund", "momentum_factor"])
        if ret < -self.top_pct:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=min(abs(ret) * 2, 1.0),
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Momentum factor: return {ret:.2%}, short",
                evidence={"momentum_return": round(float(ret), 4)}, factors=["hedge_fund", "momentum_factor"])
        return None

    def __str__(self) -> str:
        return f"MomentumFactorStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

