"""Fibonacci Fan strategy."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class FibonacciFanStrategy(BaseStrategy):
    """Fibonacci fan lines for trend angle support/resistance.

    Fan lines at 38.2%, 50%, 61.8% from a major trend move.
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="FibonacciFan", params=params)
        self.lookback: int = int(self.params.get("lookback", 60))
        self.fan_levels: List[float] = self.params.get("fan_levels", [0.382, 0.5, 0.618])

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        high = data["high"]
        low = data["low"]
        close = data["close"]
        price = float(close.iloc[-1])

        first_half = data.iloc[:len(data)//2]
        second_half = data.iloc[len(data)//2:]
        h1_high = float(first_half["high"].max())
        h1_low = float(first_half["low"].min())
        h2_low = float(second_half["low"].min())
        h2_high = float(second_half["high"].max())
        trend_range = h1_high - h1_low
        if trend_range == 0:
            return None

        fan_up = h1_low + trend_range * np.array(self.fan_levels)
        fan_down = h1_high - trend_range * np.array(self.fan_levels)

        for i, level in enumerate(self.fan_levels):
            if abs(price - fan_up[i]) / trend_range < 0.02:
                return Signal(
                    symbol=self.name, signal_type=SignalType.BUY,
                    confidence=0.65 - i * 0.05, price=round(price, 6),
                    source_agent=self.name, source_strategy=self.name,
                    reasoning=f"Price at fan support {level:.1%}",
                    evidence={"fan_level": level}, factors=["fibonacci", "fan"],
                )
            if abs(price - fan_down[i]) / trend_range < 0.02:
                return Signal(
                    symbol=self.name, signal_type=SignalType.SELL,
                    confidence=0.65 - i * 0.05, price=round(price, 6),
                    source_agent=self.name, source_strategy=self.name,
                    reasoning=f"Price at fan resistance {level:.1%}",
                    evidence={"fan_level": level}, factors=["fibonacci", "fan"],
                )
        return None
