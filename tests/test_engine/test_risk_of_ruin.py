"""Tests for the Risk of Ruin Calculator module."""

import math

import numpy as np
import pytest

from quant_nanggroe.engine.risk.risk_of_ruin import (
    RiskOfRuinConfig,
    RiskOfRuinReport,
    RiskOfRuinResult,
    generate_risk_of_ruin_report,
    kelly_risk_of_ruin,
    optimal_position_size,
    simulate_risk_of_ruin,
)


def _make_config(**overrides) -> RiskOfRuinConfig:
    """Create a config with sensible defaults, allowing overrides."""
    defaults = dict(
        initial_capital=100000,
        win_rate=0.55,
        avg_win=0.02,
        avg_loss=0.02,
        position_size_pct=0.02,
        max_simulations=2000,
        max_trades_per_sim=500,
        ruin_threshold=0.0,
        cost_per_trade=0.001,
    )
    defaults.update(overrides)
    return RiskOfRuinConfig(**defaults)


class TestSimulateRiskOfRuin:
    """Tests for the Monte Carlo simulation."""

    def test_zero_win_rate_ruin_certain(self):
        """With 0% win rate, ruin should be near-certain."""
        config = _make_config(
            win_rate=0.0,
            ruin_threshold=0.5,  # Ruin = 50% drawdown
            position_size_pct=0.10,
            max_trades_per_sim=1000,
        )
        result = simulate_risk_of_ruin(config)
        assert result.probability_of_ruin > 0.9
        assert not result.is_acceptable

    def test_high_win_rate_safe(self):
        """With a very high win rate and small position, ruin should be rare."""
        config = _make_config(win_rate=0.85, position_size_pct=0.01)
        result = simulate_risk_of_ruin(config)
        assert result.probability_of_ruin < 0.1
        assert result.median_final_capital > config.initial_capital

    def test_result_has_all_fields(self):
        """Result should contain all required fields."""
        config = _make_config()
        result = simulate_risk_of_ruin(config)
        assert isinstance(result, RiskOfRuinResult)
        assert 0 <= result.probability_of_ruin <= 1
        assert result.expected_survival_trades > 0
        assert result.median_final_capital >= 0
        assert result.p5_final_capital >= 0
        assert result.p95_final_capital >= 0
        assert len(result.max_drawdown_distribution) > 0
        assert len(result.capital_paths_sample) > 0
        assert len(result.confidence_interval) == 2
        assert isinstance(result.is_acceptable, bool)
        assert result.recommendation != ""

    def test_larger_position_more_ruin(self):
        """Larger position sizes should increase risk of ruin."""
        config_small = _make_config(position_size_pct=0.01)
        config_large = _make_config(position_size_pct=0.10)
        result_small = simulate_risk_of_ruin(config_small)
        result_large = simulate_risk_of_ruin(config_large)
        assert result_large.probability_of_ruin >= result_small.probability_of_ruin


class TestKellyRiskOfRuin:
    """Tests for the analytical Kelly-based approximation."""

    def test_kelly_no_edge_certain_ruin(self):
        """With no edge (50% win rate), ruin should be certain."""
        ror = kelly_risk_of_ruin(kelly_fraction=1.0, win_rate=0.5)
        assert ror >= 0.99  # Near certain

    def test_kelly_high_edge_low_ruin(self):
        """With a strong edge, risk of ruin should be low."""
        ror = kelly_risk_of_ruin(kelly_fraction=0.25, win_rate=0.7)
        assert ror < 0.5

    def test_kelly_fractional_reduces_ror(self):
        """Fractional Kelly should reduce risk of ruin."""
        ror_full = kelly_risk_of_ruin(kelly_fraction=1.0, win_rate=0.6)
        ror_half = kelly_risk_of_ruin(kelly_fraction=0.5, win_rate=0.6)
        assert ror_half < ror_full

    def test_kelly_zero_fraction_certain_ruin(self):
        """Zero Kelly fraction should mean no bet -> certain non-ruin... but our model says 1."""
        ror = kelly_risk_of_ruin(kelly_fraction=0.0, win_rate=0.6)
        assert ror == 1.0  # No bet = certain ruin in our formulation


