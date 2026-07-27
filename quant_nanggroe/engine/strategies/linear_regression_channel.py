"""Linear Regression Channel — price deviation from regression."""

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
class LinearRegressionChannelStrategy(Strategy):
    """Linear Regression Channel — price vs regression line."""

    name = "linear_regression_channel"
    description = "Linear regression channel: price deviation"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 50))
        self.std_mult: float = float(self._parameters.get("std_mult", 2.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"].values[-self.period:]
            if len(c) < self.period:
                return self._hold("Insufficient data")
            X = np.arange(self.period)
            A = np.vstack([X, np.ones(self.period)]).T
            slope, intercept = np.linalg.lstsq(A, c, rcond=None)[0]
            line = slope * X + intercept
            resid = c - line
            std = np.std(resid)
            price = float(c[-1])
            line_val = float(line[-1])
            dev = (price - line_val) / (std + 1e-10)
            if dev > self.std_mult:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"Price {dev:.2f} std above regression",
                    indicators={"slope": round(float(slope), 4), "deviation": round(float(dev), 3), "std": round(float(std), 4)},
                )
            if dev < -self.std_mult:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"Price {abs(dev):.2f} std below regression",
                    indicators={"slope": round(float(slope), 4), "deviation": round(float(dev), 3), "std": round(float(std), 4)},
                )
            return self._hold(f"Deviation {dev:.2f} within channel")
        except Exception as exc:
            logger.error("LinearRegressionChannel error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["LinearRegressionChannelStrategy"]
