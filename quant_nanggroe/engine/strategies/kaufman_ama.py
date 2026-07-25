"""Kaufman Adaptive Moving Average — responds to noise level."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class KaufmanAMAStrategy(Strategy):
    """Kaufman AMA — responds to noise level."""

    name = "kaufman_ama"
    description = "Kaufman AMA: adaptive moving average"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 14))
        self.fast: int = int(self._parameters.get("fast", 2))
        self.slow: int = int(self._parameters.get("slow", 30))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"].values
            if len(c) < self.period + 10:
                return self._hold("Insufficient data")
            n = len(c)
            ama = np.zeros(n)
            ama[0] = c[0]
            fast_w = 2.0 / (self.fast + 1)
            slow_w = 2.0 / (self.slow + 1)
            for t in range(self.period, n):
                direction = abs(c[t] - c[t - self.period])
                vol = sum(abs(c[i] - c[i - 1]) for i in range(t - self.period + 1, t + 1))
                er = direction / (vol + 1e-10)
                sc = (er * (fast_w - slow_w) + slow_w) ** 2
                ama[t] = ama[t - 1] + sc * (c[t] - ama[t - 1])
            price = float(c[-1])
            if price > ama[-1]:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning="Price above Kaufman AMA (bullish)",
                    indicators={"kama": round(float(ama[-1]), 4)},
                )
            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=SignalDirection.SELL,
                confidence=0.5,
                entry_price=round(price, 6),
                reasoning="Price below Kaufman AMA (bearish)",
                indicators={"kama": round(float(ama[-1]), 4)},
            )
        except Exception as exc:
            logger.error("KaufmanAMA error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["KaufmanAMAStrategy"]
