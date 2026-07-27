"""Fibonacci Retracement — support/resistance at retracement levels."""

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
class FibonacciRetracementStrategy(Strategy):
    """Fibonacci Retracement — support/resistance at retracement levels."""

    name = "fibonacci_retracement"
    description = "Fibonacci retracement: support/resistance levels"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 50))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.lookback + 5:
                return self._hold("Insufficient data")
            window_h = h.iloc[-self.lookback:]
            window_l = l.iloc[-self.lookback:]
            hh = float(window_h.max())
            ll = float(window_l.min())
            price = float(c.iloc[-1])
            diff = hh - ll
            levels = {
                0.236: hh - 0.236 * diff,
                0.382: hh - 0.382 * diff,
                0.5: hh - 0.5 * diff,
                0.618: hh - 0.618 * diff,
                0.786: hh - 0.786 * diff,
            }
            for lvl, price_lvl in levels.items():
                dist = abs(price - price_lvl) / (diff + 1e-10)
                if dist < 0.02:
                    if price < price_lvl:
                        return StrategySignal(
                            strategy_name=self.name,
                            symbol=kwargs.get("symbol", ""),
                            direction=SignalDirection.BUY,
                            confidence=0.5,
                            entry_price=round(price, 6),
                            reasoning=f"Price at fib {lvl:.3f} support",
                            indicators={"fib_level": lvl, "level_price": round(price_lvl, 4)},
                        )
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning=f"Price at fib {lvl:.3f} resistance",
                        indicators={"fib_level": lvl, "level_price": round(price_lvl, 4)},
                    )
            return self._hold("Price between fib levels")
        except Exception as exc:
            logger.error("FibonacciRetracement error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["FibonacciRetracementStrategy"]
