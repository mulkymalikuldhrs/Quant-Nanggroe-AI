"""Elder Triple Screen — multi-timeframe trend and oscillator."""

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
class ElderTripleScreenStrategy(Strategy):
    """Elder Triple Screen — multi-timeframe trend + oscillator."""

    name = "elder_triple_screen"
    description = "Elder Triple Screen: multi-TF trend + oscillator"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.trend: int = int(self._parameters.get("trend", 26))
        self.osc: int = int(self._parameters.get("osc", 13))

    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, min_periods=period, adjust=False).mean()

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.trend + 5:
                return self._hold("Insufficient data")
            trend_ma = self._ema(c, self.trend)
            trend_ok = float(c.iloc[-1]) > float(trend_ma.iloc[-1])
            if np.isnan(trend_ma.iloc[-1]):
                return self._hold("Trend MA not ready")
            max_hist = float(h.iloc[-self.osc:].max())
            min_hist = float(l.iloc[-self.osc:].min())
            price = float(c.iloc[-1])
            osc_val = (price - min_hist) / (max_hist - min_hist + 1e-10)
            price = float(c.iloc[-1])
            if trend_ok and osc_val < 0.3:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning="Elder Triple: bullish trend + oversold",
                    indicators={"trend_ma": round(float(trend_ma.iloc[-1]), 4), "osc": round(osc_val, 3)},
                )
            if not trend_ok and osc_val > 0.7:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning="Elder Triple: bearish trend + overbought",
                    indicators={"trend_ma": round(float(trend_ma.iloc[-1]), 4), "osc": round(osc_val, 3)},
                )
            return self._hold(f"Elder Triple neutral: trend={trend_ok}, osc={osc_val:.2f}")
        except Exception as exc:
            logger.error("ElderTripleScreen error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["ElderTripleScreenStrategy"]
