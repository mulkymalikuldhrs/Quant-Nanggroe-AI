"""Tests for Fama-French 5-factor model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe_ai.factors.fama_french import (
    FamaFrenchModel,
    compute_mkt_rf,
    compute_smb,
    compute_hml,
    compute_rmw,
    compute_cma,
    FAMA_FRENCH_FACTORS,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_panel() -> dict[str, pd.DataFrame]:
    """Generate a synthetic panel with 4 instruments, 300 days."""
    np.random.seed(42)
    n_days = 300
    n_inst = 4
    dates = pd.date_range("2023-01-01", periods=n_days, freq="B")
    instruments = [f"INST_{i}" for i in range(n_inst)]

    close = pd.DataFrame(
        100.0 + np.cumsum(np.random.randn(n_days, n_inst) * 0.5, axis=0),
        index=dates, columns=instruments,
    )
    volume = pd.DataFrame(
        np.random.randint(100_000, 10_000_000, (n_days, n_inst)).astype(float),
        index=dates, columns=instruments,
    )
    high = close * (1 + np.abs(np.random.randn(n_days, n_inst) * 0.01))
    low = close * (1 - np.abs(np.random.randn(n_days, n_inst) * 0.01))

    return {
        "close": close,
        "high": high,
        "low": low,
        "volume": volume,
    }


@pytest.fixture
def sample_close(sample_panel) -> pd.DataFrame:
    return sample_panel["close"]


@pytest.fixture
def sample_volume(sample_panel) -> pd.DataFrame:
    return sample_panel["volume"]


# ── Individual Factors ────────────────────────────────────────────────────

class TestComputeMktRf:
    def test_returns_dataframe(self, sample_close):
        result = compute_mkt_rf(sample_close)
        assert isinstance(result, pd.DataFrame)

    def test_shape_matches_close(self, sample_close):
        result = compute_mkt_rf(sample_close)
        assert result.shape == sample_close.shape

    def test_values_finite(self, sample_close):
        result = compute_mkt_rf(sample_close)
        finite = result.dropna()
        assert np.isfinite(finite.values).all()


class TestComputeSmb:
    def test_returns_dataframe(self, sample_close, sample_volume):
        result = compute_smb(sample_close, sample_volume)
        assert isinstance(result, pd.DataFrame)

    def test_values_finite(self, sample_close, sample_volume):
        result = compute_smb(sample_close, sample_volume)
        finite = result.dropna()
        assert np.isfinite(finite.values).all()


class TestComputeHml:
    def test_returns_dataframe(self, sample_close):
        result = compute_hml(sample_close)
        assert isinstance(result, pd.DataFrame)


class TestComputeRmw:
    def test_returns_dataframe(self, sample_close):
        result = compute_rmw(sample_close)
        assert isinstance(result, pd.DataFrame)


class TestComputeCma:
    def test_returns_dataframe(self, sample_volume):
        result = compute_cma(sample_volume)
        assert isinstance(result, pd.DataFrame)


# ── FamaFrenchModel ───────────────────────────────────────────────────────

class TestFamaFrenchModel:
    def test_compute_all(self, sample_panel):
        model = FamaFrenchModel()
        results = model.compute_all(sample_panel)
        assert isinstance(results, dict)
        assert "MKT_RF" in results
        assert "SMB" in results
        assert "HML" in results
        assert "RMW" in results
        assert "CMA" in results

    def test_factor_regression(self, sample_panel):
        model = FamaFrenchModel()
        returns = sample_panel["close"].pct_change().iloc[1:]
        factors = model.compute_all(sample_panel)
        # Align factors with returns
        for key in factors:
            factors[key] = factors[key].reindex(returns.index)
        result = model.factor_regression(returns, factors)
        assert isinstance(result, dict)

    def test_registry_has_5_factors(self):
        assert len(FAMA_FRENCH_FACTORS) == 5


# ── Edge Cases ────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_instrument(self):
        np.random.seed(42)
        n = 200
        dates = pd.date_range("2023-01-01", periods=n, freq="B")
        close = pd.DataFrame(
            100.0 + np.cumsum(np.random.randn(n) * 0.5),
            index=dates, columns=["INST_0"],
        )
        result = compute_mkt_rf(close)
        assert isinstance(result, pd.DataFrame)
