from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class KalmanFilterStrategy(BaseStrategy):
    """Kalman filter — state estimation for trend."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="KalmanFilter", params=params)
        self.r: float = float(self.params.get("r", 1e-4))
        self.q: float = float(self.params.get("q", 1e-4))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return 20

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 20:
            return None
        c = data["close"].values
        n = len(c)
        x = np.zeros(n)
        p = np.zeros(n)
        x[0] = c[0]
        p[0] = 1.0
        for i in range(1, n):
            x[i] = x[i-1]
            p[i] = p[i-1] + self.q
            k = p[i] / (p[i] + self.r)
            x[i] = x[i] + k * (c[i] - x[i])
            p[i] = (1 - k) * p[i]
        price = float(c[-1])
        if price > x[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Kalman: price above state estimate",
                evidence={"kf_state": round(float(x[-1]), 4)}, factors=["ml", "kalman"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
            price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
            reasoning="Kalman: price below state estimate",
            evidence={"kf_state": round(float(x[-1]), 4)}, factors=["ml", "kalman"])
