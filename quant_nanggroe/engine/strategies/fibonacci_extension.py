"""Fibonacci Extension — target levels beyond swing completions."""

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
class FibonacciExtensionStrategy(Strategy):
    """Fibonacci Extension — target levels beyond swing completions."""

    name = "fibonacci_extension"
    description = "Fibonacci extension: price target levels"

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
            price = float(c.iloc[-1])
            window_h = h.iloc[-self.lookback:]
            window_l = l.iloc[-self.lookback:]
            hh = float(window_h.max())
            ll = float(window_l.min())
            hh_idx = window_h.idxmax()
            ll_idx = window_l.idxmin()
            if hh_idx > ll_idx:
                recent = hh
                prior = ll
                ret = float(c.loc[hh_idx]) if hh_idx in c.index else price
                move = hh - ll
                ext = (price - ret) / (move + 1e-10)
                if ext >= 0.618:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning="Price at fib ext 0.618 above prior high",
                        indicators={"extension": round(ext, 3)},
                    )
            else:
                recent = ll
                prior = hh
                ret = float(c.loc[ll_idx]) if ll_idx in c.index else price
                move = hh - ll
                ext = (ret - price) / (move + 1e-10)
                if ext >= 0.618:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.BUY,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning="Price at fib ext 0.618 below prior low",
                        indicators={"extension": round(ext, 3)},
                    )
            return self._hold("No fib extension signal")
        except Exception as exc:
            logger.error("FibonacciExtension error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["FibonacciExtensionStrategy"]
