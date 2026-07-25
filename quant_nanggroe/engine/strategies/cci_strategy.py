"""Commodity Channel Index — overbought/oversold with trend."""

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
class CCIStrategy(Strategy):
    """Commodity Channel Index — overbought/oversold with trend."""

    name = "cci"
    description = "CCI overbought/oversold signals"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 20))
        self.overbought: float = float(self._parameters.get("overbought", 100.0))
        self.oversold: float = float(self._parameters.get("oversold", -100.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            if len(data) < self.period + 5:
                return self._hold("Insufficient data")
            tp = (data["high"] + data["low"] + data["close"]) / 3
            sma = tp.rolling(self.period).mean()
            mad = tp.rolling(self.period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
            cci = (tp - sma) / (0.015 * mad + 1e-10)
            val = float(cci.iloc[-1]) if not np.isnan(cci.iloc[-1]) else 0.0
            price = float(data["close"].iloc[-1])
            if val > self.overbought:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"CCI {val:.0f} overbought",
                    indicators={"cci": round(val, 2)},
                )
            if val < self.oversold:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"CCI {val:.0f} oversold",
                    indicators={"cci": round(val, 2)},
                )
            return self._hold(f"CCI {val:.0f} neutral")
        except Exception as exc:
            logger.error("CCI error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["CCIStrategy"]
