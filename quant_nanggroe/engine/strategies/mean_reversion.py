"""Mean Reversion Strategy (Stochastic) — QNA-compatible port."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
class MeanReversionStrategy(Strategy):
    """Mean Reversion via Stochastic Oscillator."""

    name = "mean_rev"
    description = "Mean Reversion: Stochastic %K/%D crossover"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("k_period"):
            params.set("k_period", 14)
        if not params.get("d_period"):
            params.set("d_period", 3)
        if not params.get("oversold"):
            params.set("oversold", 20)
        if not params.get("overbought"):
            params.set("overbought", 80)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No DataFrame")
            df = data.copy()
            if len(df) < 30:
                return self._hold("Insufficient data")
            h, l, c = df["high"], df["low"], df["close"]
            kp = int(self._parameters.get("k_period", 14))
            dp = int(self._parameters.get("d_period", 3))
            os_ = float(self._parameters.get("oversold", 20))
            ob_ = float(self._parameters.get("overbought", 80))

            low_k = l.rolling(kp).min()
            high_k = h.rolling(kp).max()
            stoch_k = 100 * (c - low_k) / (high_k - low_k)
            stoch_d = stoch_k.rolling(dp).mean()

            last = -1
            k = stoch_k.values[last]
            d = stoch_d.values[last]
            close = float(c.values[last])

            if k < os_ and k > d:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    entry_price=close,
                    reasoning=f"MeanRev: stochastic oversold ({k:.1f}) K crossed above D",
                    indicators={"stoch_k": float(k), "stoch_d": float(d)},
                )
            if k > ob_ and k < d:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    entry_price=close,
                    reasoning=f"MeanRev: stochastic overbought ({k:.1f}) K crossed below D",
                    indicators={"stoch_k": float(k), "stoch_d": float(d)},
                )
            return self._hold("No stochastic signal")
        except Exception as e:  # pragma: no cover
            logger.debug("MeanRev error: %s", e)
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["MeanReversionStrategy"]
