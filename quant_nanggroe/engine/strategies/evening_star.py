"""Evening Star — bearish reversal candlestick pattern."""

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
class EveningStarStrategy(Strategy):
    """Evening Star — bearish reversal candle pattern."""

    name = "evening_star"
    description = "Evening star: bearish reversal candlestick pattern"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty or len(data) < 3:
                return self._hold("No or insufficient data")
            o, c = data["open"], data["close"]
            c1, c2, c3 = c.iloc[-3], c.iloc[-2], c.iloc[-1]
            o1 = o.iloc[-2]
            price = float(c3)
            if c.iloc[-3] > o.iloc[-3] and abs(c1 - o.iloc[-3]) > 0:
                body2 = abs(c2 - o1) / (c1 - o.iloc[-3])
                if body2 < 0.3 and c3 < o1:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        confidence=0.6,
                        entry_price=round(price, 6),
                        reasoning="Evening star pattern",
                        indicators={},
                    )
            return self._hold("No evening star pattern")
        except Exception as exc:
            logger.error("EveningStar error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["EveningStarStrategy"]
