"""Choppiness Index — trending vs choppy regime detection."""

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
class ChoppinessIndexStrategy(Strategy):
    """Choppiness Index — trending vs choppy regime detection."""

    name = "choppiness_index"
    description = "Choppiness index: trending vs choppy market"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 14))
        self.trend_threshold: float = float(self._parameters.get("trend_threshold", 38.0))
        self.choppy_threshold: float = float(self._parameters.get("choppy_threshold", 62.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.period + 5:
                return self._hold("Insufficient data")
            tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
            atr_sum = tr.rolling(self.period).sum()
            hh = h.rolling(self.period).max()
            ll = l.rolling(self.period).min()
            ci = 100 * np.log(atr_sum / (hh - ll + 1e-10)) / np.log(self.period)
            val = float(ci.iloc[-1]) if not np.isnan(ci.iloc[-1]) else 50.0
            price = float(c.iloc[-1])
            if val < self.trend_threshold:
                ret = float(c.iloc[-1]) / float(c.iloc[-int(self.period / 2)]) - 1.0
                sig = 1.0 if ret > 0 else -1.0
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY if sig > 0 else SignalDirection.SELL,
                    confidence=0.6,
                    entry_price=round(price, 6),
                    reasoning=f"Choppiness {val:.0f} < {self.trend_threshold}: trending",
                    indicators={"choppiness": round(val, 2)},
                )
            return self._hold(f"Choppiness {val:.0f} in choppy range")
        except Exception as exc:
            logger.error("ChoppinessIndex error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["ChoppinessIndexStrategy"]
