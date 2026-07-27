"""Fibonacci Arc — trend reversal at support/resistance arcs."""

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
class FibonacciArcStrategy(Strategy):
    """Fibonacci Arc — trend reversal at support/resistance arcs."""

    name = "fibonacci_arc"
    description = "Fibonacci arc: support/resistance arcs from swings"

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
            window = c.iloc[-self.lookback:]
            hh = float(h.iloc[-self.lookback:].max())
            ll = float(l.iloc[-self.lookback:].min())
            price = float(c.iloc[-1])
            levels = [0.382, 0.5, 0.618]
            for lvl in levels:
                supp = hh - lvl * (hh - ll)
                res = ll + lvl * (hh - ll)
                if abs(price - supp) / (hh - ll + 1e-10) < 0.02:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.BUY,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning=f"Price at fib arc support {lvl:.3f}",
                        indicators={"fib_level": lvl, "support": round(supp, 4), "resistance": round(res, 4)},
                    )
                if abs(price - res) / (hh - ll + 1e-10) < 0.02:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning=f"Price at fib arc resistance {lvl:.3f}",
                        indicators={"fib_level": lvl, "support": round(supp, 4), "resistance": round(res, 4)},
                    )
            return self._hold("Price between fib arc levels")
        except Exception as exc:
            logger.error("FibonacciArc error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["FibonacciArcStrategy"]
