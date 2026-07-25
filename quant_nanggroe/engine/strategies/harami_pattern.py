"""Harami Pattern — reversal candlestick pattern (inside bar)."""

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
class HaramiPatternStrategy(Strategy):
    """Harami Pattern — reversal candlestick inside bar pattern."""

    name = "harami_pattern"
    description = "Harami: bullish/bearish inside-bar reversal"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty or len(data) < 2:
                return self._hold("No or insufficient data")
            o, c = data["open"], data["close"]
            prev_green = c.iloc[-2] > o.iloc[-2]
            cur_inside = c.iloc[-1] < o.iloc[-2] and o.iloc[-1] > c.iloc[-2]
            price = float(c.iloc[-1])
            if prev_green and cur_inside and c.iloc[-1] > o.iloc[-1]:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning="Bearish harami pattern",
                    indicators={},
                )
            prev_red = c.iloc[-2] < o.iloc[-2]
            if prev_red and cur_inside and c.iloc[-1] < o.iloc[-1]:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning="Bullish harami pattern",
                    indicators={},
                )
            return self._hold("No harami pattern")
        except Exception as exc:
            logger.error("HaramiPattern error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["HaramiPatternStrategy"]
