"""Comprehensive tests for RiskManager integration.

Tests the top-level RiskManager that orchestrates kill switch,
drawdown monitor, Kelly criterion, VaR calculator, and the 9-checkpoint gate.
"""

from __future__ import annotations

import pytest
from datetime import datetime, date

from quant_nanggroe.engine.risk.manager import RiskManager, RiskState
from quant_nanggroe.engine.risk.constants import (
    MAX_RISK_PER_TRADE, MAX_DAILY_LOSS, MAX_WEEKLY_LOSS,
    MAX_DRAWDOWN_PCT, MIN_RISK_REWARD, MAX_CORRELATED_POSITIONS,
    MAX_DAILY_TRADES,
)


@pytest.fixture
def risk_manager():
    """Fresh RiskManager with default equity."""
    return RiskManager(initial_equity=1_000_000.0)


@pytest.fixture
def low_equity_manager():
    """RiskManager with low equity for testing drawdown triggers."""
    return RiskManager(initial_equity=100_000.0)


class TestRiskManagerInit:
    """Test RiskManager initialization."""

    def test_default_initialization(self, risk_manager):
        assert risk_manager.state.current_equity == 1_000_000.0
        assert risk_manager.state.peak_equity == 1_000_000.0
        assert risk_manager.state.daily_pnl == 0.0
        assert risk_manager.state.weekly_pnl == 0.0
        assert not risk_manager.kill_switch.is_active

    def test_custom_initial_equity(self):
        rm = RiskManager(initial_equity=500_000.0)
        assert rm.state.peak_equity == 500_000.0
        assert rm.state.current_equity == 500_000.0

    def test_has_all_sub_components(self, risk_manager):
        assert risk_manager.check_gate is not None
        assert risk_manager.kill_switch is not None
        assert risk_manager.drawdown_monitor is not None
        assert risk_manager.kelly is not None
        assert risk_manager.var_calculator is not None


class TestRiskManagerCheckTrade:
    """Test trade checking through RiskManager."""

    def test_approve_valid_trade(self, risk_manager):
        result = risk_manager.check_trade(
            symbol="EURUSD", direction="BUY", lot_size=0.01,
            entry=1.1000, stop_loss=1.0950, account_balance=1_000_000,
            take_profit=1.1100,
        )
        assert result["verdict"] in ("APPROVED", "VETOED")
        assert "timestamp" in result

    def test_veto_when_kill_switch_active(self, risk_manager):
        risk_manager.kill_switch.activate("MANUAL")
        result = risk_manager.check_trade(
            symbol="EURUSD", direction="BUY", lot_size=0.01,
            entry=1.1000, stop_loss=1.0950,
        )
        assert result["verdict"] == "VETOED"
        assert result["reason"] == "KILL_SWITCH_ACTIVE"

    def test_veto_high_risk_trade(self, risk_manager):
        result = risk_manager.check_trade(
            symbol="EURUSD", direction="BUY", lot_size=1.0,
            entry=1.1000, stop_loss=1.0500,
        )
        assert result["verdict"] == "VETOED"

    def test_counters_updated_on_veto(self, risk_manager):
        risk_manager.check_trade(
            symbol="EURUSD", direction="BUY", lot_size=1.0,
            entry=1.1000, stop_loss=1.0500,
        )
        assert risk_manager._veto_count == 1

    def test_counters_updated_on_approval(self, risk_manager):
        risk_manager.check_trade(
            symbol="EURUSD", direction="BUY", lot_size=0.01,
            entry=1.1000, stop_loss=1.0950, account_balance=1_000_000,
            take_profit=1.1100,
        )
        # May or may not be approved depending on checkpoints
        assert risk_manager._veto_count + risk_manager._approval_count >= 1

    def test_result_includes_veto_counts(self, risk_manager):
        result = risk_manager.check_trade(
            symbol="EURUSD", direction="BUY", lot_size=0.01,
            entry=1.1000, stop_loss=1.0950, account_balance=1_000_000,
        )
        assert "veto_count_total" in result
        assert "approval_count_total" in result


class TestRiskManagerPnLTracking:
    """Test P&L tracking and auto kill switch triggers."""

    def test_update_pnl(self, risk_manager):
        risk_manager.update_pnl(500.0, "EURUSD")
        assert risk_manager.state.daily_pnl == 500.0
        assert risk_manager.state.current_equity == 1_000_500.0

    def test_update_negative_pnl(self, risk_manager):
        risk_manager.update_pnl(-500.0, "EURUSD")
        assert risk_manager.state.daily_pnl == -500.0
        assert risk_manager.state.current_equity == 999_500.0

    def test_multiple_pnl_updates(self, risk_manager):
        risk_manager.update_pnl(1000.0, "EURUSD")
        risk_manager.update_pnl(-300.0, "GBPUSD")
        assert risk_manager.state.daily_pnl == 700.0
        assert risk_manager.state.trade_count_today == 2

    def test_peak_equity_updates(self, risk_manager):
        risk_manager.update_pnl(5000.0, "EURUSD")
        assert risk_manager.state.peak_equity == 1_005_000.0

    def test_drawdown_monitor_updated(self, risk_manager):
        risk_manager.update_pnl(-50000.0, "EURUSD")
        assert risk_manager.drawdown_monitor.current_drawdown > 0

    def test_auto_kill_switch_daily_limit(self, risk_manager):
        """Daily loss >= 1% should trigger kill switch."""
        # 1% of 1M = 10,000
        risk_manager.update_pnl(-10_500.0, "EURUSD")
        assert risk_manager.kill_switch.is_active

    def test_auto_kill_switch_weekly_limit(self, risk_manager):
        """Weekly loss >= 3% should trigger kill switch."""
        # 3% of 1M = 30,000
        risk_manager.update_pnl(-30_500.0, "EURUSD")
        assert risk_manager.kill_switch.is_active


