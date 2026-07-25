"""Fibonacci Fan — trend support/resistance via fan lines."""

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
class FibonacciFanStrategy(Strategy):
    """Fibonacci Fan — trend support/resistance via fan lines."""

    name = "fibonacci_fan"
    description = "Fibonacci fan: trend support/resistance lines"

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
            levels = [0.382, 0.5, 0.618]
            for lvl in levels:
                fan_line = hh - lvl * (hh - ll)
                dist = abs(price - fan_line) / (hh - ll + 1e-10)
                if dist < 0.02:
                    if price < fan_line:
                        return StrategySignal(
                            strategy_name=self.name,
                            symbol=kwargs.get("symbol", ""),
                            direction=SignalDirection.BUY,
                            confidence=0.5,
                            entry_price=round(price, 6),
                            reasoning=f"Price at fib fan support {lvl:.3f}",
                            indicators={"fan_level": lvl, "level_price": round(fan_line, 4)},
                        )
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning=f"Price at fib fan resistance {lvl:.3f}",
                        indicators={"fan_level": lvl, "level_price": round(fan_line, 4)},
                    )
            return self._hold("No fib fan signal")
        except Exception as exc:
            logger.error("FibonacciFan error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["FibonacciFanStrategy"]
