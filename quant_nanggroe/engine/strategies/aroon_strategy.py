"""Aroon — trend strength and direction."""

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
class AroonStrategy(Strategy):
    """Aroon — trend strength and direction."""

    name = "aroon"
    description = "Aroon: trend strength and direction"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 25))
        self.threshold: float = float(self._parameters.get("threshold", 70.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.period + 5:
                return self._hold("Insufficient data")
            h_period = h.rolling(self.period + 1)
            l_period = l.rolling(self.period + 1)
            aroon_up = ((self.period - h_period.apply(lambda x: x.argmax() if len(x) == self.period + 1 else np.nan, raw=True)) / self.period) * 100
            aroon_down = ((self.period - l_period.apply(lambda x: x.argmin() if len(x) == self.period + 1 else np.nan, raw=True)) / self.period) * 100
            if np.isnan(aroon_up.iloc[-1]):
                return self._hold("Aroon not ready")
            up, down = float(aroon_up.iloc[-1]), float(aroon_down.iloc[-1])
            price = float(c.iloc[-1])
            if up > self.threshold and up > down:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=min(up / 100, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"Aroon up {up:.0f} > down {down:.0f}",
                    indicators={"aroon_up": round(up, 2), "aroon_down": round(down, 2)},
                )
            if down > self.threshold and down > up:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=min(down / 100, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"Aroon down {down:.0f} > up {up:.0f}",
                    indicators={"aroon_up": round(up, 2), "aroon_down": round(down, 2)},
                )
            return self._hold(f"Aroon below threshold: up={up:.0f} down={down:.0f}")
        except Exception as exc:
            logger.error("Aroon error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["AroonStrategy"]
