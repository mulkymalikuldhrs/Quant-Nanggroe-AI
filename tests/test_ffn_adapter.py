"""Tests for ffn analytics adapter (QS020 research distilled).

Wraps ffn.calc_stats() into a clean dict for QNA reporting/tear-sheets.
"""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.analytics.ffn_adapter import (
    compute_stats,
    monthly_returns_table,
)


@pytest.fixture
def synthetic_returns() -> pd.Series:
    """Deterministic daily returns series (500 days)."""
    rng = np.random.default_rng(7)
    return pd.Series(
        rng.normal(0.0004, 0.01, 500),
        index=pd.date_range("2024-01-01", periods=500, freq="B"),
    )


class TestComputeStats:
    def test_returns_expected_keys(self, synthetic_returns):
        stats = compute_stats(synthetic_returns)
        for key in (
            "total_return",
            "cagr",
            "sharpe",
            "sortino",
            "calmar",
            "max_drawdown",
            "volatility",
        ):
            assert key in stats, f"missing key {key}"

    def test_values_are_finite_and_plausible(self, synthetic_returns):
        stats = compute_stats(synthetic_returns)
        for key, value in stats.items():
            assert np.isfinite(value), f"{key} not finite: {value}"
        assert stats["total_return"] > 0  # positive drift
        assert -1.0 < stats["max_drawdown"] <= 0.0
        assert stats["sharpe"] > 0


class TestMonthlyReturnsTable:
    def test_returns_dataframe(self, synthetic_returns):
        table = monthly_returns_table(synthetic_returns)
        assert isinstance(table, pd.DataFrame)
        assert not table.empty

    def test_columns_are_months(self, synthetic_returns):
        table = monthly_returns_table(synthetic_returns)
        assert "Jan" in table.columns
        assert table.index.name is not None  # year index

    def test_constant_returns_are_identical(self):
        n = 365
        flat = pd.Series(
            [0.001] * n,
            index=pd.date_range("2024-01-01", periods=n, freq="B"),
        )
        table = monthly_returns_table(flat)
        # All non-empty cells equal 0.001 within float tolerance
        values = table.values[~np.isnan(table.values)]
        np.testing.assert_allclose(values, 0.001, rtol=1e-6)
