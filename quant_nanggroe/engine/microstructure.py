"""Market microstructure models for Quant Nanggroe AI.

Implements institutional-grade microstructure metrics:
- VPIN (Volume-synchronized Probability of Informed Trading)
- Kyle's Lambda (price impact / order flow)
- Amihud Illiquidity Ratio
- Realized Spread / Effective Spread estimation

All metrics operate on tick-level or bar-level data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MicrostructureMetrics:
    vpin: float = 0.0
    kyle_lambda: float = 0.0
    amihud_illiquidity: float = 0.0
    realized_spread: float = 0.0
    effective_spread: float = 0.0
    trade_intensity: float = 0.0
    avg_trade_size: float = 0.0
    n_observations: int = 0


class VPINCalculator:
    """Volume-synchronized Probability of Informed Trading.

    VPIN = 1 - |2 * V_buy - V_sell| / V_total over N volume buckets.

    Higher VPIN (>0.6) indicates higher probability of informed trading
    and toxic order flow.
    """

    def __init__(self, n_buckets: int = 50, bucket_volume: int = 1000) -> None:
        self.n_buckets = n_buckets
        self.bucket_volume = bucket_volume

    def calculate(self, trades: pd.DataFrame) -> float:
        if trades.empty or len(trades) < self.n_buckets:
            return 0.0

        required_cols = {"price", "volume"}
        if not required_cols.issubset(trades.columns):
            raise ValueError(f"Need columns: {required_cols}")

        direction = np.where(trades["price"].diff().fillna(0) >= 0, 1, -1)
        v_buy = (trades["volume"] * np.maximum(direction, 0)).sum()
        v_sell = (trades["volume"] * np.maximum(-direction, 0)).sum()
        v_total = v_buy + v_sell

        if v_total == 0:
            return 0.0

        vpin = 1.0 - abs(2.0 * v_buy - v_total) / v_total
        return float(np.clip(vpin, 0, 1))


class KyleLambdaCalculator:
    """Kyle's Lambda — price impact per unit of order flow.

    Regresses ``Δprice`` on ``signed_volume``. Higher lambda = less liquid.
    """

    def calculate(self, trades: pd.DataFrame) -> float:
        if trades.empty or len(trades) < 30:
            return 0.0

        required = {"price", "volume"}
        if not required.issubset(trades.columns):
            raise ValueError(f"Need columns: {required}")

        delta_p = trades["price"].diff().fillna(0).values[1:]
        signed_v = trades["volume"].values[1:] * np.sign(delta_p)

        X = signed_v.reshape(-1, 1)
        y = delta_p

        try:
            from sklearn.linear_model import LinearRegression
            model = LinearRegression(fit_intercept=True)
            model.fit(X, y)
            return float(model.coef_[0])
        except ImportError:
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            return float(beta[0]) if len(beta) > 0 else 0.0


class AmihudCalculator:
    """Amihud Illiquidity Ratio — daily price response per unit volume.

    ``Amihud = mean(|r| / V_daily)`` where ``r`` is return and ``V`` is volume.

    Higher values indicate greater illiquidity (price moves more per $ traded).
    """

    def calculate(self, trades: pd.DataFrame) -> float:
        if trades.empty or len(trades) < 2:
            return 0.0

        required = {"price", "volume"}
        if not required.issubset(trades.columns):
            raise ValueError(f"Need columns: {required}")

        returns = np.abs(trades["price"].pct_change().fillna(0).values[1:])
        volumes = trades["volume"].values[1:]

        ratios = returns / np.maximum(volumes, 1e-8)
        return float(np.nanmean(ratios))


class MicrostructureAnalyzer:
    """Aggregate microstructure analysis combining VPIN, Kyle, Amihud.

    Usage::
        analyzer = MicrostructureAnalyzer()
        metrics = analyzer.analyze(trade_dataframe)
    """

    def __init__(self) -> None:
        self._vpin = VPINCalculator()
        self._kyle = KyleLambdaCalculator()
        self._amihud = AmihudCalculator()

    def analyze(self, trades: pd.DataFrame) -> MicrostructureMetrics:
        return MicrostructureMetrics(
            vpin=self._vpin.calculate(trades),
            kyle_lambda=self._kyle.calculate(trades),
            amihud_illiquidity=self._amihud.calculate(trades),
            realized_spread=self._estimate_realized_spread(trades),
            effective_spread=self._estimate_effective_spread(trades),
            trade_intensity=len(trades) / max(1, trades["timestamp"].nunique()) if "timestamp" in trades.columns else 0,
            avg_trade_size=float(trades["volume"].mean()) if "volume" in trades.columns else 0,
            n_observations=len(trades),
        )

    @staticmethod
    def _estimate_realized_spread(trades: pd.DataFrame) -> float:
        if trades.empty or len(trades) < 10:
            return 0.0
        if "price" not in trades.columns:
            return 0.0
        spread = trades["price"].rolling(5).std().mean()
        return float(spread) * 2 if not np.isnan(spread) else 0.0

    @staticmethod
    def _estimate_effective_spread(trades: pd.DataFrame) -> float:
        if trades.empty or len(trades) < 2:
            return 0.0
        if "price" not in trades.columns:
            return 0.0
        mid = trades["price"].rolling(2).mean()
        eff = abs(trades["price"] - mid).mean()
        return float(eff) if not np.isnan(eff) else 0.0
