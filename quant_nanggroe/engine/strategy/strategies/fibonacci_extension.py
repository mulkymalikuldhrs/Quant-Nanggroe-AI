"""Fibonacci Extension strategy."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class FibonacciExtensionStrategy(BaseStrategy):
    """Fibonacci extension levels for profit targets.

    Projects 1.272/1.382/1.5/1.618 extensions from prior swing.
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="FibonacciExtension", params=params)
        self.lookback: int = int(self.params.get("lookback", 50))
        self.ext_levels: List[float] = self.params.get("ext_levels", [1.272, 1.382, 1.5, 1.618])

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

        swing_high = float(high.iloc[-self.lookback:].max())
        swing_low = float(low.iloc[-self.lookback:].min())
        diff = swing_high - swing_low
        if diff == 0:
            return None

        # Trend direction
        trend_up = float(close.iloc[-1]) > float(close.iloc[-self.lookback // 2])
        base = swing_low if trend_up else swing_high

        for ext in self.ext_levels:
            target = base + diff * ext if trend_up else base - diff * ext
            proximity = abs(price - target) / diff
            if proximity < 0.03:
                sig = -1.0 if trend_up else 1.0
                return Signal(
                    symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                    confidence=0.7, price=round(price, 6), source_agent=self.name,
                    source_strategy=self.name,
                    reasoning=f"Price at Fib extension {ext:.3f}, reversal expected",
                    evidence={"extension": ext, "target": round(target, 4)},
                    factors=["fibonacci", "extension"],
                )
        return None
