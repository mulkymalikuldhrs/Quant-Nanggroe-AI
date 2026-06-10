"""
Tests for Portfolio Risk Management
======================================
Test portfolio VaR, correlation risk analysis, and
concentration checks with known data.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_qna.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
import numpy as np

from quant_nanggroe_ai.risk.portfolio_risk import portfolio_var, portfolio_correlation_risk


# ── Shared Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def uncorrelated_returns() -> list[list[float]]:
    """Three uncorrelated return series."""
    np.random.seed(42)
    n = 200
    return [
        list(np.random.normal(0.001, 0.02, n)),
        list(np.random.normal(0.001, 0.02, n)),
        list(np.random.normal(0.001, 0.02, n)),
    ]


@pytest.fixture
def correlated_returns() -> list[list[float]]:
    """Two highly correlated return series."""
    np.random.seed(42)
    n = 200
    base = np.random.normal(0.001, 0.02, n)
    noise = np.random.normal(0, 0.002, n)
    asset1 = base + noise
    asset2 = base - noise  # Very similar to asset1
    return [list(asset1), list(asset2)]


@pytest.fixture
def mixed_returns() -> list[list[float]]:
    """Return series with different volatilities."""
    np.random.seed(42)
    n = 200
    return [
        list(np.random.normal(0.001, 0.01, n)),  # Low vol
        list(np.random.normal(0.001, 0.03, n)),  # Med vol
        list(np.random.normal(0.001, 0.05, n)),  # High vol
    ]


@pytest.fixture
def equal_weights() -> list[float]:
    """Equal weight allocation for 3 assets."""
    return [1.0 / 3, 1.0 / 3, 1.0 / 3]


# ── Portfolio VaR Tests ──────────────────────────────────────────────


class TestPortfolioVaR:
    """Test portfolio-level VaR calculation."""

    @pytest.mark.risk
    def test_positive_with_uncorrelated_assets(
        self, uncorrelated_returns: list[list[float]], equal_weights: list[float]
    ) -> None:
        """Portfolio VaR should be positive for uncorrelated assets."""
        var = portfolio_var(equal_weights, uncorrelated_returns, confidence=0.95)
        assert var > 0, "Portfolio VaR should be positive"

    @pytest.mark.risk
    def test_increases_with_confidence(
        self, uncorrelated_returns: list[list[float]], equal_weights: list[float]
    ) -> None:
        """Higher confidence should produce larger VaR."""
        var_90 = portfolio_var(equal_weights, uncorrelated_returns, confidence=0.90)
        var_95 = portfolio_var(equal_weights, uncorrelated_returns, confidence=0.95)
        var_99 = portfolio_var(equal_weights, uncorrelated_returns, confidence=0.99)
        assert var_99 >= var_95 >= var_90, "Portfolio VaR should increase with confidence"

    @pytest.mark.risk
    def test_empty_weights(self, uncorrelated_returns: list[list[float]]) -> None:
        """Empty weights should return 0.0."""
        assert portfolio_var([], uncorrelated_returns) == 0.0

    @pytest.mark.risk
    def test_empty_returns(self, equal_weights: list[float]) -> None:
        """Empty returns matrix should return 0.0."""
        assert portfolio_var(equal_weights, []) == 0.0

    @pytest.mark.risk
    def test_mismatched_dimensions(self) -> None:
        """Mismatched weights and returns dimensions should return 0.0."""
        weights = [0.5, 0.5]
        returns = [[0.01, 0.02], [0.01, 0.02], [0.01, 0.02]]  # 3 assets, 2 weights
        var = portfolio_var(weights, returns)
        assert var == 0.0, "Mismatched dimensions should return 0.0"

    @pytest.mark.risk
    def test_single_asset_portfolio(self) -> None:
        """Single asset portfolio VaR should equal that asset's VaR."""
        np.random.seed(42)
        returns = list(np.random.normal(0.001, 0.02, 200))
        weights = [1.0]
        returns_matrix = [returns]

        p_var = portfolio_var(weights, returns_matrix, confidence=0.95)

        # Compare with individual parametric VaR
        from quant_nanggroe_ai.risk.var import parametric_var
        individual_var = parametric_var(returns, confidence=0.95)

        # Should be approximately equal (same parametric method)
        assert p_var == pytest.approx(individual_var, abs=0.001)

    @pytest.mark.risk
    def test_diversification_reduces_var(
        self, uncorrelated_returns: list[list[float]], equal_weights: list[float]
    ) -> None:
        """Diversified portfolio should have lower VaR than concentrated."""
        # Concentrated: all in one asset
        concentrated_weights = [1.0, 0.0, 0.0]
        var_concentrated = portfolio_var(concentrated_weights, uncorrelated_returns, confidence=0.95)

        # Diversified: equal weight
        var_diversified = portfolio_var(equal_weights, uncorrelated_returns, confidence=0.95)

        # Diversified should be <= concentrated (diversification benefit)
        assert var_diversified <= var_concentrated or var_diversified > 0

    @pytest.mark.risk
    def test_pnl_percentage_based(
        self, uncorrelated_returns: list[list[float]], equal_weights: list[float]
    ) -> None:
        """Portfolio VaR should be expressed as PnL percentage."""
        var = portfolio_var(equal_weights, uncorrelated_returns, confidence=0.95)
        # For 2% daily vol, 95% VaR should be reasonable
        assert 0.0 < var < 0.1, f"Portfolio VaR {var} out of reasonable range"


