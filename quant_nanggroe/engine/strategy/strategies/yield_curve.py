from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class YieldCurveStrategy(BaseStrategy):
    """Yield curve — short vs long maturity momentum as steepness proxy."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="YieldCurve", params=params)
        self.short_lookback: int = int(self.params.get("short_lookback", 20))
        self.long_lookback: int = int(self.params.get("long_lookback", 100))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.long_lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        short_ret = float(c.iloc[-1]) / float(c.iloc[-self.short_lookback]) - 1.0
        long_ret = float(c.iloc[-1]) / float(c.iloc[-self.long_lookback]) - 1.0
        steepness = short_ret - long_ret
        price = float(c.iloc[-1])
        if steepness > 0.02:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Yield curve steepening: short {short_ret:.2%} > long {long_ret:.2%}",
                evidence={"steepness": round(float(steepness), 4), "short_ret": round(float(short_ret), 4), "long_ret": round(float(long_ret), 4)},
                factors=["macro", "yield_curve"])
        if steepness < -0.02:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Yield curve flattening: short {short_ret:.2%} < long {long_ret:.2%}",
                evidence={"steepness": round(float(steepness), 4), "short_ret": round(float(short_ret), 4), "long_ret": round(float(long_ret), 4)},
                factors=["macro", "yield_curve"])
        return None

