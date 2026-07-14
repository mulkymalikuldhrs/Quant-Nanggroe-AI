from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class LinearRegressionChannelStrategy(BaseStrategy):
    """Linear regression channel — trend direction + deviation."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="LinearRegressionChannel", params=params)
        self.period: int = int(self.params.get("period", 50))
        self.std_mult: float = float(self.params.get("std_mult", 2.0))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"].values[-self.period:]
        if len(c) < self.period:
            return None
        x = np.arange(len(c))
        slope, intercept = np.polyfit(x, c, 1)
        trend = intercept + slope * x
        resid = c - trend
        std = np.std(resid)
        price = float(c[-1])
        z = float(resid[-1] / (std + 1e-10))
        if z > self.std_mult:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min(z / (self.std_mult * 2), 1.0), price=round(price, 6),
                source_agent=self.name, source_strategy=self.name,
                reasoning=f"Price {z:.2f} std above regression channel",
                evidence={"zscore": round(z, 3), "slope": round(float(slope), 6)},
                factors=["ml", "linear_regression"])
        if z < -self.std_mult:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=min(abs(z) / (self.std_mult * 2), 1.0), price=round(price, 6),
                source_agent=self.name, source_strategy=self.name,
                reasoning=f"Price {abs(z):.2f} std below regression channel",
                evidence={"zscore": round(z, 3), "slope": round(float(slope), 6)},
                factors=["ml", "linear_regression"])
        return None
