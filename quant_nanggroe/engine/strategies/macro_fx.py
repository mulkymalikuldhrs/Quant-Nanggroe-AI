"""Macro FX — momentum-based FX macro strategy."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class MacroFXStrategy(Strategy):
    """Macro FX — momentum-based FX cross signals."""

    name = "macro_fx"
    description = "Macro FX: momentum-based FX cross strategy"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 20))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.lookback + 5:
                return self._hold("Insufficient data")
            sma = c.rolling(self.lookback).mean()
            price = float(c.iloc[-1])
            ma = float(sma.iloc[-1]) if not np.isnan(sma.iloc[-1]) else price
            slope = 0.0
            if len(c) >= self.lookback:
                x = np.arange(min(self.lookback, len(c)))
                y_vals = c.iloc[-len(x):].values
                if len(x) == len(y_vals):
                    slope = np.polyfit(x, y_vals, 1)[0]
            if price > ma and slope > 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"FX bullish: price above MA, slope {slope:.4f}",
                    indicators={"ma": round(ma, 4), "slope": round(slope, 4)},
                )
            if price < ma and slope < 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"FX bearish: price below MA, slope {slope:.4f}",
                    indicators={"ma": round(ma, 4), "slope": round(slope, 4)},
                )
            return self._hold("FX neutral")
        except Exception as exc:
            logger.error("MacroFX error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["MacroFXStrategy"]
