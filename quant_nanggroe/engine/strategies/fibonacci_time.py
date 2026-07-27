"""Fibonacci Time — time-based cycle projection."""

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
class FibonacciTimeStrategy(Strategy):
    """Fibonacci Time — time-based cycle projection."""

    name = "fibonacci_time"
    description = "Fibonacci time: time-based cycle projection"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 100))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.lookback:
                return self._hold("Insufficient data")
            window_h = h.iloc[-self.lookback:]
            window_l = l.iloc[-self.lookback:]
            hh_idx = window_h.idxmax()
            ll_idx = window_l.idxmin()
            if hh_idx > ll_idx:
                bars = int(c.index.get_loc(hh_idx) - c.index.get_loc(ll_idx)) if c.index.is_monotonic_increasing else 0
            else:
                bars = int(c.index.get_loc(ll_idx) - c.index.get_loc(hh_idx)) if c.index.is_monotonic_increasing else 0
            bars = max(bars, 1)
            price = float(c.iloc[-1])
            fibs = [0.382, 0.5, 0.618, 1.0, 1.618, 2.618]
            for fib in fibs:
                target = int(bars * fib)
                if target > 0 and target <= len(c):
                    ref_price = float(c.iloc[-target])
                    ret = price / ref_price - 1.0
                    if abs(ret) > 0.02:
                        return StrategySignal(
                            strategy_name=self.name,
                            symbol=kwargs.get("symbol", ""),
                            direction=SignalDirection.BUY if ret > 0 else SignalDirection.SELL,
                            confidence=0.5,
                            entry_price=round(price, 6),
                            reasoning=f"Fib time: {fib:.3f} of {bars}-bar cycle",
                            indicators={"fib": fib, "cycle_bars": bars, "ret": round(ret, 4)},
                        )
            return self._hold("No fib time signal")
        except Exception as exc:
            logger.error("FibonacciTime error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["FibonacciTimeStrategy"]
