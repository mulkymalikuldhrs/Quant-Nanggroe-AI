"""Carry Trade — proxy carry trade via momentum."""

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
class CarryTradeStrategy(Strategy):
    """Carry trade via short-term vs long-term momentum."""

    name = "carry_trade"
    description = "Carry trade proxy via momentum comparison"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 21))
        self.carry_threshold: float = float(self._parameters.get("carry_threshold", 0.02))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            close = data["close"]
            if len(close) < self.lookback + 5:
                return self._hold("Insufficient data")
            rets = close.pct_change().iloc[-self.lookback:]
            if len(rets) < 5:
                return self._hold("Insufficient returns data")
            avg_ret = float(rets.mean())
            price = float(close.iloc[-1])
            if avg_ret > self.carry_threshold:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"Carry long: avg return {avg_ret:.4f} > {self.carry_threshold}",
                    indicators={"avg_return": round(avg_ret, 4)},
                )
            if avg_ret < -self.carry_threshold:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"Carry short: avg return {avg_ret:.4f} < {-self.carry_threshold}",
                    indicators={"avg_return": round(avg_ret, 4)},
                )
            return self._hold(f"Carry neutral: avg return {avg_ret:.4f}")
        except Exception as exc:
            logger.error("CarryTrade error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["CarryTradeStrategy"]
