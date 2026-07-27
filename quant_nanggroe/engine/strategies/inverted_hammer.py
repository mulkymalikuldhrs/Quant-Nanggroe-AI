"""Inverted Hammer — potential bullish reversal after downtrend."""

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
class InvertedHammerStrategy(Strategy):
    """Inverted Hammer — potential bullish reversal after downtrend."""

    name = "inverted_hammer"
    description = "Inverted hammer: bullish reversal after downtrend"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty or len(data) < 2:
                return self._hold("No or insufficient data")
            o, h, l, c = data["open"], data["high"], data["low"], data["close"]
            body = abs(c.iloc[-1] - o.iloc[-1])
            lower_wick = o.iloc[-1] - l.iloc[-1] if c.iloc[-1] > o.iloc[-1] else c.iloc[-1] - l.iloc[-1]
            upper_wick = h.iloc[-1] - c.iloc[-1] if c.iloc[-1] > o.iloc[-1] else h.iloc[-1] - o.iloc[-1]
            price = float(c.iloc[-1])
            if body > 0 and upper_wick > body * 2 and lower_wick < body * 0.5:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning="Inverted hammer: bullish reversal",
                    indicators={"upper_wick_ratio": round(float(upper_wick / (body + 1e-10)), 2)},
                )
            return self._hold("No inverted hammer pattern")
        except Exception as exc:
            logger.error("InvertedHammer error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["InvertedHammerStrategy"]
