"""
Tests for :mod:`quant_nanggroe.core.intermarket.lead_lag`.

Uses synthetic price series to avoid live network dependency.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.core.intermarket.lead_lag import (
    DEFAULT_MAX_LAG,
    DEFAULT_WINDOWS,
    LeadLagResult,
    measure_lead_lag,
    matrix_to_rows,
    build_lead_lag_matrix,
)


def _synthetic_lead_lag(
    n: int = 300,
    seed: int = 7,
    lead_candles: int = 3,
    noise: float = 0.05,
    base: float = 100.0,
):
    """Generate two synchronized price Series with a known lead-lag.

    ``alpha`` leads by ``lead_candles`` (positive => alpha first).
    """
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0, noise, size=n)
    alpha = base + np.cumsum(returns)

    beta = np.empty_like(alpha)
    beta[:lead_candles] = alpha[:lead_candles]
    beta[lead_candles:] = alpha[:-lead_candles] + rng.normal(0.0, noise * 0.5, size=n - lead_candles)

    idx = pd.date_range("2024-01-01", periods=n, freq="1D")
    return pd.Series(alpha, index=idx, name="ALPHA"), pd.Series(beta, index=idx, name="BETA"), lead_candles


class TestMeasureLeadLag:
    def test_synthetic_positive_lead_detected(self):
        alpha, beta, expected_lag = _synthetic_lead_lag(lead_candles=4, noise=0.04)
        result = measure_lead_lag(alpha, beta, max_lag=DEFAULT_MAX_LAG)
        assert result["lead_asset"] == "ALPHA"
        assert result["lag_asset"] == "BETA"
        assert result["lag"] == expected_lag
        assert 0.0 <= result["confidence"] <= 1.0

    def test_synthetic_beta_lead_detected(self):
        alpha, beta, expected_lag = _synthetic_lead_lag(lead_candles=5, noise=0.04)
        # alpha leads beta regardless of call order, lag is symmetric.
        result = measure_lead_lag(beta, alpha, max_lag=DEFAULT_MAX_LAG)
        assert result["lead_asset"] == "ALPHA"
        assert result["lag_asset"] == "BETA"
        assert result["lag"] == expected_lag

    def test_insufficient_data(self):
        short = pd.Series([1.0, 2.0])
        result = measure_lead_lag(short, short, max_lag=3)
        assert result["confidence"] == 0.0
        assert result["lag"] == 0

    def test_constant_series(self):
        idx = pd.date_range("2024-01-01", periods=120, freq="1D")
        a = pd.Series(100.0, index=idx)
        b = pd.Series(200.0, index=idx)
        result = measure_lead_lag(a, b, max_lag=5)
        assert result["confidence"] == 0.0

    def test_ndarray_input(self):
        a, b, _ = _synthetic_lead_lag(lead_candles=3, noise=0.03)
        res_arr = measure_lead_lag(a.values, b.values, max_lag=DEFAULT_MAX_LAG)
        assert res_arr["confidence"] > 0.0

    def test_output_keys(self):
        a, b, _ = _synthetic_lead_lag()
        result = measure_lead_lag(a, b, max_lag=7)
        assert set(result.keys()) == {"lead_asset", "lag_asset", "lag", "confidence"}


class TestLeadLagMatrix:
    def test_build_matrix_shape(self):
        a, b, _ = _synthetic_lead_lag(lead_candles=2, noise=0.02)
        s = pd.DataFrame({"A": a, "B": b})
        # Patch network path by monkeypatching cache/fetch
        import quant_nanggroe.core.intermarket.lead_lag as mod
        original = mod._fetch_prices
        mod._fetch_prices = lambda symbol, lookback_days=540: s[symbol] if symbol in s.columns else None
        try:
            matrix = build_lead_lag_matrix(windows=DEFAULT_WINDOWS, max_lag=DEFAULT_MAX_LAG, universe=["A", "B"])
            assert "A" in matrix and "B" in matrix
            assert any(len(v) > 0 for v in matrix["A"].values())
        finally:
            mod._fetch_prices = original

    def test_matrix_to_rows_dataframe(self):
        a, b, _ = _synthetic_lead_lag(lead_candles=2, noise=0.02)
        df = matrix_to_rows({"A": {"B": [LeadLagResult("A", "B", 2, 0.8, 30, 0.8)]}})
        assert len(df) == 1
        assert df.loc[0, "asset_a"] == "A"
        assert df.loc[0, "window"] == 30

    def test_matrix_min_confidence_filter(self):
        rows = matrix_to_rows({
            "A": {"B": [
                LeadLagResult("A", "B", 1, 0.9, 30, 0.9),
                LeadLagResult("A", "B", 2, 0.1, 60, 0.1),
            ]}
        }, min_confidence=0.5)
        assert len(rows) == 1
        assert float(rows.loc[0, "confidence"]) == pytest.approx(0.9)