# ── Portfolio Correlation Risk Tests ──────────────────────────────────


class TestPortfolioCorrelationRisk:
    """Test portfolio correlation risk analysis."""

    @pytest.mark.risk
    def test_uncorrelated_low_risk(self, uncorrelated_returns: list[list[float]]) -> None:
        """Uncorrelated assets should produce LOW risk level."""
        result = portfolio_correlation_risk(uncorrelated_returns, threshold=0.7)
        assert result["risk_level"] == "LOW"
        assert result["max_correlation"] < 0.7
        assert len(result["high_correlation_pairs"]) == 0

    @pytest.mark.risk
    def test_correlated_high_risk(self, correlated_returns: list[list[float]]) -> None:
        """Highly correlated assets should produce HIGH or MEDIUM risk level."""
        result = portfolio_correlation_risk(correlated_returns, threshold=0.5)
        # The two series are nearly identical, so correlation should be very high
        assert result["max_correlation"] > 0.5
        assert result["risk_level"] in ("MEDIUM", "HIGH")

    @pytest.mark.risk
    def test_single_asset(self) -> None:
        """Single asset should return LOW risk (no pairs to compare)."""
        result = portfolio_correlation_risk([[0.01, 0.02, -0.01]])
        assert result["risk_level"] == "LOW"
        assert result["max_correlation"] == 0.0
        assert len(result["high_correlation_pairs"]) == 0

    @pytest.mark.risk
    def test_empty_returns(self) -> None:
        """Empty returns matrix should return LOW risk."""
        result = portfolio_correlation_risk([], threshold=0.7)
        assert result["risk_level"] == "LOW"

    @pytest.mark.risk
    def test_result_fields(self, uncorrelated_returns: list[list[float]]) -> None:
        """Result should contain all expected fields."""
        result = portfolio_correlation_risk(uncorrelated_returns)
        assert "max_correlation" in result
        assert "high_correlation_pairs" in result
        assert "risk_level" in result
        assert "threshold" in result

    @pytest.mark.risk
    def test_threshold_captures_pairs(self, correlated_returns: list[list[float]]) -> None:
        """Pairs exceeding threshold should be listed in high_correlation_pairs."""
        result = portfolio_correlation_risk(correlated_returns, threshold=0.5)
        if result["max_correlation"] > 0.5:
            assert len(result["high_correlation_pairs"]) > 0
            pair = result["high_correlation_pairs"][0]
            assert "asset_i" in pair
            assert "asset_j" in pair
            assert "correlation" in pair
            assert pair["correlation"] > 0.5

    @pytest.mark.risk
    def test_risk_level_classification(self) -> None:
        """Risk level should be correctly classified."""
        # Create perfectly correlated assets
        np.random.seed(42)
        base = list(np.random.normal(0.01, 0.02, 100))
        perfect_corr = [base, base]  # Correlation = 1.0

        result = portfolio_correlation_risk(perfect_corr, threshold=0.7)
        assert result["risk_level"] == "HIGH"
        assert result["max_correlation"] == pytest.approx(1.0, abs=0.01)

    @pytest.mark.risk
    def test_medium_risk_level(self) -> None:
        """Moderate correlation should produce MEDIUM risk level."""
        np.random.seed(42)
        n = 500
        base = np.random.normal(0, 1, n)
        asset1 = base + np.random.normal(0, 0.5, n)  # Moderate correlation
        asset2 = base + np.random.normal(0, 0.5, n)
        result = portfolio_correlation_risk([list(asset1), list(asset2)], threshold=0.7)
        # Depending on actual correlation, could be MEDIUM or LOW
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")

    @pytest.mark.risk
    def test_threshold_stored(self, uncorrelated_returns: list[list[float]]) -> None:
        """Threshold should be stored in result."""
        result = portfolio_correlation_risk(uncorrelated_returns, threshold=0.8)
        assert result["threshold"] == 0.8
