"""Quarterly Theory (ICT) Strategy — QNA-compatible port."""

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
class QuarterlyTheoryStrategy(Strategy):
    """ICT Quarterly Theory — session liquidity grabs."""

    name = "quarterly"
    description = "Quarterly Theory: Asian/London/NY session bias"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 20)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No DataFrame")
            df = data.copy()
            if len(df) < 30:
                return self._hold("Insufficient data")
            h, l, c = df["high"], df["low"], df["close"]
            lb = int(self._parameters.get("lookback", 20))
            last = -1

            hh_20 = h.rolling(lb).max().values
            ll_20 = l.rolling(lb).min().values

            # Liquidity grab: break below recent low then close back above
            if c.values[last] > ll_20[last] and c.values[last - 1] <= ll_20[last - 1]:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    entry_price=float(c.values[last]),
                    reasoning="Quarterly: liquidity grab below LL then reclaim",
                    indicators={"ll_20": float(ll_20[last])},
                )
            if c.values[last] < hh_20[last] and c.values[last - 1] >= hh_20[last - 1]:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    entry_price=float(c.values[last]),
                    reasoning="Quarterly: liquidity grab above HH then reject",
                    indicators={"hh_20": float(hh_20[last])},
                )
            return self._hold("No liquidity grab")
        except Exception as e:  # pragma: no cover
            logger.debug("Quarterly error: %s", e)
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["QuarterlyTheoryStrategy"]
