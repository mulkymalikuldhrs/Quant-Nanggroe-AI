"""Engulfing pattern — strong reversal candlestick pattern."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class EngulfingPatternStrategy(Strategy):
    """Engulfing pattern — strong reversal candlestick pattern."""

    name = "engulfing_pattern"
    description = "Engulfing: bullish/bearish reversal candlestick"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty or len(data) < 2:
                return self._hold("No or insufficient data")
            o, c = data["open"], data["close"]
            prev_red = c.iloc[-2] < o.iloc[-2]
            cur_green = c.iloc[-1] > o.iloc[-1]
            engulfs_up = o.iloc[-1] < c.iloc[-2] and c.iloc[-1] > o.iloc[-2]
            if prev_red and cur_green and engulfs_up:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.65,
                    entry_price=round(float(c.iloc[-1]), 6),
                    reasoning="Bullish engulfing pattern",
                    indicators={},
                )
            prev_green = c.iloc[-2] > o.iloc[-2]
            cur_red = c.iloc[-1] < o.iloc[-1]
            engulfs_down = o.iloc[-1] > c.iloc[-2] and c.iloc[-1] < o.iloc[-2]
            if prev_green and cur_red and engulfs_down:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.65,
                    entry_price=round(float(c.iloc[-1]), 6),
                    reasoning="Bearish engulfing pattern",
                    indicators={},
                )
            return self._hold("No engulfing pattern")
        except Exception as exc:
            logger.error("EngulfingPattern error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["EngulfingPatternStrategy"]
