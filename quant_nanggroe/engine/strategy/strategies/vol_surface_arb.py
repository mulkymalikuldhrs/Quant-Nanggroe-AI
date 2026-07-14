from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class VolSurfaceArbStrategy(BaseStrategy):
    """Vol surface arbitrage proxy — skew between vol regimes."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VolSurfaceArb", params=params)
        self.fast: int = int(self.params.get("fast", 5))
        self.medium: int = int(self.params.get("medium", 20))
        self.slow: int = int(self.params.get("slow", 60))
        self.skew_threshold: float = float(self.params.get("skew_threshold", 0.2))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.slow + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"].values
        if len(c) < self.slow:
            return None
        rets = np.diff(np.log(c))
        v1 = np.std(rets[-self.fast:]) * np.sqrt(252)
        v2 = np.std(rets[-self.medium:]) * np.sqrt(252)
        v3 = np.std(rets[-self.slow:]) * np.sqrt(252)
        skew_short = (v1 - v2) / (v2 + 1e-10)
        skew_long = (v2 - v3) / (v3 + 1e-10)
        price = float(c[-1])
        if skew_short > self.skew_threshold and skew_long > self.skew_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Vol surface: upward skew across maturities",
                evidence={"skew_short": round(float(skew_short), 4), "skew_long": round(float(skew_long), 4)},
                factors=["volatility", "vol_surface"])
        if skew_short < -self.skew_threshold and skew_long < -self.skew_threshold:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Vol surface: downward skew across maturities",
                evidence={"skew_short": round(float(skew_short), 4), "skew_long": round(float(skew_long), 4)},
                factors=["volatility", "vol_surface"])
        return None
