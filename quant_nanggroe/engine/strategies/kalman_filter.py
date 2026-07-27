"""Kalman Filter — adaptive trend estimation."""

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
class KalmanFilterStrategy(Strategy):
    """Kalman Filter — adaptive trend estimation."""

    name = "kalman_filter"
    description = "Kalman filter: adaptive trend estimation"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 20))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"].values
            if len(c) < self.period + 5:
                return self._hold("Insufficient data")
            n = len(c)
            X = np.zeros(n)
            P = np.ones(n) * 0.1
            R, Q = 0.01, 0.001
            for t in range(1, n):
                X_pred = X[t - 1]
                P_pred = P[t - 1] + Q
                K = P_pred / (P_pred + R)
                X[t] = X_pred + K * (c[t] - X_pred)
                P[t] = (1 - K) * P_pred
            state = X
            price = float(c[-1])
            today = float(state[-1])
            yesterday = float(state[-2])
            if price > today and today > yesterday:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning="Kalman filter: uptrend",
                    indicators={"state": round(float(today), 4)},
                )
            if price < today and today < yesterday:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning="Kalman filter: downtrend",
                    indicators={"state": round(float(today), 4)},
                )
            return self._hold("Kalman filter: no clear trend")
        except Exception as exc:
            logger.error("KalmanFilter error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["KalmanFilterStrategy"]
