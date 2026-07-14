from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class PCAStrategy(BaseStrategy):
    """PCA — principal components as synthetic features for direction."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="PCAStrategy", params=params)
        self.lookback: int = int(self.params.get("lookback", 50))
        self.n_components: int = int(self.params.get("n_components", 3))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        df = data.iloc[-self.lookback:][["open", "high", "low", "close", "volume"]].dropna()
        if len(df) < self.lookback // 2:
            return None
        vals = df.values
        vals = (vals - vals.mean(axis=0)) / (vals.std(axis=0) + 1e-10)
        cov = np.cov(vals.T)
        eigvals, eigvecs = np.linalg.eigh(cov)
        idx = np.argsort(eigvals)[::-1][:self.n_components]
        components = vals @ eigvecs[:, idx]
        # First component direction = trend
        pc1 = components[:, 0]
        slope = np.polyfit(np.arange(len(pc1)), pc1, 1)[0]
        price = float(data["close"].iloc[-1])
        if slope > 0:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning="PCA: PC1 trending up", evidence={"pc1_slope": round(float(slope), 6)},
                factors=["ml", "pca"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name, source_strategy=self.name,
            reasoning="PCA: PC1 trending down", evidence={"pc1_slope": round(float(slope), 6)},
            factors=["ml", "pca"])
