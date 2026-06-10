"""
Tests for Alpha101 Factors
============================
Test each alpha factor with sample data, verify alpha020 uses correct
`low` parameter, and check registry completeness.
"""

from __future__ import annotations

import pytest
import numpy as np
import pandas as pd

from quant_nanggroe_ai.factors.alpha101 import (
    alpha001,
    alpha002,
    alpha003,
    alpha006,
    alpha012,
    alpha014,
    alpha015,
    alpha020,
    alpha023,
    alpha026,
    ALPHA_FACTORS,
)
from quant_nanggroe_ai.factors.registry import FactorRegistry


# ── Shared fixtures ────────────────────────────────────────────────────


@pytest.fixture
def sample_data() -> dict[str, pd.Series]:
    """Generate sample OHLCV + returns data for factor testing."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="D")

    close = pd.Series(np.cumsum(np.random.normal(0.1, 1.0, n)) + 100, index=dates)
    open_ = close + np.random.normal(0, 0.5, n)
    high = close + abs(np.random.normal(0, 1.0, n))
    low = close - abs(np.random.normal(0, 1.0, n))
    volume = pd.Series(np.random.lognormal(10, 1, n), index=dates)
    returns = close.pct_change()

    return {
        "close": close,
        "open": open_,
        "high": high,
        "low": low,
        "volume": volume,
        "returns": returns,
    }


# ── Individual Factor Tests ────────────────────────────────────────────


class TestAlpha001:
    """Alpha#1: Ts_ArgMax based factor."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha001(sample_data["close"], sample_data["returns"], sample_data["volume"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])

    def test_values_in_range(self, sample_data: dict) -> None:
        """Result should be roughly in [-0.5, 0.5] range (rank - 0.5)."""
        result = alpha001(sample_data["close"], sample_data["returns"], sample_data["volume"])
        valid = result.dropna()
        if len(valid) > 0:
            assert valid.min() >= -0.6
            assert valid.max() <= 0.6


class TestAlpha002:
    """Alpha#2: Correlation of delta log volume and price ratio."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha002(sample_data["close"], sample_data["open"], sample_data["volume"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])


class TestAlpha003:
    """Alpha#3: Correlation of rank(open) and rank(volume)."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha003(sample_data["close"], sample_data["open"], sample_data["volume"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])


class TestAlpha006:
    """Alpha#6: Correlation of open and volume."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha006(sample_data["close"], sample_data["open"], sample_data["volume"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])


class TestAlpha012:
    """Alpha#12: Sign of volume delta * negative close delta."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha012(sample_data["close"], sample_data["volume"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])


class TestAlpha014:
    """Alpha#14: Rank of delta returns * correlation of open and volume."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha014(sample_data["close"], sample_data["open"], sample_data["volume"], sample_data["returns"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])


class TestAlpha015:
    """Alpha#15: Sum of rank correlation of high and volume."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha015(sample_data["close"], sample_data["high"], sample_data["volume"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])


class TestAlpha020:
    """Alpha#20: Uses open, high, low, close — tests the `low` parameter."""

    def test_returns_series(self, sample_data: dict) -> None:
        """alpha020 must accept close, open, high, low parameters."""
        result = alpha020(sample_data["close"], sample_data["open"], sample_data["high"], sample_data["low"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])

    def test_uses_low_parameter(self, sample_data: dict) -> None:
        """Verify alpha020 actually uses the `low` parameter (not ignoring it)."""
        result_with_low = alpha020(
            sample_data["close"], sample_data["open"], sample_data["high"], sample_data["low"]
        )
        # Create a different low series — result should differ
        different_low = sample_data["low"] * 0.9
        result_different_low = alpha020(
            sample_data["close"], sample_data["open"], sample_data["high"], different_low
        )
        # The results should not be identical since low is different
        valid_mask = result_with_low.notna() & result_different_low.notna()
        if valid_mask.sum() > 0:
            assert not result_with_low[valid_mask].equals(result_different_low[valid_mask])

    def test_callable_signature(self) -> None:
        """alpha020 should accept (close, open_, high, low) as parameters."""
        import inspect
        sig = inspect.signature(alpha020)
        params = list(sig.parameters.keys())
        assert "close" in params
        assert "open_" in params
        assert "high" in params
        assert "low" in params


class TestAlpha023:
    """Alpha#23: High price relative to SMA(20)."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha023(sample_data["high"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["high"])


class TestAlpha026:
    """Alpha#26: ts_max of correlation of volume rank and high rank."""

    def test_returns_series(self, sample_data: dict) -> None:
        result = alpha026(sample_data["close"], sample_data["high"], sample_data["volume"], sample_data["returns"])
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data["close"])


# ── Registry Completeness ─────────────────────────────────────────────


class TestAlphaRegistry:
    """Test the ALPHA_FACTORS registry completeness."""

    def test_registry_has_all_factors(self) -> None:
        """Registry should contain all 10 alpha factors."""
        expected = {
            "alpha001", "alpha002", "alpha003", "alpha006",
            "alpha012", "alpha014", "alpha015", "alpha020",
            "alpha023", "alpha026",
        }
        assert set(ALPHA_FACTORS.keys()) == expected

    def test_registry_values_are_callable(self) -> None:
        """All registry values must be callable functions."""
        for name, fn in ALPHA_FACTORS.items():
            assert callable(fn), f"{name} is not callable"

    @pytest.mark.parametrize("factor_name", [
        "alpha001", "alpha002", "alpha003", "alpha006",
        "alpha012", "alpha014", "alpha015", "alpha020",
        "alpha023", "alpha026",
    ])
    def test_individual_factor_in_registry(self, factor_name: str) -> None:
        """Each expected factor should be present in the registry."""
        assert factor_name in ALPHA_FACTORS

    def test_factor_registry_class(self) -> None:
        """FactorRegistry should support register/get/list_factors."""
        FactorRegistry.register("test_factor", lambda x: x * 2)
        assert FactorRegistry.get("test_factor") is not None
        assert "test_factor" in FactorRegistry.list_factors()
        result = FactorRegistry.compute("test_factor", x=5)
        assert result == 10
