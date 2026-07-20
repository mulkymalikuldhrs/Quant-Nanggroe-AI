from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class BayesianRidgeStrategy(BaseStrategy):
    """Bayesian ridge regression with uncertainty-aware signals."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="BayesianRidge", params=params)
        self.period: int = int(self.params.get("period", 50))
        self.std_mult: float = float(self.params.get("std_mult", 1.5))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"].values[-self.period:]
        if len(c) < self.period:
            return None
        X = np.c_[np.ones(self.period), np.arange(self.period)]
        y = c
        # OLS with ridge prior (closed form)
        lam = 1.0
        I = np.eye(2)
        I[0, 0] = 0
        beta = np.linalg.solve(X.T @ X + lam * I, X.T @ y)
        pred = X @ beta
        resid = y - pred
        se = np.sqrt(np.sum(resid ** 2) / (self.period - 2)) if self.period > 2 else 1.0
        se_pred = se * np.sqrt(1 + 1/self.period + (X[:, 1] - X[:, 1].mean()) ** 2 / np.sum((X[:, 1] - X[:, 1].mean()) ** 2))
        z = float(resid[-1] / (se_pred[-1] + 1e-10))
        price = float(c[-1])
        if z > self.std_mult:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min((z - self.std_mult) / 3.0, 1.0), price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Bayesian ridge: {z:.2f} std above", evidence={"zscore": round(z, 3)},
                factors=["ml", "bayesian_ridge"])
        if z < -self.std_mult:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=min((abs(z) - self.std_mult) / 3.0, 1.0), price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Bayesian ridge: {abs(z):.2f} std below", evidence={"zscore": round(z, 3)},
                factors=["ml", "bayesian_ridge"])
        return None
