from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class StochasticOscillatorStrategy(BaseStrategy):
    """Stochastic oscillator %K/%D crossover."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="StochasticOscillator", params=params)
        self.k_period: int = int(self.params.get("k_period", 14))
        self.d_period: int = int(self.params.get("d_period", 3))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.k_period + self.d_period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        hh = data["high"].rolling(self.k_period).max()
        ll = data["low"].rolling(self.k_period).min()
        k = 100 * (data["close"] - ll) / (hh - ll + 1e-10)
        d = k.rolling(self.d_period).mean()
        if np.isnan(k.iloc[-1]):
            return None
        price = float(data["close"].iloc[-1])
        if k.iloc[-1] < 20 and k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Stochastic bullish crossover", evidence={"k": round(float(k.iloc[-1]), 2), "d": round(float(d.iloc[-1]), 2)},
                factors=["technical", "stochastic"])
        if k.iloc[-1] > 80 and k.iloc[-1] < d.iloc[-1] and k.iloc[-2] >= d.iloc[-2]:
            return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.55,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Stochastic bearish crossover", evidence={"k": round(float(k.iloc[-1]), 2), "d": round(float(d.iloc[-1]), 2)},
                factors=["technical", "stochastic"])
        return None

