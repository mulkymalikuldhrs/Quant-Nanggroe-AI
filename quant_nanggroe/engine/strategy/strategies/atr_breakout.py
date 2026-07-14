from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ATRBreakoutStrategy(BaseStrategy):
    """ATR breakout — volatility-adjusted breakout detection."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ATRBreakout", params=params)
        self.atr_period: int = int(self.params.get("atr_period", 14))
        self.lookback: int = int(self.params.get("lookback", 20))
        self.atr_mult: float = float(self.params.get("atr_mult", 2.0))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return max(self.atr_period, self.lookback) + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        h, l, c = data["high"], data["low"], data["close"]
        atr = self.compute_atr(h, l, c, self.atr_period)
        if np.isnan(atr.iloc[-1]):
            return None
        atr_val = float(atr.iloc[-1])
        highest = float(h.iloc[-self.lookback:].max())
        lowest = float(l.iloc[-self.lookback:].min())
        price = float(c.iloc[-1])
        if price > highest - atr_val * 0.5:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"ATR breakout: price near {self.lookback}-bar high",
                evidence={"atr": round(atr_val, 4), "high": round(highest, 4)},
                factors=["volatility", "atr_breakout"])
        if price < lowest + atr_val * 0.5:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"ATR breakdown: price near {self.lookback}-bar low",
                evidence={"atr": round(atr_val, 4), "low": round(lowest, 4)},
                factors=["volatility", "atr_breakout"])
        return None
