"""ATR breakout — volatility-adjusted breakout detection."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class ATRBreakoutStrategy(Strategy):
    """ATR breakout — volatility-adjusted breakout detection."""

    name = "atr_breakout"
    description = "ATR breakout: volatility-adjusted breakout detection"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.atr_period: int = int(self._parameters.get("atr_period", 14))
        self.lookback: int = int(self._parameters.get("lookback", 20))
        self.atr_mult: float = float(self._parameters.get("atr_mult", 2.0))

    @staticmethod
    def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=period).mean()

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            min_len = max(self.atr_period, self.lookback) + 5
            if len(c) < min_len:
                return self._hold("Insufficient data")
            atr = self._compute_atr(h, l, c, self.atr_period)
            atr_val = float(atr.iloc[-1])
            if np.isnan(atr_val):
                return self._hold("ATR not ready")
            highest = float(h.iloc[-self.lookback:].max())
            lowest = float(l.iloc[-self.lookback:].min())
            price = float(c.iloc[-1])
            if price > highest - atr_val * 0.5:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"ATR breakout: price near {self.lookback}-bar high",
                    indicators={"atr": round(atr_val, 4), "high": round(highest, 4)},
                )
            if price < lowest + atr_val * 0.5:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"ATR breakdown: price near {self.lookback}-bar low",
                    indicators={"atr": round(atr_val, 4), "low": round(lowest, 4)},
                )
            return self._hold("No breakout detected")
        except Exception as exc:
            logger.error("ATRBreakout error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["ATRBreakoutStrategy"]
