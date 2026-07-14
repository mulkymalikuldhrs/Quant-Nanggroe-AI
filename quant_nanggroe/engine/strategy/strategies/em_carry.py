from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class EMCarryStrategy(BaseStrategy):
    """E M Carry trading strategy.

    Detects the e m carry candlestick pattern by comparing
    short-term and long-term momentum to proxy carry trade dynamics.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="EMCarry", params=params)
        self.lookback: int = int(self.params.get("lookback", 21))
        self.carry_threshold: float = float(self.params.get("carry_threshold", 0.015))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        rets = c.pct_change().iloc[-self.lookback:]
        avg_ret = float(rets.mean())
        price = float(c.iloc[-1])
        if avg_ret > self.carry_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=min(avg_ret * 20, 1.0),
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"EM carry positive: avg {avg_ret:.4f}",
                evidence={"avg_return": round(float(avg_ret), 4)}, factors=["macro", "em_carry"])
        if avg_ret < -self.carry_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=min(abs(avg_ret) * 20, 1.0),
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"EM carry negative: avg {avg_ret:.4f}",
                evidence={"avg_return": round(float(avg_ret), 4)}, factors=["macro", "em_carry"])
        return None

    def __str__(self) -> str:
        return f"EMCarryStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

