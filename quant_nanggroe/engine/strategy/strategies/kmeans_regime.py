from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class KMeansRegimeStrategy(BaseStrategy):
    """K-Means regime detection on returns and vol clusters."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="KMeansRegime", params=params)
        self.lookback: int = int(self.params.get("lookback", 100))
        self.n_clusters: int = int(self.params.get("n_clusters", 3))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"].values[-self.lookback:]
        if len(c) < self.lookback:
            return None
        rets = np.diff(np.log(c))
        if len(rets) < 10:
            return None
        features = np.column_stack([rets, np.concatenate([rets[:1], rets[:-1]])])
        # Simple k-means via iterative Lloyd
        n = self.n_clusters
        centroids = features[np.random.choice(len(features), n, replace=False)]
        for _ in range(20):
            dists = np.linalg.norm(features[:, None] - centroids[None], axis=2)
            labels = np.argmin(dists, axis=1)
            for k in range(n):
                if np.sum(labels == k) > 0:
                    centroids[k] = features[labels == k].mean(axis=0)
        cur_label = labels[-1]
        cur_return = float(np.mean(rets[labels == cur_label]))
        price = float(c[-1])
        if cur_return > 0:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name, source_strategy=self.name,
                reasoning=f"K-Means regime {cur_label}: positive returns",
                evidence={"regime": int(cur_label), "mean_return": round(cur_return, 4)},
                factors=["ml", "kmeans"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name, source_strategy=self.name,
            reasoning=f"K-Means regime {cur_label}: negative returns",
            evidence={"regime": int(cur_label), "mean_return": round(cur_return, 4)},
            factors=["ml", "kmeans"])
