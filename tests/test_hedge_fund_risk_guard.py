"""Tests: Hedge Fund Risk Guard — weekly loss veto, daily loss, position sizing.

Run: python -m pytest tests/test_hedge_fund_risk_guard.py -v
"""

import sys
from pathlib import Path

# Allow hedge_fund.tools.risk_guard import from test runner
_HF_TOOLS = Path(__file__).resolve().parents[1] / "quant_nanggroe" / "hedge_fund" / "tools"
sys.path.insert(0, str(_HF_TOOLS))

from risk_guard import calculate_risk_score, approve


class TestWeeklyLossVeto:
    """Weekly loss veto in calculate_risk_score must fire at boundary."""

    BALANCE = 10_000.0
    POLICY = {
        "risk_max_drawdown_stop": 0.20,
        "max_leverage": 3.0,
        "max_daily_loss": 0.05,
        "max_weekly_loss": 0.03,
        "max_position_size": 0.02,
        "risk_score_threshold": 0.8,
        "concentration_limit": 0.3,
    }

    def _base_proposal(self, **overrides) -> dict:
        p = {
            "symbol": "EURUSD",
            "action": "buy",
            "volume": 0.01,
            "price": 1.1000,
            "sl": 1.0950,
            "account_balance": self.BALANCE,
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "open_positions": 0,
            "market_volatility": 0.001,
        }
        p.update(overrides)
        return p

    def test_weekly_loss_at_exact_threshold_triggers_veto(self):
        """weekly_pnl at exactly max_weekly_loss (3% of balance) -> veto risk=0.85 > 0.8"""
        proposal = self._base_proposal(weekly_pnl=-self.BALANCE * 0.03)
        risk, reasons = calculate_risk_score(proposal, self.POLICY)
        assert risk >= 0.85, f"Expected risk >=0.85 at 3% weekly loss, got {risk}"
        assert any("weekly_loss" in r for r in reasons), (
            f"Expected weekly_loss reason, got {reasons}"
        )
        result = approve(proposal)
        assert result["status"] == "VETOED", (
            f"Expected VETOED at 3% weekly loss, got {result['status']}"
        )
        assert result["risk_score"] >= 0.85

    def test_weekly_loss_above_hard_limit_triggers_full_veto(self):
        """weekly_pnl at 4% (> 3% * 1.2 = 3.6%) -> veto risk=1.0"""
        proposal = self._base_proposal(weekly_pnl=-self.BALANCE * 0.04)
        risk, reasons = calculate_risk_score(proposal, self.POLICY)
        assert risk >= 1.0, f"Expected risk=1.0 at 4% weekly loss, got {risk}"
        assert any("weekly_loss_limit_hit" in r for r in reasons)

    def test_weekly_loss_below_threshold_no_veto(self):
        """weekly_pnl at 1% (< 3%) -> no weekly loss reason, risk from other factors"""
        proposal = self._base_proposal(weekly_pnl=-self.BALANCE * 0.01)
        risk, reasons = calculate_risk_score(proposal, self.POLICY)
        assert not any("weekly_loss" in r for r in reasons), (
            f"Expected no weekly_loss reason at 1% loss, got {reasons}"
        )

    def test_weekly_loss_missing_degrades_gracefully(self):
        """weekly_pnl=None -> risk=0.5 baseline, no weekly_loss reason"""
        proposal = self._base_proposal(weekly_pnl=None)
        risk, reasons = calculate_risk_score(proposal, self.POLICY)
        assert risk >= 0.5, f"Expected risk>=0.5 when weekly_pnl missing, got {risk}"
        assert not any("weekly_loss" in r for r in reasons), (
            f"Expected no weekly_loss reason when weekly_pnl missing, got {reasons}"
        )
        result = approve(proposal)
        # At risk=0.5 with no other reason, no_risk_evidence_veto fires -> risk=1.0
        assert result["status"] == "VETOED"

    def test_weekly_loss_positive_does_not_fire(self):
        """positive weekly_pnl -> week_loss_ratio=0 -> no weekly reason"""
        proposal = self._base_proposal(weekly_pnl=500.0)
        risk, reasons = calculate_risk_score(proposal, self.POLICY)
        assert not any("weekly_loss" in r for r in reasons)


class TestDailyLossVeto:
    """Daily loss still works as expected (regression)."""

    BALANCE = 10_000.0
    POLICY = {
        "risk_max_drawdown_stop": 0.20,
        "max_leverage": 3.0,
        "max_daily_loss": 0.05,
        "max_weekly_loss": 0.03,
        "max_position_size": 0.02,
        "risk_score_threshold": 0.8,
        "concentration_limit": 0.3,
    }

    def _base_proposal(self, **overrides) -> dict:
        p = {
            "symbol": "EURUSD",
            "action": "buy",
            "volume": 0.01,
            "price": 1.1000,
            "sl": 1.0950,
            "account_balance": self.BALANCE,
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "open_positions": 0,
            "market_volatility": 0.001,
        }
        p.update(overrides)
        return p

    def test_daily_loss_at_exact_threshold_triggers_veto(self):
        """daily_pnl at exactly max_daily_loss (5% of balance) -> risk=0.85 >= gate"""
        proposal = self._base_proposal(daily_pnl=-self.BALANCE * 0.05)
        risk, reasons = calculate_risk_score(proposal, self.POLICY)
        assert risk >= 0.85, f"Expected risk>=0.85 at 5% daily loss, got {risk}"
        assert any("daily_loss" in r for r in reasons)