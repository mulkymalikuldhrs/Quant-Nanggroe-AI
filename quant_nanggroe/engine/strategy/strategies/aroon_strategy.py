from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class AroonStrategy(BaseStrategy):
    """Aroon — trend strength and direction."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="AroonStrategy", params=params)
        self.period: int = int(self.params.get("period", 25))
        self.threshold: float = float(self.params.get("threshold", 70.0))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h, l, c = data["high"], data["low"], data["close"]
        h_period = h.rolling(self.period + 1)
        l_period = l.rolling(self.period + 1)
        aroon_up = ((self.period - h_period.apply(lambda x: x.argmax() if len(x) == self.period + 1 else np.nan, raw=True)) / self.period) * 100
        aroon_down = ((self.period - l_period.apply(lambda x: x.argmin() if len(x) == self.period + 1 else np.nan, raw=True)) / self.period) * 100
        if np.isnan(aroon_up.iloc[-1]):
            return None
        up, down = float(aroon_up.iloc[-1]), float(aroon_down.iloc[-1])
        price = float(c.iloc[-1])
        if up > self.threshold and up > down:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=min(up / 100, 1.0),
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Aroon up {up:.0f} > down {down:.0f}", evidence={"aroon_up": round(up, 2), "aroon_down": round(down, 2)},
                factors=["technical", "aroon"])
        if down > self.threshold and down > up:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=min(down / 100, 1.0),
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Aroon down {down:.0f} > up {up:.0f}", evidence={"aroon_up": round(up, 2), "aroon_down": round(down, 2)},
                factors=["technical", "aroon"])
        return None
