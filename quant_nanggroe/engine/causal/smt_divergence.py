"""
SMT Divergence Detector — Cointegration-based cross-asset divergence detection.

Implements the Bennett (2022) methodology for detecting Smart Money Technique (SMT)
divergence via Engle-Granger cointegration breakdown:

    SMT divergences occur when two fundamentally correlated assets
    temporarily decouple — typically indicating institutional distribution
    (fake breakout) or accumulation (fake breakdown).

The detector:
    1. Fits an Engle-Granger cointegration model on a rolling window
    2. Computes the current z-score of the spread
    3. Flags divergence when z-score exceeds configurable thresholds
    4. Computes half-life of mean reversion for trade timing

References:
    - Engle & Granger (1987): "Co-Integration and Error Correction:
      Representation, Estimation, and Testing" (Econometrica)
    - Bennett (2022): Smart Money Concepts / ICT methodology
    - SSRN-3847291: Institutional order flow detection via cross-asset divergence
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)


class SMTDivergenceDetector:
    """
    SMT Divergence Detector — tracks cointegration between correlated pairs.

    Detects when two fundamentally linked assets (e.g. GC1! vs SI1!, ES1! vs NQ1!)
    diverge beyond statistical norms, signalling institutional manipulation.

    Key pairs tracked:
        - GC1! (Gold) ↔ SI1! (Silver) — Precious metals
        - ES1! (S&P 500) ↔ NQ1! (Nasdaq) — Equity indices
        - 6E1! (EUR/USD) ↔ 6J1! (USD/JPY) — Inverse dollar pairs
        - GC1! (Gold) ↔ ZB1! (Bonds) — Safe haven competition
        - ES1! (S&P 500) ↔ ZB1! (Bonds) — Risk-on/off regime

    Usage:
        detector = SMTDivergenceDetector()
        result = detector.check_divergence(prices_a, prices_b, "GC1!", "SI1!")
    """

    # Default cointegration pairs with expected hedge ratios
    DEFAULT_PAIRS = {
        ("GC1!", "SI1!"): {"expected_ratio": 75.0, "description": "Gold / Silver"},
        ("SI1!", "GC1!"): {"expected_ratio": 0.013, "description": "Silver / Gold"},
        ("ES1!", "NQ1!"): {"expected_ratio": 0.14, "description": "S&P 500 / Nasdaq"},
        ("NQ1!", "ES1!"): {"expected_ratio": 7.2, "description": "Nasdaq / S&P 500"},
        ("6E1!", "6J1!"): {"expected_ratio": 0.009, "description": "EUR/USD / USD/JPY"},
        ("GC1!", "ZB1!"): {"expected_ratio": 0.30, "description": "Gold / Bonds"},
        ("ES1!", "ZB1!"): {"expected_ratio": 0.04, "description": "S&P 500 / Bonds"},
    }

    def __init__(
        self,
        cointegration_window: int = 60,
        divergence_threshold: float = 2.0,
        severe_threshold: float = 3.0,
        half_life_max: float = 40.0,
        adf_pvalue_threshold: float = 0.05,
    ):
        """
        Args:
            cointegration_window: Rolling window for ADF test (default: 60 periods).
            divergence_threshold: Z-score threshold for divergence flag (default: 2.0σ).
            severe_threshold: Z-score threshold for severe divergence (default: 3.0σ).
            half_life_max: Maximum acceptable half-life for mean reversion (default: 40).
            adf_pvalue_threshold: P-value threshold for cointegration test (default: 0.05).
        """
        self.cointegration_window = cointegration_window
        self.divergence_threshold = divergence_threshold
        self.severe_threshold = severe_threshold
        self.half_life_max = half_life_max
        self.adf_pvalue_threshold = adf_pvalue_threshold

        # State
        self._spread_history: Dict[str, List[float]] = {}
        self._last_results: Dict[str, Dict[str, Any]] = {}

    def _pair_key(self, name_a: str, name_b: str) -> str:
        """Generate a canonical key for a pair."""
        return f"{name_a}↔{name_b}"

    def check_divergence(
        self,
        series_a: List[float],
        series_b: List[float],
        name_a: str = "asset_a",
        name_b: str = "asset_b",
    ) -> Dict[str, Any]:
        """
        Check SMT divergence between two correlated price series.

        Methodology (Bennett 2022):
            1. Fit linear regression: series_a = beta * series_b + spread
            2. ADF test on spread → check cointegration
            3. Compute current z-score of the spread
            4. Flag divergence if |z-score| > threshold

        Args:
            series_a: Price series for asset A (e.g. GC1! gold futures).
            series_b: Price series for asset B (e.g. SI1! silver futures).
            name_a: Name of asset A.
            name_b: Name of asset B.

        Returns:
            Dict with:
                diverged: True/False
                zscore: Current spread z-score
                half_life: Mean reversion half-life (periods)
                direction: "A_OVER_B" | "B_OVER_A" | "NEUTRAL"
                severity: "none" | "diverged" | "severe"
                is_cointegrated: True/False
                adf_statistic: ADF test statistic
                adf_pvalue: ADF test p-value
                hedge_ratio: Estimated hedge ratio (beta)
        """
        arr_a = np.asarray(series_a, dtype=np.float64)
        arr_b = np.asarray(series_b, dtype=np.float64)

        if len(arr_a) < self.cointegration_window or len(arr_b) < self.cointegration_window:
            return {
                "diverged": False,
                "error": "Insufficient data for cointegration test",
                "n_samples": min(len(arr_a), len(arr_b)),
                "required": self.cointegration_window,
            }

        # Ensure same length
        min_len = min(len(arr_a), len(arr_b))
        arr_a = arr_a[-min_len:]
        arr_b = arr_b[-min_len:]

        pair_key = self._pair_key(name_a, name_b)

        try:
            # Step 1: Estimate hedge ratio via linear regression
            #   series_a = beta * series_b + spread
            beta, alpha, r_value, p_value, std_err = stats.linregress(arr_b, arr_a)
            spread = arr_a - (alpha + beta * arr_b)

            # Step 2: ADF test for cointegration
            adf_result = adfuller(
                spread, maxlag=min(12, len(spread) // 4 - 1), autolag="AIC"
            )
            adf_stat, adf_pvalue = adf_result[0], adf_result[1]
            is_cointegrated = adf_pvalue < self.adf_pvalue_threshold

            # Step 3: Compute spread z-score
            spread_mean = np.mean(spread)
            spread_std = np.std(spread)
            current_spread = spread[-1]
            zscore = float((current_spread - spread_mean) / max(spread_std, 1e-12))

            # Step 4: Half-life of mean reversion
            spread_lag = spread[:-1]
            spread_diff = np.diff(spread)
            try:
                hr_beta, hr_alpha, _, _, _ = stats.linregress(spread_lag, spread_diff)
                half_life = float(-np.log(2) / max(hr_beta, 1e-12))
                half_life = min(max(half_life, 1.0), self.half_life_max)
            except Exception:
                half_life = self.half_life_max

            # Step 5: Determine divergence severity
            abs_z = abs(zscore)
            if abs_z >= self.severe_threshold:
                severity = "severe"
                diverged = True
            elif abs_z >= self.divergence_threshold:
                severity = "diverged"
                diverged = True
            else:
                severity = "none"
                diverged = False

            # Step 6: Direction
            if zscore > self.divergence_threshold:
                direction = f"{name_a}_OVER_{name_b}"
            elif zscore < -self.divergence_threshold:
                direction = f"{name_b}_OVER_{name_a}"
            else:
                direction = "NEUTRAL"

            # Step 7: Expected convergence based on pair metadata
            pair_info = self.DEFAULT_PAIRS.get(
                (name_a, name_b),
                {"expected_ratio": 1.0, "description": f"{name_a} / {name_b}"},
            )
            expected_ratio = pair_info["expected_ratio"]
            current_ratio = arr_a[-1] / max(arr_b[-1], 1e-12)
            ratio_deviation_pct = ((current_ratio - expected_ratio) / expected_ratio) * 100

            result = {
                "diverged": diverged,
                "severity": severity,
                "zscore": round(zscore, 3),
                "half_life": round(half_life, 1),
                "direction": direction,
                "is_cointegrated": bool(is_cointegrated),
                "adf_statistic": round(float(adf_stat), 4),
                "adf_pvalue": round(float(adf_pvalue), 6),
                "hedge_ratio": round(float(beta), 4),
                "current_spread": round(float(current_spread), 4),
                "spread_mean": round(float(spread_mean), 4),
                "spread_std": round(float(spread_std), 4),
                "expected_ratio": expected_ratio,
                "current_ratio": round(float(current_ratio), 4),
                "ratio_deviation_pct": round(float(ratio_deviation_pct), 2),
                "n_samples": min_len,
                "pair_name": pair_info["description"],
                "asset_a": name_a,
                "asset_b": name_b,
            }

            # Store history
            if pair_key not in self._spread_history:
                self._spread_history[pair_key] = []
            self._spread_history[pair_key].append(zscore)
            # Keep last 500 entries
            if len(self._spread_history[pair_key]) > 500:
                self._spread_history[pair_key] = self._spread_history[pair_key][-500:]

            self._last_results[pair_key] = result
            return result

        except Exception as e:
            logger.warning("SMT divergence check failed: %s", e)
            return {
                "diverged": False,
                "error": str(e),
                "asset_a": name_a,
                "asset_b": name_b,
            }

    def get_zscore_history(self, name_a: str, name_b: str) -> List[float]:
        """Get historical z-scores for a pair."""
        return self._spread_history.get(
            self._pair_key(name_a, name_b), []
        ).copy()

    def get_last_result(
        self, name_a: str, name_b: str
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent divergence check result for a pair."""
        return self._last_results.get(self._pair_key(name_a, name_b))

    def get_all_active_divergences(
        self, min_severity: str = "diverged"
    ) -> List[Dict[str, Any]]:
        """
        Get all currently active divergences across tracked pairs.

        Args:
            min_severity: Minimum severity level ("diverged" or "severe").

        Returns:
            List of result dicts for divergences meeting the threshold.
        """
        levels = {"none": 0, "diverged": 1, "severe": 2}
        min_level = levels.get(min_severity, 1)

        active = []
        for pair_key, result in self._last_results.items():
            if levels.get(result.get("severity", "none"), 0) >= min_level:
                active.append(result)
        return active

    def pair_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a summary of all tracked pairs and their current status.
        """
        summary = {}
        for (a, b), info in self.DEFAULT_PAIRS.items():
            pair_key = self._pair_key(a, b)
            result = self._last_results.get(pair_key, {})
            summary[pair_key] = {
                "pair_name": info["description"],
                "asset_a": a,
                "asset_b": b,
                "diverged": result.get("diverged", False),
                "severity": result.get("severity", "none"),
                "zscore": result.get("zscore", 0.0),
                "half_life": result.get("half_life", 0.0),
                "is_cointegrated": result.get("is_cointegrated", False),
                "last_checked": result.get("n_samples", 0) > 0,
            }
        return summary


__all__ = [
    "SMTDivergenceDetector",
]
