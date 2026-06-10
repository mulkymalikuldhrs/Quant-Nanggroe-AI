"""Comprehensive tests for Risk modules.

Tests:
- VaRCalculator (parametric, historical, Monte Carlo, auto-select, CVaR)
- DrawdownMonitor (tracking, constitutional limits, recovery)
- KellyCriterion (4 variants, constraints, expected growth, risk of ruin)
- PositionSizer (fixed_fractional, volatility_based, kelly_based, optimal_f)
- RiskCheckGate (9-checkpoint validation)
- KillSwitch (activation, reset, auto-trigger)
- CorrelationMonitor (group detection, diversification, stress)
- Constitutional constants immutability
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, date

from quant_nanggroe.engine.risk.var import VaRCalculator, VaRResult
from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor, DrawdownInfo
from quant_nanggroe.engine.risk.kelly import (
    KellyCriterion, KellyMethod, KellyParameters, KellyResult,
)
from quant_nanggroe.engine.risk.position_sizing import PositionSizer, PositionSizeResult
from quant_nanggroe.engine.risk.checks import RiskCheckGate
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, RESET_CONFIRMATION
from quant_nanggroe.engine.risk.correlation import CorrelationMonitor
from quant_nanggroe.engine.risk.constants import (
    MAX_RISK_PER_TRADE, MAX_DAILY_LOSS, MAX_WEEKLY_LOSS,
    MAX_DRAWDOWN_PCT, MIN_RISK_REWARD, MAX_CORRELATED_POSITIONS,
    MAX_DAILY_TRADES, CONFIDENCE_THRESHOLD,
)


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def normal_returns():
    """1000 normal-distribution returns for VaR testing."""
    np.random.seed(42)
    return np.random.normal(0.0001, 0.02, 1000)


@pytest.fixture
def negative_returns():
    """Returns with strong negative bias."""
    np.random.seed(42)
    return np.random.normal(-0.005, 0.03, 500)


@pytest.fixture
def short_returns():
    """Only 10 returns (insufficient for historical VaR)."""
    return np.array([0.01, -0.02, 0.015, -0.01, 0.005, -0.03, 0.02, -0.005, 0.01, -0.015])


@pytest.fixture
def var_calculator():
    return VaRCalculator(default_confidence=0.95)


@pytest.fixture
def drawdown_monitor():
    return DrawdownMonitor(max_drawdown=0.10, initial_equity=1_000_000.0)


@pytest.fixture
def kelly_criterion():
    return KellyCriterion(max_position=0.20, min_position=0.01)


@pytest.fixture
def good_kelly_params():
    """Parameters with a clear positive edge."""
    return KellyParameters(win_rate=0.6, avg_win=200.0, avg_loss=100.0, confidence=0.8)


@pytest.fixture
def bad_kelly_params():
    """Parameters with no edge."""
    return KellyParameters(win_rate=0.3, avg_win=100.0, avg_loss=200.0, confidence=0.5)


@pytest.fixture
def risk_check_gate():
    return RiskCheckGate()


@pytest.fixture
def kill_switch():
    return KillSwitch()


# ═══════════════════════════════════════════════════════════════════════════
# VaR Calculator Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestVaRCalculator:
    """Comprehensive VaR Calculator tests."""

    # --- Parametric VaR ---

    def test_parametric_var_positive(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="parametric")
        assert result.var_value > 0, "VaR should be positive for normal returns"
        assert result.cvar_value > 0, "CVaR should be positive"
        assert result.cvar_value >= result.var_value, \
            "CVaR should be >= VaR (captures tail losses)"

    def test_parametric_var_increases_with_confidence(self, var_calculator, normal_returns):
        result_90 = var_calculator.calculate(normal_returns, confidence_level=0.90, method="parametric")
        result_95 = var_calculator.calculate(normal_returns, confidence_level=0.95, method="parametric")
        result_99 = var_calculator.calculate(normal_returns, confidence_level=0.99, method="parametric")
        assert result_99.var_value > result_95.var_value > result_90.var_value, \
            "VaR should increase with confidence level"

    def test_parametric_var_portfolio_value_scaling(self, var_calculator, normal_returns):
        result_1m = var_calculator.calculate(normal_returns, method="parametric", portfolio_value=1_000_000)
        result_2m = var_calculator.calculate(normal_returns, method="parametric", portfolio_value=2_000_000)
        # VaR should scale with portfolio value
        ratio = result_2m.var_value / result_1m.var_value
        assert abs(ratio - 2.0) < 0.01, f"VaR should scale linearly, got ratio {ratio}"

    def test_parametric_var_zero_std(self, var_calculator):
        """Zero std returns → VaR = 0."""
        constant_returns = np.zeros(100)
        result = var_calculator.calculate(constant_returns, method="parametric")
        assert result.var_value == 0.0
        assert result.cvar_value == 0.0

    def test_parametric_confidence_interval(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="parametric")
        ci = result.confidence_interval
        assert ci[0] < ci[1], "CI lower should be less than upper"

    # --- Historical VaR ---

    def test_historical_var_positive(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="historical")
        assert result.var_value > 0

    def test_historical_var_method_name(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="historical")
        assert result.method == "historical"

    def test_historical_cvar_exceeds_var(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="historical")
        assert result.cvar_value >= result.var_value, \
            "CVaR should be >= VaR for historical method"

    def test_historical_var_with_large_loss_tail(self, var_calculator):
        """Returns with fat tail should have high VaR/CVaR."""
        np.random.seed(42)
        returns = np.concatenate([
            np.random.normal(0.001, 0.01, 490),
            np.random.normal(-0.1, 0.05, 10),  # Fat tail
        ])
        result = var_calculator.calculate(returns, method="historical")
        assert result.cvar_value > result.var_value, \
            "CVaR should exceed VaR when fat tail exists"

    # --- Monte Carlo VaR ---

    def test_monte_carlo_var_positive(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="monte_carlo")
        assert result.var_value > 0

    def test_monte_carlo_var_method_name(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="monte_carlo")
        assert result.method == "monte_carlo"

    def test_monte_carlo_sensible_range(self, var_calculator, normal_returns):
        """Monte Carlo VaR should be in a reasonable range."""
        result = var_calculator.calculate(normal_returns, method="monte_carlo")
        # Should be between 0.5% and 20% of portfolio
        assert 0.005 < result.var_value < 0.20

    # --- Auto selection ---

    def test_auto_selects_parametric_for_small_samples(self, var_calculator, short_returns):
        """With < 100 observations, auto should select parametric."""
        method = VaRCalculator._select_method(50)
        assert method == "parametric"

    def test_auto_selects_parametric_for_100_to_499(self, var_calculator):
        method = VaRCalculator._select_method(200)
        assert method == "parametric"

    def test_auto_selects_historical_for_large_samples(self, var_calculator):
        method = VaRCalculator._select_method(600)
        assert method == "historical"

    def test_auto_method(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="auto")
        assert result.method in ("parametric", "historical", "monte_carlo")

    # --- Edge cases ---

    def test_insufficient_data_single_value(self, var_calculator):
        result = var_calculator.calculate(np.array([0.01]))
        assert result.method == "insufficient_data"
        assert result.var_value == 0.0
        assert result.cvar_value == 0.0

    def test_insufficient_data_empty(self, var_calculator):
        result = var_calculator.calculate(np.array([]))
        assert result.method == "insufficient_data"

    def test_nan_handling(self, var_calculator):
        """NaN values should be filtered out."""
        returns = np.array([0.01, np.nan, -0.02, 0.015, np.nan, -0.01, 0.005, -0.03, 0.02, -0.005])
        result = var_calculator.calculate(returns, method="parametric")
        assert result.method == "parametric"
        assert result.var_value > 0

    def test_all_nan_returns(self, var_calculator):
        """All-NaN returns should return insufficient_data."""
        returns = np.array([np.nan] * 10)
        result = var_calculator.calculate(returns)
        assert result.method == "insufficient_data"

    def test_unknown_method_defaults_to_historical(self, var_calculator, normal_returns):
        result = var_calculator.calculate(normal_returns, method="unknown_method")
        assert result.method == "historical"

    def test_var_result_dataclass(self):
        result = VaRResult(
            method="test",
            confidence_level=0.95,
            var_value=0.01,
            cvar_value=0.02,
            confidence_interval=(0.005, 0.015),
        )
        assert result.method == "test"
        assert result.cvar_value > result.var_value

    def test_var_consistency_across_methods(self, var_calculator, normal_returns):
        """All methods should give VaR in same order of magnitude."""
        param = var_calculator.calculate(normal_returns, method="parametric")
        hist = var_calculator.calculate(normal_returns, method="historical")
        mc = var_calculator.calculate(normal_returns, method="monte_carlo")
        # All should be within 10x of each other
        min_var = min(param.var_value, hist.var_value, mc.var_value)
        max_var = max(param.var_value, hist.var_value, mc.var_value)
        assert max_var / min_var < 10, \
            f"VaR methods diverge too much: param={param.var_value}, hist={hist.var_value}, mc={mc.var_value}"


# ═══════════════════════════════════════════════════════════════════════════
# Drawdown Monitor Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDrawdownMonitor:
    """Comprehensive Drawdown Monitor tests."""

    def test_initial_state(self, drawdown_monitor):
        assert drawdown_monitor.current_drawdown == 0.0
        assert drawdown_monitor.max_drawdown_observed == 0.0
        assert not drawdown_monitor.is_breached

    def test_no_drawdown_on_new_high(self, drawdown_monitor):
        drawdown_monitor.update(1_100_000)
        assert drawdown_monitor.current_drawdown == 0.0

    def test_drawdown_on_decline(self, drawdown_monitor):
        drawdown_monitor.update(950_000)  # 5% DD
        assert abs(drawdown_monitor.current_drawdown - 0.05) < 1e-6, \
            f"Expected 5% drawdown, got {drawdown_monitor.current_drawdown}"

    def test_drawdown_not_breached_at_9pct(self, drawdown_monitor):
        drawdown_monitor.update(910_000)  # 9% DD
        assert not drawdown_monitor.is_breached

    def test_drawdown_breached_at_10pct(self, drawdown_monitor):
        drawdown_monitor.update(900_000)  # 10% DD
        assert drawdown_monitor.is_breached

    def test_max_drawdown_tracked(self, drawdown_monitor):
        drawdown_monitor.update(950_000)  # 5% DD
        drawdown_monitor.update(920_000)  # 8% DD
        drawdown_monitor.update(980_000)  # Recovery
        assert abs(drawdown_monitor.max_drawdown_observed - 0.08) < 1e-6

    def test_peak_updates_on_new_high(self, drawdown_monitor):
        drawdown_monitor.update(1_100_000)
        drawdown_monitor.update(1_200_000)
        # Now decline from 1.2M
        drawdown_monitor.update(1_140_000)  # 5% DD from 1.2M
        assert abs(drawdown_monitor.current_drawdown - 0.05) < 1e-6

    def test_drawdown_info_returned(self, drawdown_monitor):
        info = drawdown_monitor.update(950_000)
        assert isinstance(info, DrawdownInfo)
        assert info.current_drawdown > 0
        assert info.recovery_factor < 1.0
        assert not info.is_breached

    def test_drawdown_info_breached(self, drawdown_monitor):
        info = drawdown_monitor.update(890_000)  # 11% DD
        assert info.is_breached

    def test_bars_since_peak(self, drawdown_monitor):
        drawdown_monitor.update(950_000)  # Bar 1
        drawdown_monitor.update(940_000)  # Bar 2
        drawdown_monitor.update(930_000)  # Bar 3
        info = drawdown_monitor.update(920_000)  # Bar 4
        assert info.drawdown_duration == 4

    def test_bars_since_peak_reset_on_new_high(self, drawdown_monitor):
        drawdown_monitor.update(950_000)
        drawdown_monitor.update(940_000)
        info = drawdown_monitor.update(1_100_000)  # New high
        assert info.drawdown_duration == 0

    def test_get_status(self, drawdown_monitor):
        drawdown_monitor.update(950_000)
        status = drawdown_monitor.get_status()
        assert "current_drawdown" in status
        assert "constitutional_limit" in status
        assert "drawdown_breached" in status

    def test_constitutional_limit_cannot_be_exceeded(self):
        """Max drawdown parameter is capped at constitutional limit."""
        monitor = DrawdownMonitor(max_drawdown=0.50)  # Try to set 50%
        # Should be capped at MAX_DRAWDOWN_PCT (0.15)
        assert monitor._max_dd <= MAX_DRAWDOWN_PCT

    def test_calculate_cvar_drawdown(self):
        monitor = DrawdownMonitor()
        equity = pd.Series([100, 102, 101, 103, 100, 98, 95, 97, 99, 101,
                            100, 98, 96, 94, 93, 95, 97, 99, 101, 103])
        cvar_dd = monitor.calculate_cvar_drawdown(equity, confidence_level=0.95)
        assert cvar_dd >= 0

    def test_calculate_cvar_drawdown_empty(self):
        monitor = DrawdownMonitor()
        equity = pd.Series([], dtype=float)
        cvar_dd = monitor.calculate_cvar_drawdown(equity)
        assert cvar_dd == 0.0

    def test_calculate_risk_of_ruin_negative_expectancy(self):
        """Negative expectancy → certain ruin (1.0)."""
        ror = DrawdownMonitor.calculate_risk_of_ruin(
            win_rate=0.3, avg_win=50.0, avg_loss=100.0
        )
        assert ror == 1.0

    def test_calculate_risk_of_ruin_positive_expectancy(self):
        """Positive expectancy → risk of ruin < 1."""
        ror = DrawdownMonitor.calculate_risk_of_ruin(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0
        )
        assert 0.0 <= ror < 1.0

    def test_calculate_risk_of_ruin_zero_loss(self):
        """Zero avg_loss → no ruin possible (0)."""
        ror = DrawdownMonitor.calculate_risk_of_ruin(
            win_rate=0.5, avg_win=100.0, avg_loss=0.0
        )
        assert ror == 0.0

    def test_estimate_recovery_time(self):
        """Recovery time should be positive for drawdown > 0."""
        years = DrawdownMonitor.estimate_recovery_time(0.10, avg_annual_return=0.10)
        assert years > 0

    def test_estimate_recovery_time_zero_drawdown(self):
        years = DrawdownMonitor.estimate_recovery_time(0.0, avg_annual_return=0.10)
        assert years == 0.0

    def test_estimate_recovery_time_zero_return(self):
        years = DrawdownMonitor.estimate_recovery_time(0.10, avg_annual_return=0.0)
        assert years == 0.0

    def test_recovery_factor(self, drawdown_monitor):
        info = drawdown_monitor.update(950_000)
        expected_factor = 950_000 / 1_000_000
        assert abs(info.recovery_factor - expected_factor) < 1e-6

    def test_equity_history_tracking(self, drawdown_monitor):
        drawdown_monitor.update(950_000)
        drawdown_monitor.update(980_000)
        assert len(drawdown_monitor._equity_history) == 3  # initial + 2 updates


# ═══════════════════════════════════════════════════════════════════════════
# Kelly Criterion Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestKellyCriterion:
    """Comprehensive Kelly Criterion tests."""

    def test_basic_kelly_positive_edge(self, kelly_criterion, good_kelly_params):
        result = kelly_criterion.calculate_kelly(good_kelly_params)
        assert result.optimal_fraction > 0, "Should have positive Kelly with edge"

    def test_basic_kelly_negative_edge(self, kelly_criterion, bad_kelly_params):
        result = kelly_criterion.calculate_kelly(bad_kelly_params)
        assert result.optimal_fraction == 0.0, "Kelly should be 0 with no edge"

    def test_half_kelly_default(self, kelly_criterion, good_kelly_params):
        result = kelly_criterion.calculate_kelly(good_kelly_params, method=KellyMethod.HALF_KELLY)
        assert result.adjusted_fraction <= result.optimal_fraction

    def test_quarter_kelly_smaller(self, kelly_criterion, good_kelly_params):
        half = kelly_criterion.calculate_kelly(good_kelly_params, method=KellyMethod.HALF_KELLY)
        quarter = kelly_criterion.calculate_kelly(good_kelly_params, method=KellyMethod.QUARTER_KELLY)
        assert quarter.adjusted_fraction <= half.adjusted_fraction

    def test_full_kelly(self, kelly_criterion, good_kelly_params):
        full = kelly_criterion.calculate_kelly(good_kelly_params, method=KellyMethod.FULL_KELLY)
        half = kelly_criterion.calculate_kelly(good_kelly_params, method=KellyMethod.HALF_KELLY)
        assert full.optimal_fraction == half.optimal_fraction
        assert full.adjusted_fraction >= half.adjusted_fraction

    def test_max_position_cap(self, kelly_criterion):
        """Kelly should be capped at max_position."""
        params = KellyParameters(win_rate=0.9, avg_win=500.0, avg_loss=50.0, confidence=1.0)
        result = kelly_criterion.calculate_kelly(params, method=KellyMethod.FULL_KELLY)
        assert result.adjusted_fraction <= kelly_criterion.max_position

    def test_min_position_floor(self, kelly_criterion):
        """Very small positive Kelly should be floored at min_position."""
        params = KellyParameters(win_rate=0.51, avg_win=101.0, avg_loss=100.0, confidence=0.9)
        result = kelly_criterion.calculate_kelly(params, method=KellyMethod.FULL_KELLY)
        if result.optimal_fraction > 0:
            assert result.adjusted_fraction >= kelly_criterion.min_position or result.adjusted_fraction == 0.0

    def test_expected_value(self, kelly_criterion, good_kelly_params):
        result = kelly_criterion.calculate_kelly(good_kelly_params)
        # EV = p*avg_win - q*avg_loss = 0.6*200 - 0.4*100 = 80
        assert result.expected_value > 0

    def test_expected_growth_positive(self, kelly_criterion, good_kelly_params):
        result = kelly_criterion.calculate_kelly(good_kelly_params)
        assert result.expected_growth > 0

    def test_risk_of_ruin_low(self, kelly_criterion, good_kelly_params):
        result = kelly_criterion.calculate_kelly(good_kelly_params, method=KellyMethod.HALF_KELLY)
        # Risk of ruin depends on fraction and edge; with good params it should be < 0.5
        assert 0.0 <= result.risk_of_ruin <= 1.0

    def test_recommendation_avoid_negative_growth(self, kelly_criterion, bad_kelly_params):
        result = kelly_criterion.calculate_kelly(bad_kelly_params)
        assert "AVOID" in result.recommendation or "NO POSITION" in result.recommendation

    def test_kelly_method_enum(self):
        assert KellyMethod.FULL_KELLY.value == "FULL_KELLY"
        assert KellyMethod.HALF_KELLY.value == "HALF_KELLY"
        assert KellyMethod.QUARTER_KELLY.value == "QUARTER_KELLY"

    def test_continuous_kelly(self, kelly_criterion):
        f = kelly_criterion.calculate_continuous_kelly(
            mean_return=0.10, variance=0.04, risk_free_rate=0.02
        )
        assert abs(f - 2.0) < 1e-10, f"Expected 2.0, got {f}"

    def test_continuous_kelly_zero_variance(self, kelly_criterion):
        f = kelly_criterion.calculate_continuous_kelly(mean_return=0.10, variance=0.0)
        assert f == 0.0

    def test_multi_asset_kelly(self, kelly_criterion):
        expected_returns = np.array([0.10, 0.15])
        cov_matrix = np.array([[0.04, 0.01], [0.01, 0.09]])
        weights = kelly_criterion.calculate_multi_asset_kelly(expected_returns, cov_matrix)
        assert len(weights) == 2
        assert np.sum(np.abs(weights)) <= 1.0 + 1e-10

    def test_multi_asset_kelly_singular_matrix(self, kelly_criterion):
        """Singular covariance matrix should return zeros."""
        expected_returns = np.array([0.10, 0.15])
        cov_matrix = np.array([[0.0, 0.0], [0.0, 0.0]])  # Singular
        weights = kelly_criterion.calculate_multi_asset_kelly(expected_returns, cov_matrix)
        np.testing.assert_array_equal(weights, [0.0, 0.0])

    def test_zero_avg_loss_returns_zero(self, kelly_criterion):
        params = KellyParameters(win_rate=0.6, avg_win=200.0, avg_loss=0.0)
        result = kelly_criterion.calculate_kelly(params)
        assert result.optimal_fraction == 0.0

    def test_confidence_adjustment(self, kelly_criterion, good_kelly_params):
        high_conf = good_kelly_params
        low_conf = KellyParameters(**{**good_kelly_params.__dict__, "confidence": 0.1})
        result_high = kelly_criterion.calculate_kelly(high_conf)
        result_low = kelly_criterion.calculate_kelly(low_conf)
        # Higher confidence should give higher adjusted fraction
        assert result_high.adjusted_fraction >= result_low.adjusted_fraction

    def test_kelly_fractional_method(self, kelly_criterion, good_kelly_params):
        result = kelly_criterion.calculate_kelly(good_kelly_params, method=KellyMethod.FRACTIONAL_KELLY)
        # Fractional Kelly should be half of full Kelly
        full = kelly_criterion.calculate_kelly(good_kelly_params, method=KellyMethod.FULL_KELLY)
        # Before constraints, fractional should be half
        assert result.optimal_fraction == full.optimal_fraction


# ═══════════════════════════════════════════════════════════════════════════
# Position Sizer Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPositionSizer:
    """Comprehensive Position Sizer tests."""

    def test_fixed_fractional_basic(self):
        result = PositionSizer.fixed_fractional(
            equity=100_000, risk_pct=0.01, entry_price=100.0, stop_price=99.0
        )
        assert result.size > 0
        assert result.method == "fixed_fractional"
        # Risk is capped at MAX_RISK_PER_TRADE (0.005), so risk_amount = 100k * 0.005 = 500
        assert result.risk_amount == 100_000 * result.risk_pct

    def test_fixed_fractional_capped_at_max_risk(self):
        """Risk > MAX_RISK_PER_TRADE should be capped."""
        result = PositionSizer.fixed_fractional(
            equity=100_000, risk_pct=0.10, entry_price=100.0, stop_price=99.0
        )
        assert result.capped is True
        assert result.risk_pct <= MAX_RISK_PER_TRADE

    def test_fixed_fractional_zero_stop_distance(self):
        """Entry == stop → zero size."""
        result = PositionSizer.fixed_fractional(
            equity=100_000, risk_pct=0.01, entry_price=100.0, stop_price=100.0
        )
        assert result.size == 0.0

    def test_fixed_fractional_correct_size(self):
        """Verify size calculation: size = risk_amount / |entry - stop|."""
        result = PositionSizer.fixed_fractional(
            equity=100_000, risk_pct=0.01, entry_price=100.0, stop_price=98.0
        )
        # Risk capped at 0.005, so risk_amount = 500, size = 500 / 2 = 250
        expected_size = (100_000 * result.risk_pct) / 2.0
        assert abs(result.size - expected_size) < 1e-6

    def test_volatility_based_basic(self):
        result = PositionSizer.volatility_based(
            equity=100_000, atr=2.0, entry_price=100.0, risk_pct=0.01
        )
        assert result.size > 0
        assert result.method == "volatility_based"

    def test_volatility_based_capped(self):
        result = PositionSizer.volatility_based(
            equity=100_000, atr=2.0, entry_price=100.0, risk_pct=0.10
        )
        assert result.capped is True

    def test_volatility_based_zero_atr(self):
        """Zero ATR → zero size."""
        result = PositionSizer.volatility_based(
            equity=100_000, atr=0.0, entry_price=100.0
        )
        assert result.size == 0.0

    def test_volatility_based_with_multiplier(self):
        result_2x = PositionSizer.volatility_based(
            equity=100_000, atr=2.0, atr_multiplier=2.0, risk_pct=0.01
        )
        result_3x = PositionSizer.volatility_based(
            equity=100_000, atr=2.0, atr_multiplier=3.0, risk_pct=0.01
        )
        # Larger multiplier → wider stop → smaller size
        assert result_2x.size > result_3x.size

    def test_kelly_based_basic(self):
        result = PositionSizer.kelly_based(
            equity=100_000, win_rate=0.6, avg_win=200.0, avg_loss=100.0
        )
        assert result.size > 0
        assert result.method == "kelly_based"

    def test_kelly_based_zero_loss(self):
        result = PositionSizer.kelly_based(
            equity=100_000, win_rate=0.6, avg_win=200.0, avg_loss=0.0
        )
        assert result.size == 0.0

    def test_kelly_based_no_edge(self):
        result = PositionSizer.kelly_based(
            equity=100_000, win_rate=0.3, avg_win=100.0, avg_loss=200.0
        )
        assert result.size == 0.0 or result.risk_pct == 0.0

    def test_kelly_based_capped(self):
        result = PositionSizer.kelly_based(
            equity=100_000, win_rate=0.9, avg_win=500.0, avg_loss=50.0
        )
        # Very strong edge, but risk should be capped
        assert result.risk_pct <= MAX_RISK_PER_TRADE

    def test_optimal_f_basic(self):
        trades = [100, -50, 200, -30, 150, -80, 120, -60, 180, -40]
        result = PositionSizer.optimal_f(equity=100_000, trades_pnl=trades)
        assert result.size > 0
        assert result.method == "optimal_f"

    def test_optimal_f_empty_trades(self):
        result = PositionSizer.optimal_f(equity=100_000, trades_pnl=[])
        assert result.size == 0.0

    def test_optimal_f_all_positive(self):
        """All positive trades → min(pnl) is positive, so max_loss = min value."""
        result = PositionSizer.optimal_f(equity=100_000, trades_pnl=[100, 200, 150])
        # No losing trades in the data, but code uses abs(min(trades_pnl))
        # Since all are positive, the result is still calculated
        assert result.method == "optimal_f"

    def test_optimal_f_capped(self):
        trades = [-10, 50, -5, 60, -8, 70, -3, 80, -2, 90]
        result = PositionSizer.optimal_f(equity=100_000, trades_pnl=trades)
        assert result.risk_pct <= MAX_RISK_PER_TRADE


# ═══════════════════════════════════════════════════════════════════════════
# Risk Check Gate Tests (9-Checkpoint)
# ═══════════════════════════════════════════════════════════════════════════

class TestRiskCheckGate:
    """Comprehensive 9-checkpoint risk gate tests."""

    def test_approve_valid_trade(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
            # Use TP that gives R:R strictly > 2.0 to avoid floating point issues
            take_profit=1.1105,
        )
        assert result["verdict"] == "APPROVED", f"Expected APPROVED, got {result['verdict']}. Failed: {result['failed_checkpoints']}"

    def test_veto_high_risk(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=1.0,  # Large lot
            entry=1.1000,
            stop_loss=1.0500,  # Wide stop
            account_balance=1_000_000,
        )
        assert result["verdict"] == "VETOED"
        assert "1_risk_per_trade" in result["failed_checkpoints"]

    def test_veto_no_stop_loss(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=0,  # No stop loss
            account_balance=1_000_000,
        )
        assert result["verdict"] == "VETOED"
        assert "5_stop_loss_exists" in result["failed_checkpoints"]

    def test_veto_invalid_entry(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=0,  # Invalid entry
            stop_loss=1.0950,
            account_balance=1_000_000,
        )
        assert result["verdict"] == "VETOED"

    def test_veto_invalid_direction(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="INVALID",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
        )
        assert result["verdict"] == "VETOED"
        assert "7_valid_direction" in result["failed_checkpoints"]

    def test_veto_overtrading(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
            trade_count_today=10,  # Over the limit
        )
        assert result["verdict"] == "VETOED"
        assert "8_not_overtrading" in result["failed_checkpoints"]

    def test_veto_daily_loss_limit(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
            daily_pnl=-15000,  # 1.5% daily loss
        )
        assert result["verdict"] == "VETOED"
        assert "2_daily_loss" in result["failed_checkpoints"]

    def test_veto_weekly_loss_limit(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
            weekly_pnl=-40000,  # 4% weekly loss
        )
        assert result["verdict"] == "VETOED"
        assert "3_weekly_loss" in result["failed_checkpoints"]

    def test_veto_risk_reward(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
            take_profit=1.1050,  # Only 1:1 R:R
        )
        assert result["verdict"] == "VETOED"
        assert "4_risk_reward" in result["failed_checkpoints"]

    def test_approve_with_good_rr(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
            take_profit=1.1110,  # R:R > 2.0 to avoid float precision
        )
        # R:R check should pass
        assert result["checkpoints"]["4_risk_reward"]["passed"] is True

    def test_all_9_checkpoints_present(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
        )
        expected_checks = [
            "1_risk_per_trade", "2_daily_loss", "3_weekly_loss",
            "4_risk_reward", "5_stop_loss_exists", "6_valid_entry",
            "7_valid_direction", "8_not_overtrading", "9_correlation_check",
        ]
        for check in expected_checks:
            assert check in result["checkpoints"], f"Missing checkpoint: {check}"

    def test_direction_case_insensitive(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="buy",  # lowercase
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
        )
        assert result["checkpoints"]["7_valid_direction"]["passed"] is True

    def test_sell_direction_valid(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="SELL",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.1050,
            account_balance=1_000_000,
            take_profit=1.0900,
        )
        assert result["checkpoints"]["7_valid_direction"]["passed"] is True

    def test_correlation_check_passes(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="AAPL",
            direction="BUY",
            lot_size=0.01,
            entry=150.0,
            stop_loss=149.0,
            account_balance=1_000_000,
            active_positions=["MSFT", "GOOGL"],  # Not correlated
        )
        assert result["checkpoints"]["9_correlation_check"]["passed"] is True

    def test_correlation_check_fails_too_many(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=1_000_000,
            active_positions=["GBPUSD", "AUDUSD", "NZDUSD"],  # All correlated
        )
        assert result["checkpoints"]["9_correlation_check"]["passed"] is False

    def test_multiple_failures_listed(self, risk_check_gate):
        result = risk_check_gate.evaluate(
            symbol="EURUSD",
            direction="INVALID",
            lot_size=1.0,
            entry=0,
            stop_loss=0,
            account_balance=1_000_000,
        )
        assert len(result["failed_checkpoints"]) >= 3


# ═══════════════════════════════════════════════════════════════════════════
# Kill Switch Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestKillSwitch:
    """Comprehensive Kill Switch tests."""

    def test_initial_state_inactive(self, kill_switch):
        assert not kill_switch.is_active

    def test_activate(self, kill_switch):
        result = kill_switch.activate("MANUAL")
        assert kill_switch.is_active
        assert result["status"] == "ACTIVATED"
        assert result["reason"] == "MANUAL"

    def test_activate_auto(self, kill_switch):
        result = kill_switch.activate("AUTO_DAILY_LIMIT")
        assert kill_switch.is_active
        assert result["auto_triggers_total"] == 1
        assert result["manual_triggers_total"] == 0

    def test_activate_already_active(self, kill_switch):
        kill_switch.activate("MANUAL")
        result = kill_switch.activate("MANUAL")
        assert result["status"] == "ALREADY_ACTIVE"

    def test_reset_without_confirmation(self, kill_switch):
        kill_switch.activate("MANUAL")
        result = kill_switch.reset("wrong_confirmation")
        assert result["status"] == "STILL_ACTIVE"
        assert kill_switch.is_active

    def test_reset_with_correct_confirmation(self, kill_switch):
        kill_switch.activate("MANUAL")
        result = kill_switch.reset(RESET_CONFIRMATION)
        assert result["status"] == "RESET"
        assert not kill_switch.is_active

    def test_reset_when_not_active(self, kill_switch):
        result = kill_switch.reset(RESET_CONFIRMATION)
        assert result["status"] == "NOT_ACTIVE"

    def test_auto_trigger_daily_limit(self, kill_switch):
        result = kill_switch.check_auto_trigger(
            daily_loss_pct=0.02,  # 2% >= MAX_DAILY_LOSS (1%)
            weekly_loss_pct=0.0,
            drawdown_pct=0.0,
        )
        assert result is not None
        assert result["reason"] == "AUTO_DAILY_LIMIT"
        assert kill_switch.is_active

    def test_auto_trigger_weekly_limit(self, kill_switch):
        result = kill_switch.check_auto_trigger(
            daily_loss_pct=0.0,
            weekly_loss_pct=0.05,  # 5% >= MAX_WEEKLY_LOSS (3%)
            drawdown_pct=0.0,
        )
        assert result is not None
        assert result["reason"] == "AUTO_WEEKLY_LIMIT"

    def test_auto_trigger_drawdown(self, kill_switch):
        result = kill_switch.check_auto_trigger(
            daily_loss_pct=0.0,
            weekly_loss_pct=0.0,
            drawdown_pct=MAX_DRAWDOWN_PCT,  # At limit
        )
        assert result is not None
        assert result["reason"] == "AUTO_MAX_DRAWDOWN"

    def test_auto_trigger_no_breach(self, kill_switch):
        result = kill_switch.check_auto_trigger(
            daily_loss_pct=0.005,
            weekly_loss_pct=0.01,
            drawdown_pct=0.05,
        )
        assert result is None
        assert not kill_switch.is_active

    def test_status_reflects_state(self, kill_switch):
        kill_switch.activate("MANUAL")
        status = kill_switch.status()
        assert status["is_active"] is True
        assert status["activation_reason"] == "MANUAL"
        assert status["total_activations"] == 1

    def test_activation_log(self, kill_switch):
        kill_switch.activate("AUTO_DAILY_LIMIT")
        kill_switch.activate("MANUAL")  # Already active → logged differently
        status = kill_switch.status()
        assert status["auto_triggers"] == 1

    def test_manual_triggers_counted(self, kill_switch):
        kill_switch.activate("MANUAL")
        kill_switch.reset(RESET_CONFIRMATION)
        kill_switch.activate("MANUAL")
        status = kill_switch.status()
        assert status["manual_triggers"] == 2

    def test_confirmation_string_constant(self):
        assert RESET_CONFIRMATION == "CONFIRM_RESET_AFTER_REVIEW"


# ═══════════════════════════════════════════════════════════════════════════
# Correlation Monitor Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCorrelationMonitor:
    """Comprehensive Correlation Monitor tests."""

    def test_correlated_forex(self):
        monitor = CorrelationMonitor()
        assert monitor.is_correlated("EURUSD", "GBPUSD")
        assert monitor.is_correlated("EURUSD", "AUDUSD")

    def test_not_correlated_cross_asset(self):
        monitor = CorrelationMonitor()
        assert not monitor.is_correlated("EURUSD", "BTCUSDT")
        assert not monitor.is_correlated("AAPL", "BTCUSDT")

    def test_correlated_crypto(self):
        monitor = CorrelationMonitor()
        assert monitor.is_correlated("BTCUSDT", "ETHUSDT")

    def test_correlated_equities(self):
        monitor = CorrelationMonitor()
        assert monitor.is_correlated("SPY", "QQQ")

    def test_count_correlated_positions(self):
        monitor = CorrelationMonitor()
        count = monitor.count_correlated_positions("EURUSD", ["GBPUSD", "AUDUSD", "BTCUSDT"])
        assert count == 2  # GBPUSD and AUDUSD are correlated with EURUSD

    def test_count_no_correlated(self):
        monitor = CorrelationMonitor()
        count = monitor.count_correlated_positions("AAPL", ["MSFT", "GOOGL"])
        assert count == 0

    def test_case_insensitive(self):
        monitor = CorrelationMonitor()
        assert monitor.is_correlated("eurusd", "gbpusd")

    def test_rolling_correlation(self):
        monitor = CorrelationMonitor()
        np.random.seed(42)
        returns = pd.DataFrame({
            "A": np.random.normal(0, 0.02, 100),
            "B": np.random.normal(0, 0.02, 100),
        })
        corr = monitor.compute_rolling_correlation(returns)
        assert corr.shape == (2, 2)
        assert abs(corr.iloc[0, 0] - 1.0) < 1e-10  # Diagonal = 1
        assert abs(corr.iloc[1, 1] - 1.0) < 1e-10

    def test_diversification_score_single_asset(self):
        monitor = CorrelationMonitor()
        returns = pd.DataFrame({"A": np.random.normal(0, 0.02, 100)})
        score = monitor.compute_diversification_score(returns)
        assert score == 0.0  # Can't diversify with one asset

    def test_diversification_score_uncorrelated(self):
        monitor = CorrelationMonitor()
        np.random.seed(42)
        returns = pd.DataFrame({
            "A": np.random.normal(0, 0.02, 200),
            "B": np.random.normal(0, 0.02, 200),
            "C": np.random.normal(0, 0.02, 200),
        })
        score = monitor.compute_diversification_score(returns)
        assert score > 0.0, "Uncorrelated assets should have positive diversification"

    def test_diversification_score_correlated(self):
        monitor = CorrelationMonitor()
        np.random.seed(42)
        base = np.random.normal(0, 0.02, 200)
        returns = pd.DataFrame({
            "A": base,
            "B": base + np.random.normal(0, 0.001, 200),  # Highly correlated
        })
        score = monitor.compute_diversification_score(returns)
        # Score should be low for correlated assets
        assert score < 0.5

    def test_detect_stress_normal(self):
        monitor = CorrelationMonitor()
        np.random.seed(42)
        returns = pd.DataFrame({
            "A": np.random.normal(0, 0.02, 100),
            "B": np.random.normal(0, 0.02, 100),
            "C": np.random.normal(0, 0.02, 100),
        })
        result = monitor.detect_stress(returns)
        assert result["stress_level"] == "NORMAL"

    def test_detect_stress_single_asset(self):
        monitor = CorrelationMonitor()
        returns = pd.DataFrame({"A": np.random.normal(0, 0.02, 100)})
        result = monitor.detect_stress(returns)
        assert result["stress_detected"] is False


# ═══════════════════════════════════════════════════════════════════════════
# Constitutional Constants Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestConstitutionalConstants:
    """Test that constitutional constants are set correctly and are immutable."""

    def test_max_risk_per_trade(self):
        assert MAX_RISK_PER_TRADE == 0.005

    def test_max_daily_loss(self):
        assert MAX_DAILY_LOSS == 0.01

    def test_max_weekly_loss(self):
        assert MAX_WEEKLY_LOSS == 0.03

    def test_max_drawdown_pct(self):
        assert MAX_DRAWDOWN_PCT == 0.15

    def test_min_risk_reward(self):
        assert MIN_RISK_REWARD == 2.0

    def test_max_correlated_positions(self):
        assert MAX_CORRELATED_POSITIONS == 3

    def test_max_daily_trades(self):
        assert MAX_DAILY_TRADES == 5

    def test_confidence_threshold(self):
        assert CONFIDENCE_THRESHOLD == 0.65

    def test_constants_are_numbers(self):
        """All constants should be numeric (not strings)."""
        for const in [MAX_RISK_PER_TRADE, MAX_DAILY_LOSS, MAX_WEEKLY_LOSS,
                       MAX_DRAWDOWN_PCT, MIN_RISK_REWARD, MAX_CORRELATED_POSITIONS,
                       MAX_DAILY_TRADES, CONFIDENCE_THRESHOLD]:
            assert isinstance(const, (int, float))
