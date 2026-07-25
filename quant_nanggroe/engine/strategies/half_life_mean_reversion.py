"""Half-Life Mean Reversion — mean reversion at half-life decay."""

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
class HalfLifeMeanReversionStrategy(Strategy):
    """Half-Life Mean Reversion — mean reversion at half-life decay."""

    name = "half_life_mean_reversion"
    description = "Half-life mean reversion: auto-regressive decay"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 50))
        self.z_entry: float = float(self._parameters.get("z_entry", 1.5))
        self.z_exit: float = float(self._parameters.get("z_exit", 0.5))

    @staticmethod
    def _compute_half_life(series: pd.Series) -> float:
        y = series.diff().dropna().values
        x = series.shift(1).dropna().values
        if len(y) < 10:
            return 10.0
        n = min(len(y), len(x))
        y, x = y[-n:], x[-n:]
        slope = np.polyfit(x, y, 1)[0]
        if slope >= 0:
            return 10.0
        hl = -np.log(2) / slope
        return min(max(hl, 1), 100)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.lookback + 10:
                return self._hold("Insufficient data")
            series = c.iloc[-self.lookback:]
            half_life = self._compute_half_life(series)
            look = int(min(half_life, len(series) // 2))
            if look < 2:
                return self._hold("Half-life too short")
            mean = float(series.iloc[-look:].mean())
            std = float(series.iloc[-look:].std()) + 1e-10
            price = float(c.iloc[-1])
            z = (price - mean) / std
            if z < -self.z_entry:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=min((abs(z) - self.z_entry) / 2.0, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"HL mean reversion: z={z:.2f} oversold",
                    indicators={"zscore": round(z, 3), "half_life": round(half_life, 1)},
                )
            if z > self.z_entry:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=min((abs(z) - self.z_entry) / 2.0, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"HL mean reversion: z={z:.2f} overbought",
                    indicators={"zscore": round(z, 3), "half_life": round(half_life, 1)},
                )
            return self._hold(f"HL z-score {z:.2f} within entry threshold")
        except Exception as exc:
            logger.error("HalfLifeMeanReversion error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["HalfLifeMeanReversionStrategy"]
