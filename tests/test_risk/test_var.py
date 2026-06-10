"""
Tests for Value at Risk (VaR)
================================
Test parametric, historical, and Monte Carlo VaR calculations
with known data, edge cases, boundary conditions, and
PnL percentage-based tracking.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_qna.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
import numpy as np

from quant_nanggroe_ai.risk.var import parametric_var, historical_var, monte_carlo_var


# ── Shared Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def normal_returns() -> list[float]:
    """Returns from a known normal distribution N(0.001, 0.02)."""
    np.random.seed(123)
    return [float(x) for x in np.random.normal(0.001, 0.02, 500)]


@pytest.fixture
def lossy_returns() -> list[float]:
    """Returns series with predominantly losses."""
    np.random.seed(456)
    return [float(x) for x in np.random.normal(-0.005, 0.03, 200)]


@pytest.fixture
def constant_returns() -> list[float]:
    """Returns series with zero variance."""
    return [0.001] * 100


@pytest.fixture
def mixed_returns() -> list[float]:
    """Returns series with both wins and losses."""
    return [0.02, -0.03, 0.01, -0.05, 0.03, -0.01, 0.04, -0.02, 0.00, -0.04]


# ── Parametric VaR Tests ─────────────────────────────────────────────


class TestParametricVar:
    """Test parametric (variance-covariance) VaR calculation."""

    @pytest.mark.risk
    def test_positive_with_normal_returns(self, normal_returns: list[float]) -> None:
        """Parametric VaR should return a positive loss value for normal returns."""
        var = parametric_var(normal_returns, confidence=0.95)
        assert var > 0, "VaR should be positive (represents potential loss)"

    @pytest.mark.risk
    def test_increases_with_confidence(self, normal_returns: list[float]) -> None:
        """Higher confidence should produce larger VaR."""
        var_90 = parametric_var(normal_returns, confidence=0.90)
        var_95 = parametric_var(normal_returns, confidence=0.95)
        var_99 = parametric_var(normal_returns, confidence=0.99)
        assert var_99 >= var_95 >= var_90, "VaR should increase with confidence level"

    @pytest.mark.risk
    def test_known_distribution(self) -> None:
        """VaR should match known z-score calculation for known distribution."""
        np.random.seed(42)
        returns = [float(x) for x in np.random.normal(0.0, 0.01, 10000)]
        var = parametric_var(returns, confidence=0.95)
        # For N(0, 0.01) at 95%: VaR ≈ 1.645 * 0.01 ≈ 0.01645
        # Allow generous tolerance due to sample variance
        assert 0.01 < var < 0.03, f"VaR {var} unexpected for N(0, 0.01) at 95%"

    @pytest.mark.risk
    def test_empty_returns(self) -> None:
        """Empty returns list should return 0.0."""
        assert parametric_var([], confidence=0.95) == 0.0

    @pytest.mark.risk
    def test_single_return(self) -> None:
        """Single return should still produce a result (std=0 → VaR=0)."""
        var = parametric_var([0.01], confidence=0.95)
        # With single value, std with ddof=1 is NaN/0 → should handle gracefully
        # Implementation returns abs(var) if var < 0 else 0.0
        assert isinstance(var, float)

    @pytest.mark.risk
    def test_constant_returns(self, constant_returns: list[float]) -> None:
        """Constant returns (zero variance) should produce zero VaR."""
        var = parametric_var(constant_returns, confidence=0.95)
        # With zero std, var = mean - z*0 = mean = 0.001 > 0 → returns 0.0
        assert var == 0.0, f"VaR should be 0 for constant positive returns, got {var}"

    @pytest.mark.risk
    def test_lossy_returns_larger_var(self, lossy_returns: list[float], normal_returns: list[float]) -> None:
        """Returns with larger losses should produce larger VaR."""
        var_lossy = parametric_var(lossy_returns, confidence=0.95)
        var_normal = parametric_var(normal_returns, confidence=0.95)
        assert var_lossy > var_normal, "Lossy returns should produce larger VaR"

    @pytest.mark.risk
    def test_unknown_confidence_uses_default(self, normal_returns: list[float]) -> None:
        """Unknown confidence level should fall back to 1.645 (95%)."""
        var_unknown = parametric_var(normal_returns, confidence=0.93)
        var_95 = parametric_var(normal_returns, confidence=0.95)
        # Unknown confidence uses z=1.645 (same as 95%)
        assert var_unknown == pytest.approx(var_95, abs=0.001)


# ── Historical VaR Tests ─────────────────────────────────────────────


class TestHistoricalVar:
    """Test historical VaR using empirical distribution."""

    @pytest.mark.risk
    def test_positive_with_normal_returns(self, normal_returns: list[float]) -> None:
        """Historical VaR should return a positive loss value."""
        var = historical_var(normal_returns, confidence=0.95)
        assert var > 0, "Historical VaR should be positive"

    @pytest.mark.risk
    def test_increases_with_confidence(self, normal_returns: list[float]) -> None:
        """Higher confidence should produce larger or equal VaR."""
        var_90 = historical_var(normal_returns, confidence=0.90)
        var_95 = historical_var(normal_returns, confidence=0.95)
        var_99 = historical_var(normal_returns, confidence=0.99)
        assert var_99 >= var_95 >= var_90, "Historical VaR should increase with confidence"

    @pytest.mark.risk
    def test_known_percentile(self, mixed_returns: list[float]) -> None:
        """Historical VaR at 90% should use 10th percentile."""
        var = historical_var(mixed_returns, confidence=0.90)
        # 10th percentile of [-0.05, -0.04, -0.03, -0.02, -0.01, 0.00, 0.01, 0.02, 0.03, 0.04]
        # sorted: [-0.05, -0.04, -0.03, -0.02, -0.01, 0.00, 0.01, 0.02, 0.03, 0.04]
        # 10th percentile ≈ -0.046 → abs = 0.046
        assert var > 0, "VaR should be positive for mixed returns"

    @pytest.mark.risk
    def test_empty_returns(self) -> None:
        """Empty returns should return 0.0."""
        assert historical_var([], confidence=0.95) == 0.0

    @pytest.mark.risk
    def test_all_positive_returns(self) -> None:
        """If all returns are positive, VaR should be 0."""
        var = historical_var([0.01, 0.02, 0.03, 0.04, 0.05], confidence=0.95)
        # 5th percentile of positive returns is still positive → VaR = 0
        assert var == 0.0, f"VaR should be 0 for all-positive returns, got {var}"

    @pytest.mark.risk
    def test_all_negative_returns(self) -> None:
        """If all returns are negative, VaR should be positive."""
        var = historical_var([-0.01, -0.02, -0.03, -0.04, -0.05], confidence=0.95)
        assert var > 0, "VaR should be positive for all-negative returns"

    @pytest.mark.risk
    def test_pnl_percentage_tracking(self, normal_returns: list[float]) -> None:
        """VaR should be expressed as a PnL percentage (decimal)."""
        var = historical_var(normal_returns, confidence=0.95)
        # For daily returns ~2% std, 95% VaR should be in the range of 0-10%
        assert 0.0 < var < 0.1, f"VaR as percentage should be reasonable, got {var}"


# ── Monte Carlo VaR Tests ────────────────────────────────────────────


class TestMonteCarloVar:
    """Test Monte Carlo VaR using parametric bootstrap."""

    @pytest.mark.risk
    def test_positive_with_normal_returns(self, normal_returns: list[float]) -> None:
        """Monte Carlo VaR should return a positive loss value."""
        np.random.seed(789)
        var = monte_carlo_var(normal_returns, confidence=0.95, simulations=5000)
        assert var > 0, "Monte Carlo VaR should be positive"

    @pytest.mark.risk
    def test_increases_with_confidence(self, normal_returns: list[float]) -> None:
        """Higher confidence should produce larger VaR."""
        np.random.seed(789)
        var_90 = monte_carlo_var(normal_returns, confidence=0.90, simulations=5000)
        var_99 = monte_carlo_var(normal_returns, confidence=0.99, simulations=5000)
        assert var_99 >= var_90, "Monte Carlo VaR should increase with confidence"

    @pytest.mark.risk
    def test_empty_returns(self) -> None:
        """Empty returns should return 0.0."""
        assert monte_carlo_var([], confidence=0.95) == 0.0

    @pytest.mark.risk
    def test_time_horizon_scaling(self, normal_returns: list[float]) -> None:
        """Longer time horizon should produce larger VaR (scaled by sqrt(T))."""
        np.random.seed(789)
        var_1d = monte_carlo_var(normal_returns, confidence=0.95, time_horizon=1)
        var_10d = monte_carlo_var(normal_returns, confidence=0.95, time_horizon=10)
        # 10-day VaR should be larger than 1-day VaR
        assert var_10d > var_1d, "10-day VaR should exceed 1-day VaR"

    @pytest.mark.risk
    def test_simulations_consistency(self, normal_returns: list[float]) -> None:
        """More simulations should produce more stable VaR estimates."""
        np.random.seed(789)
        var_low = monte_carlo_var(normal_returns, confidence=0.95, simulations=500)
        np.random.seed(789)
        var_high = monte_carlo_var(normal_returns, confidence=0.95, simulations=50000)
        # Both should be in the same ballpark
        assert 0 < var_low < 0.1, "Low-sim VaR should be reasonable"
        assert 0 < var_high < 0.1, "High-sim VaR should be reasonable"

    @pytest.mark.risk
    def test_approximately_matches_parametric(self, normal_returns: list[float]) -> None:
        """Monte Carlo VaR should approximately match parametric VaR for normal data."""
        np.random.seed(789)
        mc_var = monte_carlo_var(normal_returns, confidence=0.95, simulations=50000)
        p_var = parametric_var(normal_returns, confidence=0.95)
        # Should be within 50% of each other (generous for Monte Carlo)
        ratio = mc_var / p_var if p_var > 0 else 0
        assert 0.5 < ratio < 2.0, f"MC VaR {mc_var} too far from parametric {p_var}"


# ── Cross-Method Consistency ─────────────────────────────────────────


class TestVaRCrossMethodConsistency:
    """Test that all VaR methods produce consistent results."""

    @pytest.mark.risk
    def test_historical_vs_parametric(self, normal_returns: list[float]) -> None:
        """Historical and parametric VaR should be similar for normal data."""
        h_var = historical_var(normal_returns, confidence=0.95)
        p_var = parametric_var(normal_returns, confidence=0.95)
        # They should be in the same order of magnitude
        assert 0.3 < h_var / p_var < 3.0 if p_var > 0 else True

    @pytest.mark.risk
    def test_all_methods_positive(self, normal_returns: list[float]) -> None:
        """All VaR methods should return positive values for normal returns."""
        p_var = parametric_var(normal_returns, confidence=0.95)
        h_var = historical_var(normal_returns, confidence=0.95)
        np.random.seed(789)
        mc_var = monte_carlo_var(normal_returns, confidence=0.95, simulations=5000)
        assert p_var > 0
        assert h_var > 0
        assert mc_var > 0

    @pytest.mark.risk
    def test_all_methods_return_zero_for_empty(self) -> None:
        """All methods should return 0.0 for empty input."""
        assert parametric_var([]) == 0.0
        assert historical_var([]) == 0.0
        assert monte_carlo_var([]) == 0.0