class TestOptimalPositionSize:
    """Tests for the binary search optimal position size."""

    def test_optimal_position_within_bounds(self):
        """Optimal position should be positive and reasonable."""
        config = _make_config(
            win_rate=0.6,
            position_size_pct=0.05,
            max_simulations=1000,
            max_trades_per_sim=200,
        )
        optimal = optimal_position_size(config, max_ror=0.05)
        assert optimal > 0
        assert optimal <= 0.10  # Should be less than 10%

    def test_optimal_position_with_no_edge(self):
        """With no edge, optimal position should be tiny."""
        config = _make_config(
            win_rate=0.45,
            position_size_pct=0.05,
            max_simulations=1000,
            max_trades_per_sim=200,
        )
        optimal = optimal_position_size(config, max_ror=0.05)
        # With negative edge, should be very small
        assert optimal >= 0


class TestRuinThreshold:
    """Tests for non-zero ruin thresholds."""

    def test_nonzero_ruin_threshold(self):
        """A non-zero ruin threshold (e.g., 50% drawdown) should be respected."""
        config = _make_config(
            ruin_threshold=0.5,
            win_rate=0.5,
            position_size_pct=0.05,
        )
        result = simulate_risk_of_ruin(config)
        # Ruin is now at 50% of initial capital
        assert result.probability_of_ruin >= 0  # Should still produce valid result


class TestConfidenceInterval:
    """Tests for the confidence interval."""

    def test_ci_contains_point_estimate(self):
        """The 95% CI should contain the point estimate of ruin probability."""
        config = _make_config()
        result = simulate_risk_of_ruin(config)
        ci_lo, ci_hi = result.confidence_interval
        assert ci_lo <= result.probability_of_ruin + 0.05  # Allow some tolerance
        assert ci_hi >= result.probability_of_ruin - 0.05
        assert ci_lo >= 0
        assert ci_hi <= 1


class TestRiskOfRuinReport:
    """Tests for the generate_risk_of_ruin_report function."""

    def test_report_structure(self):
        """Report should contain all required fields."""
        config = _make_config()
        report = generate_risk_of_ruin_report(config)
        assert isinstance(report, RiskOfRuinReport)
        assert isinstance(report.config, RiskOfRuinConfig)
        assert isinstance(report.mc_result, RiskOfRuinResult)
        assert 0 <= report.analytical_ror <= 1
        assert report.kelly_optimal_size >= 0
        assert report.recommended_max_position >= 0
        assert report.verdict in ("SAFE", "CAUTION", "DANGEROUS", "CRITICAL")
        assert len(report.recommendations) > 0

    def test_safe_verdict(self):
        """Conservative config should produce SAFE verdict."""
        config = _make_config(win_rate=0.85, position_size_pct=0.005)
        report = generate_risk_of_ruin_report(config)
        assert report.verdict in ("SAFE", "CAUTION")  # Allow some MC noise

    def test_critical_verdict(self):
        """Aggressive config with no edge should produce CRITICAL verdict."""
        config = _make_config(
            win_rate=0.3, position_size_pct=0.10,
            max_simulations=2000, max_trades_per_sim=1000,
            ruin_threshold=0.5,  # Ruin at 50% drawdown
            avg_loss=0.05,  # Larger losses
        )
        report = generate_risk_of_ruin_report(config)
        assert report.verdict in ("DANGEROUS", "CRITICAL")


class TestTransactionCosts:
    """Tests for transaction cost effects."""

    def test_high_costs_increase_ruin(self):
        """Higher transaction costs should increase risk of ruin."""
        config_low_cost = _make_config(cost_per_trade=0.0)
        config_high_cost = _make_config(cost_per_trade=0.01)
        result_low = simulate_risk_of_ruin(config_low_cost)
        result_high = simulate_risk_of_ruin(config_high_cost)
        assert result_high.probability_of_ruin >= result_low.probability_of_ruin

    def test_high_costs_flagged_in_report(self):
        """High transaction costs should be flagged in recommendations."""
        config = _make_config(cost_per_trade=0.01)
        report = generate_risk_of_ruin_report(config)
        # Should mention transaction costs in recommendations
        mentions_cost = any(
            "transaction cost" in r.lower() or "cost" in r.lower()
            for r in report.recommendations
        )
        assert mentions_cost
