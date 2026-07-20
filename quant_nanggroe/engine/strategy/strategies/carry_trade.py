from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class CarryTradeStrategy(BaseStrategy):
    """Carry Trade trading strategy.

    Detects the carry trade candlestick pattern by comparing
    short-term and long-term momentum to proxy carry trade dynamics.
    """


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="CarryTrade", params=params)
        self.lookback: int = int(self.params.get("lookback", 21))
        self.carry_threshold: float = float(self.params.get("carry_threshold", 0.02))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        rets = close.pct_change().iloc[-self.lookback:]
        if len(rets) < 5:
            return None
        avg_ret = float(rets.mean())
        price = float(close.iloc[-1])
        if avg_ret > self.carry_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Carry long: avg return {avg_ret:.4f} > {self.carry_threshold}",
                evidence={"avg_return": round(avg_ret, 4)}, factors=["hedge_fund", "carry"])
        if avg_ret < -self.carry_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Carry short: avg return {avg_ret:.4f} < {-self.carry_threshold}",
                evidence={"avg_return": round(avg_ret, 4)}, factors=["hedge_fund", "carry"])
        return None

    def __str__(self) -> str:
        return f"CarryTradeStrategy()"

    def __repr__(self) -> str:
        return self.__str__()

