"""
Tests for Position Sizing — Kelly Criterion & Risk Parity
===========================================================
Test Kelly Criterion position sizing with fractional Kelly,
edge cases (zero loss, no edge), and risk parity weight allocation.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_qna.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
import numpy as np

from quant_nanggroe_ai.risk.position_sizing import kelly_criterion_size, risk_parity_weights


# ── Kelly Criterion Tests ────────────────────────────────────────────


class TestKellyCriterionSize:
    """Test Kelly Criterion position sizing with fractional Kelly."""

    @pytest.mark.risk
    def test_positive_edge(self) -> None:
        """With a positive edge, Kelly should recommend a position."""
        result = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0, fraction=0.25, account_balance=10000.0
        )
        assert result["position_size"] > 0
        assert result["kelly_pct"] > 0
        assert result["fractional_kelly_pct"] > 0
        assert "recommendation" in result

    @pytest.mark.risk
    def test_no_edge(self) -> None:
        """With 50% win rate and 1:1 ratio, Kelly should be 0 or near-zero."""
        result = kelly_criterion_size(
            win_rate=0.5, avg_win=100.0, avg_loss=100.0, fraction=0.25, account_balance=10000.0
        )
        # Kelly = 0.5 - (0.5/1.0) = 0
        assert result["kelly_pct"] <= 0.0
        assert result["position_size"] == 0.0

    @pytest.mark.risk
    def test_zero_loss_returns_no_trade(self) -> None:
        """Zero avg_loss should return NO_TRADE (can't compute ratio)."""
        result = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=0.0, fraction=0.25, account_balance=10000.0
        )
        assert result["position_size"] == 0.0
        assert result["recommendation"] == "NO_TRADE"

    @pytest.mark.risk
    def test_zero_win_rate_returns_no_trade(self) -> None:
        """Zero win rate should return NO_TRADE."""
        result = kelly_criterion_size(
            win_rate=0.0, avg_win=200.0, avg_loss=100.0, fraction=0.25, account_balance=10000.0
        )
        assert result["position_size"] == 0.0
        assert result["recommendation"] == "NO_TRADE"

    @pytest.mark.risk
    def test_win_rate_of_one_returns_no_trade(self) -> None:
        """Win rate of 1.0 (100%) should return NO_TRADE (division by zero risk)."""
        result = kelly_criterion_size(
            win_rate=1.0, avg_win=200.0, avg_loss=100.0, fraction=0.25, account_balance=10000.0
        )
        assert result["recommendation"] == "NO_TRADE"

    @pytest.mark.risk
    def test_fractional_kelly_reduces_size(self) -> None:
        """Quarter Kelly should produce 25% of full Kelly position size."""
        full_result = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0, fraction=1.0, account_balance=10000.0
        )
        quarter_result = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0, fraction=0.25, account_balance=10000.0
        )
        assert quarter_result["position_size"] == pytest.approx(
            full_result["position_size"] * 0.25, abs=1.0
        )

    @pytest.mark.risk
    def test_position_size_scales_with_balance(self) -> None:
        """Larger account balance should produce proportionally larger position."""
        result_10k = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0, fraction=0.25, account_balance=10000.0
        )
        result_20k = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0, fraction=0.25, account_balance=20000.0
        )
        assert result_20k["position_size"] == pytest.approx(
            result_10k["position_size"] * 2.0, abs=1.0
        )

    @pytest.mark.risk
    def test_negative_kelly_capped_at_zero(self) -> None:
        """Negative full Kelly (no edge) should produce zero position."""
        result = kelly_criterion_size(
            win_rate=0.3, avg_win=50.0, avg_loss=100.0, fraction=0.25, account_balance=10000.0
        )
        # Kelly = 0.3 - (0.7/0.5) = 0.3 - 1.4 = -1.1 → capped to 0
        assert result["fractional_kelly_pct"] >= 0.0
        assert result["position_size"] >= 0.0

    @pytest.mark.risk
    def test_result_fields(self) -> None:
        """Result should contain all expected fields."""
        result = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0, fraction=0.25, account_balance=10000.0
        )
        assert "position_size" in result
        assert "kelly_pct" in result
        assert "fractional_kelly_pct" in result
        assert "fraction" in result
        assert "recommendation" in result

    @pytest.mark.risk
    def test_fraction_field_matches_input(self) -> None:
        """The 'fraction' field in the result should match the input."""
        result = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0, fraction=0.33, account_balance=10000.0
        )
        assert result["fraction"] == 0.33

    @pytest.mark.risk
    def test_known_kelly_calculation(self) -> None:
        """Test Kelly with known calculation: win_rate=0.6, W=2, L=1."""
        result = kelly_criterion_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0, fraction=1.0, account_balance=10000.0
        )
        # r = 200/100 = 2.0
        # full_kelly = 0.6 - (0.4/2.0) = 0.6 - 0.2 = 0.4
        assert result["kelly_pct"] == pytest.approx(0.4, abs=0.001)
        # position_size = 10000 * 0.4 = 4000
        assert result["position_size"] == pytest.approx(4000.0, abs=1.0)


