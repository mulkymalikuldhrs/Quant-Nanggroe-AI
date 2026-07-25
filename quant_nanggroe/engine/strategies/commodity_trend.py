"""Commodity Trend — dual moving average crossover."""

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
class CommodityTrendStrategy(Strategy):
    """Commodity trend via MA crossover."""

    name = "commodity_trend"
    description = "Commodity trend: fast/slow MA crossover"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.fast: int = int(self._parameters.get("fast", 20))
        self.slow: int = int(self._parameters.get("slow", 100))

    @staticmethod
    def _sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period, min_periods=period).mean()

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.slow + 5:
                return self._hold("Insufficient data")
            fast_ma = self._sma(c, self.fast)
            slow_ma = self._sma(c, self.slow)
            if np.isnan(fast_ma.iloc[-1]) or np.isnan(slow_ma.iloc[-1]):
                return self._hold("MA not ready")
            price = float(c.iloc[-1])
            if fast_ma.iloc[-1] > slow_ma.iloc[-1]:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning="Commodity trend bullish",
                    indicators={"fast_ma": round(float(fast_ma.iloc[-1]), 4), "slow_ma": round(float(slow_ma.iloc[-1]), 4)},
                )
            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=SignalDirection.SELL,
                confidence=0.55,
                entry_price=round(price, 6),
                reasoning="Commodity trend bearish",
                indicators={"fast_ma": round(float(fast_ma.iloc[-1]), 4), "slow_ma": round(float(slow_ma.iloc[-1]), 4)},
            )
        except Exception as exc:
            logger.error("CommodityTrend error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["CommodityTrendStrategy"]
