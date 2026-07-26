"""
CointegrationSMTDetector — SMT Divergence as Cointegration Breakdown.

Implements the Bennett et al. (2022) approach to SMT divergence detection:
instead of a simple Higher-High / Lower-High pattern heuristic, uses
statistical cointegration testing and lead-lag analysis.

Core methodology:
  1. For each correlated pair (e.g., GC1! Gold ↔ SI1! Silver), test
     for cointegration using the Engle-Granger test.
  2. If cointegrated, fit OLS: price_A = hedge_ratio × price_B + spread.
  3. Track the spread = price_A - hedge_ratio × price_B.
  4. Compute z-score of spread: (spread - rolling_mean) / rolling_std.
  5. |z-score| > threshold → cointegration breakdown = SMT divergence.
  6. Lead-lag: time-shifted cross-correlation to find which asset leads.

Reference:
  - Bennett et al. (2022), arXiv:2201.08283 — Lead-lag detection via
    network clustering and time-shifted cross-correlation.
  - Engle & Granger (1987) — Cointegration and error correction.

Usage:
    from quant_nanggroe.engine.intermarket import CointegrationSMTDetector

    detector = CointegrationSMTDetector(z_score_threshold=2.0)
    detector.fit(price_df)  # columns=['GC1!', 'SI1!', 'ES1!', 'NQ1!', ...]
    result = detector.detect()      # Returns dict of pair -> divergence status
    summary = detector.get_summary()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Correlated pair definitions
# ══════════════════════════════════════════════════════════════════════

# Each tuple: (asset_a, asset_b, pair_name, expected_correlation_sign)
# The sign is +1 if they move together, -1 if inverted (e.g., USDJPY)
CORRELATED_PAIRS: list[tuple[str, str, str, int]] = [
    # Precious Metals
    ("GC1!", "SI1!", "Gold-Silver", +1),       # Gold ↔ Silver
    # Equity Indices
    ("ES1!", "NQ1!", "S&P-Nasdaq", +1),        # S&P 500 ↔ Nasdaq
    ("ES1!", "YM1!", "S&P-Dow", +1),           # S&P 500 ↔ Dow
    ("NQ1!", "RTY1!", "Nasdaq-Russell", +1),   # Nasdaq ↔ Russell
    # FX Majors
    ("6E1!", "6B1!", "EUR-GBP", +1),           # EUR ↔ GBP
    ("6E1!", "6J1!", "EUR-JPY", +1),           # EUR ↔ JPY (both vs USD)
    ("6A1!", "6C1!", "AUD-CAD", +1),           # AUD ↔ CAD (commodity FX)
    # Bonds
    ("ZB1!", "ZN1!", "30Y-10Y", +1),           # 30Y ↔ 10Y Treasury
    ("ZN1!", "ZF1!", "10Y-5Y", +1),            # 10Y ↔ 5Y Treasury
    # Cross-asset (inverse correlation)
    ("DXY", "6E1!", "DXY-EUR", -1),            # DXY ↔ EUR (inverse)
    ("GC1!", "DXY", "Gold-DXY", -1),           # Gold ↔ DXY (inverse typically)
]


# ══════════════════════════════════════════════════════════════════════
#  Data structures
# ══════════════════════════════════════════════════════════════════════


@dataclass
class CointegratedPair:
    """Represents a cointegrated pair relationship with its statistical state.

    Attributes:
        pair_name: Human-readable name (e.g. 'Gold-Silver').
        asset_a: First asset symbol (e.g. 'GC1!').
        asset_b: Second asset symbol (e.g. 'SI1!').
        expected_sign: Expected correlation sign (+1 or -1).
        is_cointegrated: True if Engle-Granger test passed.
        hedge_ratio: OLS beta coefficient.
        intercept: OLS intercept term.
        coint_pvalue: P-value from Engle-Granger test.
        spread_mean: Rolling mean of the spread.
        spread_std: Rolling standard deviation of the spread.
        current_zscore: Current z-score of the spread.
        lead_asset: Which asset leads (detected via cross-correlation).
        lag_asset: Which asset lags.
        lead_lag_strength: Cross-correlation strength at optimal lag.
        optimal_lag: Number of periods the lead asset leads by.
        n_observations: Number of price observations used.
    """

    pair_name: str = ""
    asset_a: str = ""
    asset_b: str = ""
    expected_sign: int = 1
    is_cointegrated: bool = False
    hedge_ratio: float = 0.0
    intercept: float = 0.0
    coint_pvalue: float = 1.0
    spread_mean: float = 0.0
    spread_std: float = 0.0
    current_zscore: float = 0.0
    lead_asset: str = ""
    lag_asset: str = ""
    lead_lag_strength: float = 0.0
    optimal_lag: int = 0
    n_observations: int = 0


@dataclass
class SMTDivergenceResult:
    """Result of an SMT divergence check for a single pair.

    Attributes:
        pair_name: Human-readable pair name.
        asset_a: First asset.
        asset_b: Second asset.
        is_cointegrated: Whether the pair is statistically cointegrated.
        divergence_detected: True if |z-score| > threshold.
        divergence_type: 'breakdown_a_up_b_down', 'breakdown_a_down_b_up',
                         'lead_lag_shift', or 'none'.
        zscore: Current z-score of the spread.
        hedge_ratio: Current hedge ratio.
        lead_asset: Asset leading the move.
        lag_asset: Asset lagging.
        lead_lag_lag: Optimal lag in periods.
        confidence: How strong the divergence signal is (0.0 to 1.0).
    """

    pair_name: str = ""
    asset_a: str = ""
    asset_b: str = ""
    is_cointegrated: bool = False
    divergence_detected: bool = False
    divergence_type: str = "none"
    zscore: float = 0.0
    hedge_ratio: float = 0.0
    lead_asset: str = ""
    lag_asset: str = ""
    lead_lag_lag: int = 0
    confidence: float = 0.0


# ══════════════════════════════════════════════════════════════════════
#  CointegrationSMTDetector
# ══════════════════════════════════════════════════════════════════════


class CointegrationSMTDetector:
    """Statistical SMT divergence detector using cointegration breakdown.

    Maintains pairwise relationships for all correlated asset pairs,
    tests for cointegration, computes hedge ratios via OLS, tracks
    spread z-scores, and detects lead-lag relationships.

    Typical workflow:
        1. Fit: Provide historical price data → test cointegration
        2. Detect: Compute current spread z-scores → flag divergences
        3. Lead-lag: Time-shifted cross-correlation → identify leaders
    """

    def __init__(
        self,
        z_score_threshold: float = 2.0,
        coint_pvalue_threshold: float = 0.05,
        pairs: Optional[list[tuple[str, str, str, int]]] = None,
        lead_lag_max_lag: int = 10,
    ):
        """
        Args:
            z_score_threshold: |z-score| threshold for divergence (default: 2.0).
            coint_pvalue_threshold: Max p-value for cointegration (default: 0.05).
            pairs: Custom pair list (default: CORRELATED_PAIRS).
            lead_lag_max_lag: Max lag to check for lead-lag (default: 10).
        """
        self.z_score_threshold = z_score_threshold
        self.coint_pvalue_threshold = coint_pvalue_threshold
        self._pairs = pairs or CORRELATED_PAIRS
        self._lead_lag_max_lag = lead_lag_max_lag

        # Internal state
        self._fitted_pairs: dict[str, CointegratedPair] = {}
        self._price_data: Optional[pd.DataFrame] = None
        self._last_detection: dict[str, SMTDivergenceResult] = {}
        self._fitted = False

    # ── Properties ────────────────────────────────────────────

    @property
    def fitted(self) -> bool:
        """True if the model has been fitted with price data."""
        return self._fitted

    @property
    def n_pairs(self) -> int:
        """Number of pairs being tracked."""
        return len(self._pairs)

    @property
    def n_cointegrated(self) -> int:
        """Number of pairs confirmed as cointegrated."""
        return sum(1 for p in self._fitted_pairs.values() if p.is_cointegrated)

    @property
    def cointegrated_pairs(self) -> list[CointegratedPair]:
        """All cointegrated pairs with their statistical state."""
        return [p for p in self._fitted_pairs.values() if p.is_cointegrated]

    # ── Fit: test cointegration and compute OLS ───────────────

    def fit(
        self,
        price_data: pd.DataFrame,
    ) -> CointegrationSMTDetector:
        """Fit the detector: test cointegration for all pairs.

        For each correlated pair:
          1. Run Engle-Granger cointegration test
          2. If cointegrated, fit OLS hedge ratio
          3. Compute initial spread statistics
          4. Run lead-lag cross-correlation

        Args:
            price_data: DataFrame with columns as asset symbols.
                        Must contain at least 30 observations per asset.

        Returns:
            Self for chaining.
        """
        self._price_data = price_data
        self._fitted_pairs = {}

        for asset_a, asset_b, pair_name, expected_sign in self._pairs:
            if asset_a not in price_data.columns or asset_b not in price_data.columns:
                logger.debug("SMT pair %s: missing columns (%s, %s)", pair_name, asset_a, asset_b)
                continue

            prices_a = price_data[asset_a].dropna()
            prices_b = price_data[asset_b].dropna()

            # Align on common index
            common_idx = prices_a.index.intersection(prices_b.index)
            if len(common_idx) < 30:
                logger.debug("SMT pair %s: insufficient common data (%d obs)", pair_name, len(common_idx))
                continue

            pa = prices_a.loc[common_idx].values
            pb = prices_b.loc[common_idx].values

            # Step 1: Engle-Granger cointegration test
            is_cointegrated, pvalue = self._test_cointegration(pa, pb)

            # Step 2: OLS hedge ratio
            hedge_ratio, intercept = self._compute_hedge_ratio(pa, pb)

            # Step 3: Spread and its statistics
            spread = pa - hedge_ratio * pb - intercept
            spread_mean = float(np.mean(spread))
            spread_std = float(np.std(spread))
            current_zscore = float((spread[-1] - spread_mean) / max(spread_std, 1e-12))

            # Step 4: Lead-lag detection
            lead_asset, lag_asset, lead_strength, opt_lag = self._detect_lead_lag(
                pa, pb, asset_a, asset_b
            )

            pair = CointegratedPair(
                pair_name=pair_name,
                asset_a=asset_a,
                asset_b=asset_b,
                expected_sign=expected_sign,
                is_cointegrated=is_cointegrated,
                hedge_ratio=round(hedge_ratio, 6),
                intercept=round(intercept, 6),
                coint_pvalue=round(pvalue, 6),
                spread_mean=round(spread_mean, 6),
                spread_std=round(spread_std, 6),
                current_zscore=round(current_zscore, 4),
                lead_asset=lead_asset,
                lag_asset=lag_asset,
                lead_lag_strength=round(lead_strength, 4),
                optimal_lag=opt_lag,
                n_observations=len(common_idx),
            )
            self._fitted_pairs[pair_name] = pair

            logger.info(
                "SMT %s: coint=%s (p=%.4f), beta=%.4f, z=%.2f, lead=%s→%s (lag=%d, r=%.2f)",
                pair_name, is_cointegrated, pvalue, hedge_ratio,
                current_zscore, lead_asset, lag_asset, opt_lag, lead_strength,
            )

        self._fitted = True
        logger.info(
            "SMT detector fitted: %d/%d pairs cointegrated",
            self.n_cointegrated, self.n_pairs,
        )
        return self

    # ── Detect: compute current divergence status ─────────────

    def detect(
        self,
        price_data: Optional[pd.DataFrame] = None,
    ) -> dict[str, SMTDivergenceResult]:
        """Detect SMT divergence for all cointegrated pairs.

        Computes the current spread z-score for each cointegrated pair
        and checks if it exceeds the divergence threshold.

        Args:
            price_data: Optional new price data. If None, uses fitted data.

        Returns:
            Dict of pair_name -> SMTDivergenceResult.
        """
        data = price_data if price_data is not None else self._price_data
        if data is None:
            logger.warning("SMT detector: no price data available")
            return {}

        results: dict[str, SMTDivergenceResult] = {}

        for pair_name, pair in self._fitted_pairs.items():
            if not pair.is_cointegrated:
                continue

            pa = data[pair.asset_a].dropna().values
            pb = data[pair.asset_b].dropna().values

            # Truncate to minimum length
            n = min(len(pa), len(pb))
            if n < 5:
                continue
            pa, pb = pa[-n:], pb[-n:]

            # Compute current spread
            spread = pa - pair.hedge_ratio * pb - pair.intercept
            current_spread = spread[-1]

            # Rolling z-score (use full-history mean/std from fit as baseline)
            # For live detection, use a rolling window for faster adaptation
            window = min(n, 20)
            if n >= window:
                recent_spread = spread[-window:]
                spread_mean = float(np.mean(recent_spread))
                spread_std = float(np.std(recent_spread))
            else:
                spread_mean = pair.spread_mean
                spread_std = pair.spread_std

            zscore = float((current_spread - spread_mean) / max(spread_std, 1e-12))

            # Determine divergence type
            divergence_detected = abs(zscore) > self.z_score_threshold
            divergence_type = "none"

            if divergence_detected:
                # Asset A moving up relative to B, or vice versa
                if zscore > self.z_score_threshold:
                    divergence_type = "breakdown_a_stronger"
                else:
                    divergence_type = "breakdown_a_weaker"

            # Confidence: how far beyond threshold
            confidence = min(abs(zscore) / self.z_score_threshold, 1.0) if divergence_detected else 0.0

            result = SMTDivergenceResult(
                pair_name=pair_name,
                asset_a=pair.asset_a,
                asset_b=pair.asset_b,
                is_cointegrated=True,
                divergence_detected=divergence_detected,
                divergence_type=divergence_type,
                zscore=round(zscore, 4),
                hedge_ratio=pair.hedge_ratio,
                lead_asset=pair.lead_asset,
                lag_asset=pair.lag_asset,
                lead_lag_lag=pair.optimal_lag,
                confidence=round(confidence, 4),
            )
            results[pair_name] = result

        self._last_detection = results

        n_divergent = sum(1 for r in results.values() if r.divergence_detected)
        if n_divergent > 0:
            logger.info(
                "SMT detection: %d/%d pairs divergent",
                n_divergent, len(results),
            )

        return results

    # ── Summary ───────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        """Get a full diagnostic summary of the detector state.

        Returns:
            Dict with pair statuses, cointegration counts, and divergence flags.
        """
        pair_statuses: dict[str, dict[str, Any]] = {}
        for pair_name, pair in self._fitted_pairs.items():
            pair_statuses[pair_name] = {
                "assets": f"{pair.asset_a}↔{pair.asset_b}",
                "cointegrated": pair.is_cointegrated,
                "pvalue": pair.coint_pvalue,
                "hedge_ratio": pair.hedge_ratio,
                "current_zscore": pair.current_zscore,
                "lead": pair.lead_asset,
                "lag": pair.lag_asset,
                "lead_lag": f"{pair.lead_asset}→{pair.lag_asset} (lag={pair.optimal_lag})",
            }

        # Latest detection results
        divergent_pairs = {
            name: r for name, r in self._last_detection.items()
            if r.divergence_detected
        }

        return {
            "fitted": self._fitted,
            "total_pairs": self.n_pairs,
            "cointegrated_pairs": self.n_cointegrated,
            "pairs": pair_statuses,
            "divergent_pairs": len(divergent_pairs),
            "divergent_details": {
                name: {
                    "type": r.divergence_type,
                    "zscore": r.zscore,
                    "confidence": r.confidence,
                    "lead": r.lead_asset,
                }
                for name, r in divergent_pairs.items()
            },
            "z_score_threshold": self.z_score_threshold,
            "coint_pvalue_threshold": self.coint_pvalue_threshold,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Compatibility with MasterQuantNanggroeEngine ──────────

    def has_any_divergence(self) -> bool:
        """Returns True if ANY tracked pair has divergence."""
        return any(r.divergence_detected for r in self._last_detection.values())

    def get_blocked_symbols(self) -> list[str]:
        """Returns symbols that should have buys blocked due to SMT divergence.

        If the leading asset is stronger and the lagging asset is weaker,
        buying the lagging asset carries SMT divergence risk.

        Returns:
            List of symbols to block buys on.
        """
        blocked: set[str] = set()
        for result in self._last_detection.values():
            if result.divergence_detected:
                # The lagging asset is at risk when divergence occurs
                if result.lag_asset:
                    blocked.add(result.lag_asset)
        return list(blocked)

    # ── Statistical methods ───────────────────────────────────

    def _test_cointegration(
        self,
        series_a: np.ndarray,
        series_b: np.ndarray,
    ) -> tuple[bool, float]:
        """Engle-Granger cointegration test.

        Tests whether series_a and series_b are cointegrated.
        H0: no cointegration. Low p-value → cointegrated.

        Args:
            series_a: Price series for asset A.
            series_b: Price series for asset B.

        Returns:
            Tuple of (is_cointegrated, p_value).
        """
        try:
            from statsmodels.tsa.stattools import coint

            _, pvalue, _ = coint(series_a, series_b)
            pvalue = float(pvalue)
            return pvalue < self.coint_pvalue_threshold, pvalue
        except Exception as e:
            logger.debug("Cointegration test failed: %s", e)
            return False, 1.0

    def _compute_hedge_ratio(
        self,
        series_a: np.ndarray,
        series_b: np.ndarray,
    ) -> tuple[float, float]:
        """Compute OLS hedge ratio: price_A = beta * price_B + intercept.

        Args:
            series_a: Price series for asset A (dependent variable).
            series_b: Price series for asset B (independent variable).

        Returns:
            Tuple of (beta, intercept).
        """
        try:
            import statsmodels.api as sm

            X = sm.add_constant(series_b)
            model = sm.OLS(series_a, X).fit()
            beta = float(model.params.iloc[1] if hasattr(model.params, 'iloc') else model.params[1])
            intercept = float(model.params.iloc[0] if hasattr(model.params, 'iloc') else model.params[0])
            return beta, intercept
        except Exception as e:
            logger.debug("OLS hedge ratio failed: %s", e)
            # Fallback: simple ratio
            return float(np.mean(series_a / np.maximum(series_b, 1e-12))), 0.0

    def _detect_lead_lag(
        self,
        series_a: np.ndarray,
        series_b: np.ndarray,
        name_a: str,
        name_b: str,
    ) -> tuple[str, str, float, int]:
        """Detect which asset leads using time-shifted cross-correlation.

        Bennett et al. (2022): compute cross-correlation at various lags,
        find the lag with maximum absolute correlation → the lead asset.

        Args:
            series_a: Price series for asset A.
            series_b: Price series for asset B.
            name_a: Symbol for asset A.
            name_b: Symbol for asset B.

        Returns:
            Tuple of (lead_asset_name, lag_asset_name,
                       cross_corr_at_optimal_lag, optimal_lag).
        """
        try:
            from scipy import signal

            # Use returns for stationarity
            ret_a = np.diff(np.log(np.maximum(series_a, 1e-12)))
            ret_b = np.diff(np.log(np.maximum(series_b, 1e-12)))

            if len(ret_a) < self._lead_lag_max_lag + 5:
                return name_a, name_b, 0.0, 0

            # Cross-correlation
            corr = signal.correlate(ret_a - ret_a.mean(), ret_b - ret_b.mean(),
                                    mode="same")
            corr /= max(len(ret_a), 1)
            # Only look at positive lags (A leading) and negative (B leading)
            mid = len(corr) // 2
            max_lag = min(self._lead_lag_max_lag, mid)

            # Positive lags: A leads B
            pos_lags = corr[mid:mid + max_lag]
            # Negative lags: B leads A
            neg_lags = corr[mid - max_lag + 1:mid + 1][::-1]

            max_pos = float(np.max(np.abs(pos_lags))) if len(pos_lags) > 0 else 0
            max_neg = float(np.max(np.abs(neg_lags))) if len(neg_lags) > 0 else 0

            if max_pos > max_neg and max_pos > 0.1:
                opt_lag = int(np.argmax(np.abs(pos_lags))) + 1
                return name_a, name_b, max_pos, opt_lag
            elif max_neg > 0.1:
                opt_lag = int(np.argmax(np.abs(neg_lags))) + 1
                return name_b, name_a, max_neg, opt_lag
            else:
                return name_a, name_b, 0.0, 0

        except Exception as e:
            logger.debug("Lead-lag detection failed: %s", e)
            return name_a, name_b, 0.0, 0