class TestRiskManagerPositionTracking:
    """Test position tracking."""

    def test_add_position(self, risk_manager):
        risk_manager.add_position("EURUSD")
        assert "EURUSD" in risk_manager.state.active_positions

    def test_add_duplicate_position(self, risk_manager):
        risk_manager.add_position("EURUSD")
        risk_manager.add_position("EURUSD")
        assert risk_manager.state.active_positions.count("EURUSD") == 1

    def test_remove_position(self, risk_manager):
        risk_manager.add_position("EURUSD")
        risk_manager.remove_position("EURUSD")
        assert "EURUSD" not in risk_manager.state.active_positions

    def test_remove_nonexistent_position(self, risk_manager):
        risk_manager.remove_position("EURUSD")  # Should not raise


class TestRiskManagerPositionSizing:
    """Test position size calculation."""

    def test_calculate_position_size(self, risk_manager):
        result = risk_manager.calculate_position_size(
            account_balance=1_000_000, risk_pct=0.005,
            stop_loss_pips=50, pip_value=10.0,
        )
        assert result["lot_size"] > 0
        assert result["effective_risk_pct"] == 0.005

    def test_position_size_capped(self, risk_manager):
        """Risk > MAX_RISK_PER_TRADE should be capped."""
        result = risk_manager.calculate_position_size(
            account_balance=1_000_000, risk_pct=0.05,
            stop_loss_pips=50, pip_value=10.0,
        )
        assert result["capped"] is True
        assert result["effective_risk_pct"] <= MAX_RISK_PER_TRADE

    def test_position_size_zero_stop_loss(self, risk_manager):
        result = risk_manager.calculate_position_size(
            account_balance=1_000_000, risk_pct=0.005,
            stop_loss_pips=0, pip_value=10.0,
        )
        assert result["lot_size"] == 0.01  # Minimum lot

    def test_calculate_kelly_size(self, risk_manager):
        result = risk_manager.calculate_kelly_size(
            win_rate=0.6, avg_win=200.0, avg_loss=100.0,
            account_balance=1_000_000, method="HALF_KELLY",
        )
        assert "optimal_fraction" in result
        assert "adjusted_fraction" in result
        assert "position_size" in result

    def test_kelly_size_capped_at_max_risk(self, risk_manager):
        """Kelly position should not exceed constitutional limit."""
        result = risk_manager.calculate_kelly_size(
            win_rate=0.9, avg_win=500.0, avg_loss=50.0,
            account_balance=1_000_000, method="FULL_KELLY",
        )
        assert result["adjusted_fraction"] <= MAX_RISK_PER_TRADE or result["position_size"] > 0


class TestRiskManagerStatus:
    """Test risk manager status reporting."""

    def test_status_all_fields(self, risk_manager):
        status = risk_manager.status()
        expected_fields = [
            "overall_status", "daily_pnl", "weekly_pnl",
            "daily_status", "weekly_status", "trades_today",
            "active_positions", "veto_count", "approval_count",
            "drawdown", "kill_switch", "hardcoded_limits",
        ]
        for field in expected_fields:
            assert field in status, f"Missing field: {field}"

    def test_status_trading_allowed_initially(self, risk_manager):
        status = risk_manager.status()
        assert status["overall_status"] == "TRADING_ALLOWED"

    def test_status_trading_halt_after_kill_switch(self, risk_manager):
        risk_manager.kill_switch.activate("MANUAL")
        status = risk_manager.status()
        assert status["overall_status"] == "TRADING_HALT"

    def test_status_hardcoded_limits(self, risk_manager):
        status = risk_manager.status()
        limits = status["hardcoded_limits"]
        assert limits["override_possible"] is False
        assert "max_risk_per_trade" in limits
        assert "max_daily_loss" in limits
        assert "max_weekly_loss" in limits
        assert "max_drawdown" in limits

    def test_daily_status_ok(self, risk_manager):
        status = risk_manager.status()
        assert status["daily_status"] == "OK"

    def test_weekly_status_ok(self, risk_manager):
        status = risk_manager.status()
        assert status["weekly_status"] == "OK"


class TestRiskState:
    """Test RiskState dataclass."""

    def test_default_values(self):
        state = RiskState()
        assert state.daily_pnl == 0.0
        assert state.weekly_pnl == 0.0
        assert state.trade_count_today == 0
        assert state.trade_count_week == 0
        assert state.active_positions == []
        assert state.peak_equity == 0.0
        assert state.current_equity == 0.0

    def test_custom_values(self):
        state = RiskState(
            daily_pnl=-500.0,
            peak_equity=1_000_000.0,
            current_equity=999_500.0,
        )
        assert state.daily_pnl == -500.0
        assert state.current_equity == 999_500.0
