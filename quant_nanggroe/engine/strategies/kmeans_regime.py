"""K-Means Regime — regime detection via K-Means clustering."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

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
class KMeansRegimeStrategy(Strategy):
    """K-Means Regime — clustering regimes from returns + vol."""

    name = "kmeans_regime"
    description = "K-means regime: cluster-based market regime"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 60))
        self.n_clusters: int = int(self._parameters.get("n_clusters", 3))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.period + 10:
                return self._hold("Insufficient data")
            rets = c.pct_change().dropna().values[-self.period:]
            vol = c.rolling(5).std().dropna().values[-self.period:]
            if len(rets) < 10 or len(vol) < 10:
                return self._hold("Insufficient features")
            n = min(len(rets), len(vol))
            rets, vol = rets[-n:], vol[-n:]
            feat = np.column_stack([(rets - rets.mean()) / (rets.std() + 1e-10),
                                    (vol - vol.mean()) / (vol.std() + 1e-10)])
            centroids = feat[np.random.choice(n, min(self.n_clusters, n), replace=False)]
            for _ in range(20):
                dists = np.linalg.norm(feat[:, None] - centroids[None, :], axis=2)
                labels = np.argmin(dists, axis=1)
                new_c = np.array([feat[labels == k].mean(axis=0) if (labels == k).sum() > 0 else centroids[k] for k in range(min(self.n_clusters, n))])
                if np.allclose(centroids, new_c):
                    break
                centroids = new_c
            current_label = labels[-1]
            current_ret = rets[-1]
            cluster_mean_ret = np.mean([rets[i] for i in range(n) if labels[i] == current_label])
            price = float(c.iloc[-1])
            if cluster_mean_ret > 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning=f"KMeans regime {current_label}: positive cluster",
                    indicators={"regime_label": int(current_label), "cluster_mean_ret": round(float(cluster_mean_ret), 4)},
                )
            if cluster_mean_ret < 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning=f"KMeans regime {current_label}: negative cluster",
                    indicators={"regime_label": int(current_label), "cluster_mean_ret": round(float(cluster_mean_ret), 4)},
                )
            return self._hold(f"KMeans regime {current_label}: neutral")
        except Exception as exc:
            logger.error("KMeansRegime error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["KMeansRegimeStrategy"]
