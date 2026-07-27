"""EWMA vol — exponentially weighted volatility."""

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
class EWMAVolStrategy(Strategy):
    """EWMA vol — exponentially weighted volatility tracking."""

    name = "ewma_vol"
    description = "EWMA vol: exponentially weighted volatility"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 20))
        self.mult: float = float(self._parameters.get("mult", 2.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.period + 5:
                return self._hold("Insufficient data")
            rets = c.pct_change().dropna()
            ewma = rets.ewm(span=self.period, min_periods=self.period).std()
            current_vol = float(ewma.iloc[-1]) if not np.isnan(ewma.iloc[-1]) else 0.0
            avg_vol = float(rets.iloc[-self.period:].std())
            price = float(c.iloc[-1])
            if current_vol > avg_vol * self.mult:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.HOLD,
                    confidence=0.7,
                    entry_price=round(price, 6),
                    reasoning=f"EWMA vol spike: {current_vol:.4f} > {avg_vol*self.mult:.4f}",
                    indicators={"current_vol": round(current_vol, 6), "avg_vol": round(avg_vol, 6)},
                )
            return self._hold(f"EWMA vol normal: {current_vol:.4f}")
        except Exception as exc:
            logger.error("EWMAVol error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["EWMAVolStrategy"]
