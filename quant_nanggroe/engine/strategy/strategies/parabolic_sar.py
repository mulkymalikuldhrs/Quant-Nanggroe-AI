from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ParabolicSARStrategy(BaseStrategy):
    """Parabolic SAR — trend direction and reversal."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ParabolicSAR", params=params)
        self.af_start: float = float(self.params.get("af_start", 0.02))
        self.af_step: float = float(self.params.get("af_step", 0.02))
        self.af_max: float = float(self.params.get("af_max", 0.20))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return 50

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 5:
            return None
        h, l, c = data["high"].values, data["low"].values, data["close"].values
        n = len(h)
        sar = np.empty(n)
        af = self.af_start
        trend = 1 if c[1] > c[0] else -1
        ep = h[1] if trend == 1 else l[1]
        sar[0] = sar[1] = l[0] if trend == 1 else h[0]
        for i in range(2, n):
            sar[i] = sar[i-1] + af * (ep - sar[i-1])
            if trend == 1:
                sar[i] = min(sar[i], l[i-2], l[i-1])
                if h[i] > ep:
                    ep = h[i]
                    af = min(af + self.af_step, self.af_max)
                if l[i] < sar[i]:
                    trend = -1
                    sar[i] = ep
                    ep = l[i]
                    af = self.af_start
            else:
                sar[i] = max(sar[i], h[i-2], h[i-1])
                if l[i] < ep:
                    ep = l[i]
                    af = min(af + self.af_step, self.af_max)
                if h[i] > sar[i]:
                    trend = 1
                    sar[i] = ep
                    ep = h[i]
                    af = self.af_start
        price = float(c[-1])
        if trend == 1 and c[-1] > sar[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Parabolic SAR bullish", evidence={"sar": round(float(sar[-1]), 4)},
                factors=["technical", "parabolic_sar"])
        if trend == -1 and c[-1] < sar[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Parabolic SAR bearish", evidence={"sar": round(float(sar[-1]), 4)},
                factors=["technical", "parabolic_sar"])
        return None
