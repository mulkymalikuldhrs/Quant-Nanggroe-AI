"""Doji candle pattern — indecision / potential reversal."""

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
class DojiPatternStrategy(Strategy):
    """Doji candle pattern — indecision / potential reversal."""

    name = "doji_pattern"
    description = "Doji candle: indecision and potential reversal"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.threshold: float = float(self._parameters.get("threshold", 0.03))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty or len(data) < 2:
                return self._hold("No or insufficient data")
            o, c = data["open"], data["close"]
            price = float(c.iloc[-1])
            body = abs(c.iloc[-1] - o.iloc[-1])
            candle_range = float(data["high"].iloc[-1] - data["low"].iloc[-1])
            if candle_range > 0 and body / candle_range < self.threshold:
                if c.iloc[-1] > o.iloc[-2]:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning="Doji after green candle, potential reversal",
                        indicators={"body_ratio": round(float(body / candle_range), 4)},
                    )
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning="Doji after red candle, potential reversal",
                    indicators={"body_ratio": round(float(body / candle_range), 4)},
                )
            return self._hold("No doji pattern")
        except Exception as exc:
            logger.error("DojiPattern error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["DojiPatternStrategy"]
