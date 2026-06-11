"""Asset Correlation Monitoring.

Monitors pairwise asset correlations to detect:
- Excessive correlation between positions (risk concentration)
- Correlation regime changes (market stress detection)
- Portfolio diversification effectiveness

Provides:
- Rolling correlation matrix
- Correlation regime detection
- Diversification score
- Stress correlation analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CorrelationAlert:
    """Alert for correlation anomaly."""

    pair: str
    current_correlation: float
    historical_avg: float
    z_score: float
    alert_type: str  # "high_correlation", "regime_change", "stress"


class CorrelationMonitor:
    """Asset Correlation Monitor.

    Tracks rolling correlations between assets and alerts when:
    - Pairwise correlation exceeds threshold
    - Correlation regime changes (e.g., decorrelation → high correlation)
    - Market stress is detected (everything becomes correlated)
    """

    # Correlated asset groups for correlation checks
    CORRELATED_GROUPS = [
        {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"},
        {"USDJPY", "USDCHF", "USDCAD"},
        {"XAUUSD", "XAGUSD"},
        {"BTCUSDT", "ETHUSDT"},
        {"SPY", "QQQ", "IWM"},
    ]

    def __init__(
        self,
        lookback: int = 60,
        high_correlation_threshold: float = 0.7,
        stress_threshold: float = 0.8,
    ) -> None:
        self.lookback = lookback
        self.high_corr_threshold = high_correlation_threshold
        self.stress_threshold = stress_threshold
        self._history: List[pd.DataFrame] = []

    def is_correlated(self, symbol_a: str, symbol_b: str) -> bool:
        """Check if two symbols are in the same correlated group.

        Args:
            symbol_a: First symbol.
            symbol_b: Second symbol.

        Returns:
            True if symbols are known to be correlated.
        """
        for group in self.CORRELATED_GROUPS:
            if symbol_a.upper() in group and symbol_b.upper() in group:
                return True
        return False

    def count_correlated_positions(
        self,
        symbol: str,
        active_positions: List[str],
    ) -> int:
        """Count how many active positions are correlated with the given symbol.

        Args:
            symbol: Symbol to check.
            active_positions: List of currently held symbols.

        Returns:
            Number of correlated positions.
        """
        return sum(1 for p in active_positions if self.is_correlated(p, symbol))

    def compute_rolling_correlation(
        self,
        returns: pd.DataFrame,
        window: Optional[int] = None,
    ) -> pd.DataFrame:
        """Compute rolling correlation matrix.

        Args:
            returns: DataFrame of asset returns (columns = assets).
            window: Rolling window size (default: self.lookback).

        Returns:
            Rolling correlation matrix for the last window.
        """
        if window is None:
            window = self.lookback

        if len(returns) < window:
            return returns.corr()

        return returns.iloc[-window:].corr()

    def compute_diversification_score(
        self,
        returns: pd.DataFrame,
        weights: Optional[np.ndarray] = None,
    ) -> float:
        """Compute portfolio diversification score.

        Score is based on the ratio of weighted average volatility
        to portfolio volatility. Higher = more diversified.

        Args:
            returns: DataFrame of asset returns.
            weights: Portfolio weights (default: equal weight).

        Returns:
            Diversification score (0-1, higher is more diversified).
        """
        n = returns.shape[1]
        if n < 2:
            return 0.0

        if weights is None:
            weights = np.ones(n) / n

        vols = returns.std().values
        weighted_avg_vol = np.sum(weights * vols)

        cov = returns.cov().values
        port_vol = np.sqrt(weights @ cov @ weights)

        if weighted_avg_vol <= 0:
            return 0.0

        # Diversification ratio
        div_ratio = weighted_avg_vol / port_vol if port_vol > 0 else 0.0

        # Normalize to 0-1 range
        # Perfect diversification: div_ratio = sqrt(n)
        # No diversification: div_ratio = 1.0
        max_div = np.sqrt(n)
        score = (div_ratio - 1.0) / (max_div - 1.0) if max_div > 1 else 0.0
        return float(np.clip(score, 0.0, 1.0))

    def detect_stress(
        self,
        returns: pd.DataFrame,
        window: Optional[int] = None,
    ) -> Dict[str, any]:
        """Detect market stress via correlation analysis.

        During stress, correlations tend to increase (everything falls together).
        This is measured as the average pairwise correlation.

        Args:
            returns: DataFrame of asset returns.
            window: Rolling window size.

        Returns:
            Dict with stress detection results.
        """
        corr = self.compute_rolling_correlation(returns, window)

        # Average off-diagonal correlation
        n = corr.shape[0]
        if n < 2:
            return {"stress_detected": False, "avg_correlation": 0.0, "stress_level": "NORMAL"}

        mask = ~np.eye(n, dtype=bool)
        avg_corr = float(corr.values[mask].mean())

        stress_detected = avg_corr > self.stress_threshold
        stress_level = "STRESS" if avg_corr > self.stress_threshold else (
            "ELEVATED" if avg_corr > self.high_corr_threshold else "NORMAL"
        )

        return {
            "stress_detected": stress_detected,
            "avg_correlation": round(avg_corr, 4),
            "stress_level": stress_level,
            "max_pairwise": round(float(corr.values[mask].max()), 4),
            "min_pairwise": round(float(corr.values[mask].min()), 4),
        }
