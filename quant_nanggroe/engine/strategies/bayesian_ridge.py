"""Bayesian ridge regression with uncertainty-aware signals."""

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
class BayesianRidgeStrategy(Strategy):
    """Bayesian ridge regression with uncertainty-aware signals."""

    name = "bayesian_ridge"
    description = "Bayesian ridge regression with std deviation signals"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 50))
        self.std_mult: float = float(self._parameters.get("std_mult", 1.5))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"].values[-self.period:]
            if len(c) < self.period:
                return self._hold("Insufficient data")
            X = np.c_[np.ones(self.period), np.arange(self.period)]
            y = c
            lam = 1.0
            I = np.eye(2)
            I[0, 0] = 0
            beta = np.linalg.solve(X.T @ X + lam * I, X.T @ y)
            pred = X @ beta
            resid = y - pred
            se = np.sqrt(np.sum(resid ** 2) / (self.period - 2)) if self.period > 2 else 1.0
            se_pred = se * np.sqrt(1 + 1 / self.period + (X[:, 1] - X[:, 1].mean()) ** 2 / np.sum((X[:, 1] - X[:, 1].mean()) ** 2))
            z = float(resid[-1] / (se_pred[-1] + 1e-10))
            price = float(c[-1])
            if z > self.std_mult:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=min((z - self.std_mult) / 3.0, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"Bayesian ridge: {z:.2f} std above",
                    indicators={"zscore": round(z, 3)},
                )
            if z < -self.std_mult:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=min((abs(z) - self.std_mult) / 3.0, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"Bayesian ridge: {abs(z):.2f} std below",
                    indicators={"zscore": round(z, 3)},
                )
            return self._hold(f"Z-score {z:.2f} within threshold")
        except Exception as exc:
            logger.error("BayesianRidge error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["BayesianRidgeStrategy"]
