from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class AdaptiveMovingAverageStrategy(BaseStrategy):
    """Adaptive MA — adjusts to market volatility."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="AdaptiveMovingAverage", params=params)
        self.period: int = int(self.params.get("period", 10))
        self.min_period: int = int(self.params.get("min_period", 2))
        self.max_period: int = int(self.params.get("max_period", 30))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.max_period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"]
        rets = c.pct_change().dropna().values[-self.max_period * 2:]
        if len(rets) < self.max_period:
            return None
        vol = np.std(rets)
        vol_rank = np.clip(vol / (np.mean(np.abs(rets)) + 1e-10), 0, 1)
        adaptive_period = int(self.max_period - (self.max_period - self.min_period) * vol_rank)
        adaptive_period = max(adaptive_period, self.min_period)
        ama = self.compute_sma(c, adaptive_period)
        if np.isnan(ama.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if price > ama.iloc[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"Price above adaptive MA ({adaptive_period})",
                evidence={"adaptive_period": adaptive_period, "ama": round(float(ama.iloc[-1]), 4)},
                factors=["ml", "adaptive_ma"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name, source_strategy=self.name,
            reasoning=f"Price below adaptive MA ({adaptive_period})",
            evidence={"adaptive_period": adaptive_period, "ama": round(float(ama.iloc[-1]), 4)},
            factors=["ml", "adaptive_ma"])