# ── Risk Parity Tests ────────────────────────────────────────────────


class TestRiskParityWeights:
    """Test risk parity weight allocation."""

    @pytest.mark.risk
    def test_equal_volatility_equal_weights(self) -> None:
        """Assets with equal volatility should get equal weights."""
        np.random.seed(42)
        ret1 = list(np.random.normal(0.01, 0.02, 100))
        ret2 = list(np.random.normal(0.01, 0.02, 100))
        ret3 = list(np.random.normal(0.01, 0.02, 100))
        weights = risk_parity_weights([ret1, ret2, ret3])
        assert len(weights) == 3
        assert sum(weights) == pytest.approx(1.0, abs=0.01)
        # Equal volatility → roughly equal weights
        for w in weights:
            assert w == pytest.approx(1.0 / 3, abs=0.05)

    @pytest.mark.risk
    def test_higher_vol_lower_weight(self) -> None:
        """Asset with higher volatility should get lower weight."""
        np.random.seed(42)
        low_vol = list(np.random.normal(0.01, 0.01, 100))   # σ = 1%
        high_vol = list(np.random.normal(0.01, 0.05, 100))  # σ = 5%
        weights = risk_parity_weights([low_vol, high_vol])
        assert len(weights) == 2
        assert weights[0] > weights[1], "Low-vol asset should get higher weight"

    @pytest.mark.risk
    def test_weights_sum_to_one(self) -> None:
        """All weights should sum to approximately 1.0."""
        np.random.seed(42)
        returns = [list(np.random.normal(0.01, 0.02 * (i + 1), 100)) for i in range(5)]
        weights = risk_parity_weights(returns)
        assert sum(weights) == pytest.approx(1.0, abs=0.01)

    @pytest.mark.risk
    def test_all_weights_positive(self) -> None:
        """All weights should be positive."""
        np.random.seed(42)
        returns = [list(np.random.normal(0.01, 0.02 * (i + 1), 100)) for i in range(4)]
        weights = risk_parity_weights(returns)
        for w in weights:
            assert w > 0

    @pytest.mark.risk
    def test_empty_input(self) -> None:
        """Empty input should return empty list."""
        assert risk_parity_weights([]) == []

    @pytest.mark.risk
    def test_single_asset(self) -> None:
        """Single asset should get weight 1.0."""
        np.random.seed(42)
        returns = [list(np.random.normal(0.01, 0.02, 100))]
        weights = risk_parity_weights(returns)
        assert len(weights) == 1
        assert weights[0] == pytest.approx(1.0, abs=0.01)

    @pytest.mark.risk
    def test_empty_sublist_gets_default_vol(self) -> None:
        """Empty return sublist should be treated as unit volatility."""
        returns = [[], [0.01, 0.02, -0.01, 0.005]]
        weights = risk_parity_weights(returns)
        assert len(weights) == 2
        assert sum(weights) == pytest.approx(1.0, abs=0.01)

    @pytest.mark.risk
    def test_two_assets_known_vols(self) -> None:
        """Two assets with known vols: inverse-vol weighting."""
        # Asset 1: vol = 0.01, inv = 100
        # Asset 2: vol = 0.02, inv = 50
        # weights: [100/150, 50/150] = [0.667, 0.333]
        np.random.seed(42)
        ret1 = list(np.random.normal(0.01, 0.01, 1000))
        ret2 = list(np.random.normal(0.01, 0.02, 1000))
        weights = risk_parity_weights([ret1, ret2])
        # Lower vol → higher weight
        assert weights[0] > weights[1]
        assert weights[0] == pytest.approx(2.0 / 3.0, abs=0.05)
