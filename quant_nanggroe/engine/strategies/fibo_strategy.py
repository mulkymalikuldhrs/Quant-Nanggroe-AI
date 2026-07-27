"""FiboStrategy — Fibonacci Retracement + Extension.

QNA-compatible port of the Hedge Fund registry ``FiboStrategy`` (name='fibo').
Returns a ``StrategySignal`` (not a DataFrame column) so it wires into
``engine_production_bridge.generate_signals`` and the ``StrategyRegistry``.

Logic: entry near fib retracement levels (0.382/0.5/0.618) in the direction of
the prevailing swing (uptrend → buy dips, downtrend → sell rallies).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
class FiboStrategy(Strategy):
    """Fibonacci Retracement + Extension."""

    name = "fibo"
    description = "Fibonacci: entry di level retracement 0.382/0.5/0.618"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 30)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No DataFrame")
            df = data.copy()
            if len(df) < 30:
                return self._hold("Insufficient data")
            h, l, c = df["high"], df["low"], df["close"]
            lookback = int(self._parameters.get("lookback", 30))

            swing_h = h.rolling(lookback).max()
            swing_l = l.rolling(lookback).min()
            rng = swing_h - swing_l

            fib_382 = swing_h - rng * 0.382
            fib_500 = swing_h - rng * 0.500
            fib_618 = swing_h - rng * 0.618

            last = -1
            price = float(c.iloc[last])
            # Uptrend: price above the swing low from `lookback` bars ago
            uptrend = c.iloc[last] > swing_l.iloc[last - lookback]
            # Downtrend: price below the swing high from `lookback` bars ago
            downtrend = c.iloc[last] < swing_h.iloc[last - lookback]

            if uptrend and (price <= fib_618.iloc[last]) and (price >= fib_382.iloc[last]):
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=0.55,
                    entry_price=price,
                    reasoning="Fibo: price in 0.382-0.618 retracement zone during uptrend",
                    indicators={
                        "fib_382": float(fib_382.iloc[last]),
                        "fib_500": float(fib_500.iloc[last]),
                        "fib_618": float(fib_618.iloc[last]),
                    },
                )
            if downtrend and (price >= fib_382.iloc[last]) and (price <= fib_618.iloc[last]):
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=0.55,
                    entry_price=price,
                    reasoning="Fibo: price in 0.382-0.618 retracement zone during downtrend",
                    indicators={
                        "fib_382": float(fib_382.iloc[last]),
                        "fib_500": float(fib_500.iloc[last]),
                        "fib_618": float(fib_618.iloc[last]),
                    },
                )
            return self._hold("No fib retracement entry")
        except Exception as e:  # pragma: no cover
            logger.debug("Fibo error: %s", e)
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["FiboStrategy"]
