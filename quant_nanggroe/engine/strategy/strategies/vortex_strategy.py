from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class VortexStrategy(BaseStrategy):
    """Vortex indicator — trend direction via positive/negative VI."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VortexStrategy", params=params)
        self.period: int = int(self.params.get("period", 14))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        vm_plus = (h - l.shift()).abs().rolling(self.period).sum()
        vm_minus = (l - h.shift()).abs().rolling(self.period).sum()
        tr_sum = tr.rolling(self.period).sum()
        vi_plus = vm_plus / (tr_sum + 1e-10)
        vi_minus = vm_minus / (tr_sum + 1e-10)
        if np.isnan(vi_plus.iloc[-1]):
            return None
        price = float(c.iloc[-1])
        if vi_plus.iloc[-1] > vi_minus.iloc[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="Vortex bullish VI+ > VI-",
                evidence={"vi_plus": round(float(vi_plus.iloc[-1]), 4), "vi_minus": round(float(vi_minus.iloc[-1]), 4)},
                factors=["technical", "vortex"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name, source_strategy=self.name,
            reasoning="Vortex bearish VI- > VI+",
            evidence={"vi_plus": round(float(vi_plus.iloc[-1]), 4), "vi_minus": round(float(vi_minus.iloc[-1]), 4)},
            factors=["technical", "vortex"])
