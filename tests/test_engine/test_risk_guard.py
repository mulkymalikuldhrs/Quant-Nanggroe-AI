"""
Tests for Constitutional Risk Guard — 9-Checkpoint VETO System
================================================================
Uses ConstitutionalRiskGuard.check_trade() and RiskCheckResult.
Every checkpoint must be individually tested.
"""

from __future__ import annotations

import pytest

from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard, RiskCheckResult
from quant_nanggroe_ai.config import (
    MAX_RISK_PER_TRADE,
    MAX_DAILY_LOSS,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
    MAX_CORRELATED_POSITIONS,
)


class TestConstitutionalRiskGuard:
    """Test the 9-checkpoint constitutional risk guard."""

    @pytest.fixture
    def guard(self) -> ConstitutionalRiskGuard:
        """Fresh guard instance for each test."""
        return ConstitutionalRiskGuard()

    # ── All 9 Checkpoints Pass → APPROVED ─────────────────────────────

    def test_all_checkpoints_pass_approved(self, guard: ConstitutionalRiskGuard) -> None:
        """Valid trade with all checkpoints passing should be APPROVED."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0,
            take_profit=1.1150,  # R:R = 0.015/0.005 = 3.0 (well above 2.0 minimum)
        )
        assert result.verdict == "APPROVED"
        assert all(cp.passed for cp in result.checkpoints.values())

    # ── Checkpoint 1: Risk per trade ≤ 0.5% ──────────────────────────

    def test_checkpoint1_risk_per_trade_exceeded(self, guard: ConstitutionalRiskGuard) -> None:
        """Large lot size causing risk > 0.5% should be VETOED at checkpoint 1."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=1.0,  # 1 standard lot = $100,000
            entry=1.1000,
            stop_loss=1.0500,  # 500 pips → huge risk
            account_balance=10000.0,
            take_profit=1.2000,
        )
        assert result.verdict == "VETOED"
        assert not result.checkpoints["1_risk_per_trade"].passed
        assert result.checkpoints["1_risk_per_trade"].name == "1_risk_per_trade"

    def test_checkpoint1_risk_within_limit(self, guard: ConstitutionalRiskGuard) -> None:
        """Small trade within 0.5% risk should pass checkpoint 1."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0995,  # 5 pips risk → tiny
            account_balance=100000.0,
            take_profit=1.1020,
        )
        assert result.checkpoints["1_risk_per_trade"].passed

    # ── Checkpoint 2: Daily loss < 1.0% ──────────────────────────────

    def test_checkpoint2_daily_loss_exceeded(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade when daily loss ≥ 1% should be VETOED at checkpoint 2."""
        guard.daily_pnl = -0.015  # -1.5% daily loss
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0995,
            account_balance=10000.0,
            take_profit=1.1020,
        )
        assert result.verdict == "VETOED"
        assert not result.checkpoints["2_daily_loss"].passed

    def test_checkpoint2_daily_loss_ok(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade when daily loss < 1% should pass checkpoint 2."""
        guard.daily_pnl = -0.005  # -0.5% daily loss
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0995,
            account_balance=10000.0,
            take_profit=1.1020,
        )
        assert result.checkpoints["2_daily_loss"].passed

    # ── Checkpoint 3: Weekly loss < 3.0% ─────────────────────────────

    def test_checkpoint3_weekly_loss_exceeded(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade when weekly loss ≥ 3% should be VETOED at checkpoint 3."""
        guard.weekly_pnl = -0.04  # -4% weekly loss
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0995,
            account_balance=10000.0,
            take_profit=1.1020,
        )
        assert result.verdict == "VETOED"
        assert not result.checkpoints["3_weekly_loss"].passed

    def test_checkpoint3_weekly_loss_ok(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade when weekly loss < 3% should pass checkpoint 3."""
        guard.weekly_pnl = -0.02  # -2% weekly loss
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0995,
            account_balance=10000.0,
            take_profit=1.1020,
        )
        assert result.checkpoints["3_weekly_loss"].passed

    # ── Checkpoint 4: Risk:Reward ≥ 1:2 ──────────────────────────────

    def test_checkpoint4_rr_ratio_insufficient(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade with R:R < 1:2 should be VETOED at checkpoint 4."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0990,
            account_balance=10000.0,
            take_profit=1.1010,  # TP=10 pips, SL=10 pips → R:R = 1:1
        )
        assert not result.checkpoints["4_risk_reward"].passed

    def test_checkpoint4_rr_ratio_sufficient(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade with R:R ≥ 1:2 should pass checkpoint 4."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0990,
            account_balance=10000.0,
            take_profit=1.1030,  # TP=30 pips, SL=10 pips → R:R = 1:3 (clearly above 2.0)
        )
        assert result.checkpoints["4_risk_reward"].passed

    # ── Checkpoint 5: Stop loss exists ────────────────────────────────

    def test_checkpoint5_no_stop_loss(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade without stop loss should be VETOED at checkpoint 5."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=None,
            account_balance=10000.0,
        )
        assert result.verdict == "VETOED"
        assert not result.checkpoints["5_stop_loss_exists"].passed

    def test_checkpoint5_stop_loss_zero(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade with stop_loss=0 should fail checkpoint 5."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=0.0,
            account_balance=10000.0,
        )
        assert not result.checkpoints["5_stop_loss_exists"].passed

    def test_checkpoint5_stop_loss_exists(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade with valid stop loss should pass checkpoint 5."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0,
        )
        assert result.checkpoints["5_stop_loss_exists"].passed

    # ── Checkpoint 6: Entry is valid (> 0) ───────────────────────────

    def test_checkpoint6_invalid_entry(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade with entry=0 should be VETOED at checkpoint 6."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=0.0,
            stop_loss=1.0950,
            account_balance=10000.0,
        )
        assert not result.checkpoints["6_valid_entry"].passed

    def test_checkpoint6_negative_entry(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade with negative entry should fail checkpoint 6."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=-1.0,
            stop_loss=1.0950,
            account_balance=10000.0,
        )
        assert not result.checkpoints["6_valid_entry"].passed

    # ── Checkpoint 7: Direction is valid ──────────────────────────────

    def test_checkpoint7_invalid_direction(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade with invalid direction should be VETOED at checkpoint 7."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="SIDEWAYS",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0,
        )
        assert not result.checkpoints["7_valid_direction"].passed

    @pytest.mark.parametrize("direction", ["BUY", "SELL", "LONG", "SHORT"])
    def test_checkpoint7_valid_directions(self, guard: ConstitutionalRiskGuard, direction: str) -> None:
        """All valid directions should pass checkpoint 7."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction=direction,
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0,
            take_profit=1.1100,
        )
        assert result.checkpoints["7_valid_direction"].passed

    # ── Checkpoint 8: Not overtrading (< 5 trades/day) ───────────────

    def test_checkpoint8_overtrading(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade when 5+ trades already made today should be VETOED at checkpoint 8."""
        guard.trade_count_today = 5
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0,
            take_profit=1.1100,
        )
        assert not result.checkpoints["8_not_overtrading"].passed

    def test_checkpoint8_within_trade_limit(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade when < 5 trades today should pass checkpoint 8."""
        guard.trade_count_today = 4
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0,
            take_profit=1.1100,
        )
        assert result.checkpoints["8_not_overtrading"].passed

    # ── Checkpoint 9: Correlated position check (≤ 3) ────────────────

    def test_checkpoint9_too_many_correlated(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade when 3+ correlated positions exist should be VETOED at checkpoint 9."""
        guard.active_positions = ["EURUSD", "GBPUSD", "AUDUSD"]  # Same USD-weakness group
        result = guard.check_trade(
            symbol="NZDUSD",  # Also in USD-weakness group → 3 existing correlated
            direction="BUY",
            lot_size=0.01,
            entry=0.6200,
            stop_loss=0.6150,
            account_balance=10000.0,
            take_profit=0.6300,
        )
        assert not result.checkpoints["9_correlation_check"].passed

    def test_checkpoint9_correlation_ok(self, guard: ConstitutionalRiskGuard) -> None:
        """Trade with < 3 correlated positions should pass checkpoint 9."""
        guard.active_positions = ["EURUSD", "GBPUSD"]  # 2 correlated with AUDUSD
        result = guard.check_trade(
            symbol="AUDUSD",
            direction="BUY",
            lot_size=0.01,
            entry=0.6600,
            stop_loss=0.6550,
            account_balance=10000.0,
            take_profit=0.6700,
        )
        assert result.checkpoints["9_correlation_check"].passed

    # ── Audit Trail ────────────────────────────────────────────────────

    def test_result_has_all_nine_checkpoints(self, guard: ConstitutionalRiskGuard) -> None:
        """Every check_trade result must contain all 9 checkpoints."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0,
            take_profit=1.1100,
        )
        assert len(result.checkpoints) == 9
        expected_keys = {
            "1_risk_per_trade", "2_daily_loss", "3_weekly_loss",
            "4_risk_reward", "5_stop_loss_exists", "6_valid_entry",
            "7_valid_direction", "8_not_overtrading", "9_correlation_check",
        }
        assert set(result.checkpoints.keys()) == expected_keys

    def test_result_has_audit_fields(self, guard: ConstitutionalRiskGuard) -> None:
        """RiskCheckResult must include timestamp and counters."""
        result = guard.check_trade(
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.01,
            entry=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0,
            take_profit=1.1100,
        )
        assert result.timestamp is not None
        assert isinstance(result.veto_count_total, int)
        assert isinstance(result.approval_count_total, int)

    def test_veto_and_approval_counts(self, guard: ConstitutionalRiskGuard) -> None:
        """Veto/approval counters must track correctly across calls."""
        # First: approved trade (use TP that gives R:R well above 2.0)
        r1 = guard.check_trade(
            symbol="EURUSD", direction="BUY", lot_size=0.01,
            entry=1.1000, stop_loss=1.0950, account_balance=10000.0, take_profit=1.1150,
        )
        assert r1.approval_count_total == 1
        assert r1.veto_count_total == 0

        # Second: vetoed trade (no stop loss)
        r2 = guard.check_trade(
            symbol="EURUSD", direction="BUY", lot_size=0.01,
            entry=1.1000, stop_loss=None, account_balance=10000.0,
        )
        assert r2.veto_count_total == 1
        assert r2.approval_count_total == 1

    # ── Lot Size Calculation ───────────────────────────────────────────

    def test_calculate_lot_size_caps_risk(self, guard: ConstitutionalRiskGuard) -> None:
        """Lot size calculation must cap risk at hardcoded MAX_RISK_PER_TRADE."""
        result = guard.calculate_lot_size(
            account_balance=10000.0,
            risk_pct=0.02,  # Request 2% — should be capped to 0.5%
            stop_loss_pips=50.0,
        )
        assert result["capped"] is True
        assert result["effective_risk_pct"] == f"{MAX_RISK_PER_TRADE:.4f}"

    def test_calculate_lot_size_within_limit(self, guard: ConstitutionalRiskGuard) -> None:
        """Lot size with risk below cap should not be capped."""
        result = guard.calculate_lot_size(
            account_balance=10000.0,
            risk_pct=0.003,  # 0.3% < 0.5% cap
            stop_loss_pips=50.0,
        )
        assert result["capped"] is False
        assert float(result["effective_risk_pct"]) == pytest.approx(0.003, abs=0.0001)

    # ── Status ─────────────────────────────────────────────────────────

    def test_status_returns_expected_keys(self, guard: ConstitutionalRiskGuard) -> None:
        """Status must include all expected keys."""
        status = guard.status()
        assert "overall_status" in status
        assert "daily_pnl" in status
        assert "weekly_pnl" in status
        assert "hardcoded_limits" in status
        assert status["hardcoded_limits"]["override_possible"] is False
