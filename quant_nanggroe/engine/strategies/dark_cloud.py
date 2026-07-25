"""Dark Cloud Cover — bearish candlestick reversal pattern."""

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
class DarkCloudCoverStrategy(Strategy):
    """Dark Cloud Cover — bearish candlestick reversal pattern."""

    name = "dark_cloud_cover"
    description = "Dark cloud cover candlestick reversal pattern"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty or len(data) < 2:
                return self._hold("No or insufficient data")
            o, c = data["open"], data["close"]
            prev_bull = c.iloc[-2] > o.iloc[-2]
            cur_bear = c.iloc[-1] < o.iloc[-1]
            mid_prev = (c.iloc[-2] + o.iloc[-2]) / 2
            covers = c.iloc[-1] < mid_prev and o.iloc[-1] > o.iloc[-2]
            if prev_bull and cur_bear and covers:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.6,
                    entry_price=round(float(c.iloc[-1]), 6),
                    reasoning="Dark cloud cover pattern",
                    indicators={},
                )
            return self._hold("No dark cloud pattern")
        except Exception as exc:
            logger.error("DarkCloudCover error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["DarkCloudCoverStrategy"]
