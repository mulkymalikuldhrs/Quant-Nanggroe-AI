"""Algebra Strategy — Statistical Arbitrage (Z-score) — QNA-compatible port."""

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
class AlgebraStrategy(Strategy):
    """Statistical arbitrage via linear algebra — z-score mean reversion."""

    name = "algebra"
    description = "Algebra: Z-score mean reversion + linear regression"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("window"):
            params.set("window", 20)
        if not params.get("entry_z"):
            params.set("entry_z", 2.0)
        if not params.get("exit_z"):
            params.set("exit_z", 0.5)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No DataFrame")
            df = data.copy()
            if len(df) < 30:
                return self._hold("Insufficient data")
            c = df["close"]
            window = int(self._parameters.get("window", 20))
            entry_z = float(self._parameters.get("entry_z", 2.0))

            ma = c.rolling(window).mean()
            std = c.rolling(window).std()
            z = (c - ma) / (std + 1e-4)
            z_slope = z.diff(3)

            last = -1
            close = float(c.values[last])
            zv = float(z.values[last])
            zsl = float(z_slope.values[last])

            if zv < -entry_z and zsl > 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=min(0.8, 0.5 + abs(zv) / 10),
                    entry_price=close,
                    reasoning=f"Algebra: z-score {zv:.2f} < -{entry_z} turning up",
                    indicators={"z_score": zv},
                )
            if zv > entry_z and zsl < 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=min(0.8, 0.5 + abs(zv) / 10),
                    entry_price=close,
                    reasoning=f"Algebra: z-score {zv:.2f} > {entry_z} turning down",
                    indicators={"z_score": zv},
                )
            return self._hold("No z-score extreme")
        except Exception as e:  # pragma: no cover
            logger.debug("Algebra error: %s", e)
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["AlgebraStrategy"]
