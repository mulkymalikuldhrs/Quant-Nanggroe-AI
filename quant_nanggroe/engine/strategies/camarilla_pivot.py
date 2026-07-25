"""Camarilla Pivot trading strategy."""

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
class CamarillaPivotStrategy(Strategy):
    """Camarilla pivot levels for reversal signals."""

    name = "camarilla_pivot"
    description = "Camarilla pivot support/resistance levels"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty or len(data) < 5:
                return self._hold("No or insufficient data")
            h = float(data["high"].iloc[-2])
            l = float(data["low"].iloc[-2])
            c = float(data["close"].iloc[-2])
            r = h - l
            h8 = c + r * 1.0030
            l8 = c - r * 1.0030
            price = float(data["close"].iloc[-1])
            if price >= h8:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning=f"Price at Camarilla H8 {h8:.4f}",
                    indicators={"h8": round(h8, 4), "l8": round(l8, 4), "range": round(r, 4)},
                )
            if price <= l8:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning=f"Price at Camarilla L8 {l8:.4f}",
                    indicators={"h8": round(h8, 4), "l8": round(l8, 4), "range": round(r, 4)},
                )
            return self._hold("Price between Camarilla levels")
        except Exception as exc:
            logger.error("CamarillaPivot error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["CamarillaPivotStrategy"]
