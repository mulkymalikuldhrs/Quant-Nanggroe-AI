"""
Tests for the Risk Agent - the most critical component.

Validates the 9-checkpoint risk gate, constitutional limits enforcement,
kill switch functionality, and risk tools (VaR, CVaR, Kelly, drawdown).
"""

import json
import math
import pytest
from unittest.mock import MagicMock

from langchain_core.language_models import BaseChatModel

from quant_nanggroe.agents.risk.agent import RiskAgent
from quant_nanggroe.agents.risk.tools import (
    RISK_TOOLS,
    _is_correlated,
    compute_var,
    compute_cvar,
    check_drawdown,
    kelly_sizing,
    kill_switch,
)
from quant_nanggroe.agents.state import (
    AgentState,
    RiskCheckpoint,
    RiskVerdict,
    TradeAction,
    create_initial_state,
    MAX_CORRELATED_POSITIONS,
    MAX_DAILY_LOSS,
    MAX_DRAWDOWN_PCT,
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
)


class TestCorrelationCheck:
    """Test the correlation checking utility."""

    def test_correlated_forex_usd_weakness(self):
        """EURUSD and GBPUSD should be correlated."""
        assert _is_correlated("EURUSD", "GBPUSD") is True

    def test_correlated_forex_usd_strength(self):
        """USDJPY and USDCHF should be correlated."""
        assert _is_correlated("USDJPY", "USDCHF") is True

    def test_correlated_precious_metals(self):
        """XAUUSD and XAGUSD should be correlated."""
        assert _is_correlated("XAUUSD", "XAGUSD") is True

    def test_correlated_crypto(self):
        """BTCUSDT and ETHUSDT should be correlated."""
        assert _is_correlated("BTCUSDT", "ETHUSDT") is True

    def test_uncorrelated_assets(self):
        """AAPL and EURUSD should not be correlated."""
        assert _is_correlated("AAPL", "EURUSD") is False

    def test_uncorrelated_different_groups(self):
        """Gold and crypto should not be correlated."""
        assert _is_correlated("XAUUSD", "BTCUSDT") is False

    def test_case_insensitive(self):
        """Correlation check should be case insensitive."""
        assert _is_correlated("eurusd", "GBPUSD") is True


class TestVaRComputation:
    """Test Value at Risk computation."""

    def test_var_95(self):
        """Should compute VaR at 95% confidence."""
        result = json.loads(compute_var.invoke({"portfolio_value": 100000, "confidence_level": 0.95, "holding_period_days": 1, "daily_volatility": 0.02}))
        assert "var_amount" in result
        assert result["confidence_level"] == 0.95
        expected_var = 1.645 * 0.02 * 100000
        assert abs(result["var_amount"] - expected_var) < 10

    def test_var_99(self):
        """Should compute VaR at 99% confidence."""
        result = json.loads(compute_var.invoke({"portfolio_value": 100000, "confidence_level": 0.99, "holding_period_days": 1, "daily_volatility": 0.02}))
        assert result["confidence_level"] == 0.99
        result_95 = json.loads(compute_var.invoke({"portfolio_value": 100000, "confidence_level": 0.95, "holding_period_days": 1, "daily_volatility": 0.02}))
        assert result["var_amount"] > result_95["var_amount"]

    def test_var_scaling(self):
        """VaR should scale with holding period."""
        result_1d = json.loads(compute_var.invoke({"portfolio_value": 100000, "confidence_level": 0.95, "holding_period_days": 1, "daily_volatility": 0.02}))
        result_10d = json.loads(compute_var.invoke({"portfolio_value": 100000, "confidence_level": 0.95, "holding_period_days": 10, "daily_volatility": 0.02}))
        assert result_10d["var_amount"] > result_1d["var_amount"]


class TestCVaRComputation:
    """Test Conditional VaR computation."""

    def test_cvar_95(self):
        """Should compute CVaR at 95% confidence."""
        result = json.loads(compute_cvar.invoke({"portfolio_value": 100000, "confidence_level": 0.95, "daily_volatility": 0.02}))
        assert "cvar_amount" in result
        assert "var_amount" in result
        assert result["cvar_amount"] >= result["var_amount"]


class TestDrawdownCheck:
    """Test drawdown checking."""

    def test_no_drawdown(self):
        """Should pass when no drawdown."""
        result = json.loads(check_drawdown.invoke({"portfolio_value": 100000, "peak_value": 100000}))
        assert result["passed"] is True
        assert result["drawdown_pct"] == 0.0

    def test_small_drawdown(self):
        """Should pass when drawdown within limits."""
        result = json.loads(check_drawdown.invoke({"portfolio_value": 95000, "peak_value": 100000}))
        assert result["passed"] is True
        assert result["drawdown_pct"] == 5.0

    def test_excessive_drawdown(self):
        """Should fail when drawdown exceeds constitutional limit."""
        result = json.loads(check_drawdown.invoke({"portfolio_value": 80000, "peak_value": 100000}))
        assert result["passed"] is False
        assert result["drawdown_pct"] == 20.0
        assert result["kill_switch_trigger"] is True

    def test_near_limit_drawdown(self):
        """Should fail when drawdown is at the constitutional limit."""
        result = json.loads(check_drawdown.invoke({"portfolio_value": 85000, "peak_value": 100000}))
        assert result["passed"] is False
        assert result["drawdown_pct"] == 15.0

    def test_pre_calculated_drawdown(self):
        """Should use pre-calculated drawdown if provided."""
        result = json.loads(check_drawdown.invoke({"portfolio_value": 100000, "peak_value": 100000, "current_drawdown_pct": 8.0}))
        assert result["drawdown_pct"] == 8.0
        assert result["passed"] is True


class TestKellySizing:
    """Test Kelly criterion position sizing."""

    def test_positive_kelly(self):
        """Should compute positive Kelly fraction."""
        result = json.loads(kelly_sizing.invoke({"win_rate": 0.6, "avg_win": 200, "avg_loss": 100, "account_balance": 100000}))
        assert "raw_kelly_fraction" in result
        assert result["raw_kelly_fraction"] > 0
        assert result["half_kelly_fraction"] > 0

    def test_kelly_cap(self):
        """Kelly fraction should be capped at constitutional max."""
        result = json.loads(kelly_sizing.invoke({"win_rate": 0.9, "avg_win": 500, "avg_loss": 100, "account_balance": 100000}))
        assert result["position_size_pct"] <= MAX_POSITION_SIZE_PCT * 100

    def test_negative_kelly(self):
        """Negative Kelly should result in zero position."""
        result = json.loads(kelly_sizing.invoke({"win_rate": 0.3, "avg_win": 100, "avg_loss": 200, "account_balance": 100000}))
        assert result["raw_kelly_fraction"] <= 0

    def test_zero_avg_loss(self):
        """Should handle zero average loss."""
        result = json.loads(kelly_sizing.invoke({"win_rate": 0.6, "avg_win": 200, "avg_loss": 0, "account_balance": 100000}))
        assert result["raw_kelly_fraction"] == 0.0


class TestKillSwitch:
    """Test kill switch tool."""

    def test_check_ok(self):
        """Should return OK when no limits breached."""
        result = json.loads(kill_switch.invoke({"action": "check", "daily_pnl_pct": -0.5, "weekly_pnl_pct": -1.0}))
        assert result["status"] == "OK"

    def test_auto_activate_daily(self):
        """Should auto-activate on daily limit breach."""
        result = json.loads(kill_switch.invoke({"action": "check", "daily_pnl_pct": -1.5, "weekly_pnl_pct": 0}))
        assert result["status"] == "ACTIVATED"
        assert result["reason"] == "AUTO_DAILY_LIMIT"

    def test_auto_activate_weekly(self):
        """Should auto-activate on weekly limit breach."""
        result = json.loads(kill_switch.invoke({"action": "check", "daily_pnl_pct": 0, "weekly_pnl_pct": -4.0}))
        assert result["status"] == "ACTIVATED"
        assert result["reason"] == "AUTO_WEEKLY_LIMIT"

    def test_manual_activate(self):
        """Should manually activate kill switch."""
        result = json.loads(kill_switch.invoke({"action": "activate", "reason": "MANUAL_RISK"}))
        assert result["status"] == "ACTIVATED"

    def test_override_impossible(self):
        """Override should never be possible."""
        result = json.loads(kill_switch.invoke({"action": "activate"}))
        assert result["override_possible"] is False


class TestRiskAgent9Checkpoints:
    """Test the Risk Agent's 9-checkpoint system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MagicMock(spec=BaseChatModel)
        # Mock the LLM chain: bind_tools returns self, invoke returns message with string content
        mock_response = MagicMock()
        mock_response.content = "Risk assessment complete"
        mock_response.tool_calls = []
        self.mock_llm.invoke.return_value = mock_response
        self.mock_llm.bind_tools.return_value = self.mock_llm
        self.risk_agent = RiskAgent(llm=self.mock_llm)

    def test_all_checkpoints_run(self):
        """All 9 checkpoints should be evaluated."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["signals"] = [
            {
                "symbol": "AAPL",
                "action": "BUY",
                "entry_price": 150.0,
                "stop_loss": 145.0,
                "take_profit": 160.0,
                "risk_reward_ratio": 2.0,
                "position_size_pct": 5.0,
            }
        ]
        state["portfolio_state"] = {
            "total_value": 100000,
            "positions": {},
            "leverage": 1.0,
            "max_drawdown_pct": 2.0,
        }

        result = self.risk_agent.run(state)
        assessment = result["risk_assessment"]
        checkpoints = assessment["checkpoints"]

        assert len(checkpoints) == 9
        checkpoint_names = [cp["name"] for cp in checkpoints]
        assert "1_risk_per_trade" in checkpoint_names
        assert "2_daily_loss" in checkpoint_names
        assert "3_weekly_loss" in checkpoint_names
        assert "4_risk_reward" in checkpoint_names
        assert "5_stop_loss_exists" in checkpoint_names
        assert "6_position_size" in checkpoint_names
        assert "7_leverage" in checkpoint_names
        assert "8_drawdown" in checkpoint_names
        assert "9_correlation_check" in checkpoint_names

    def test_veto_on_missing_stop_loss(self):
        """Should VETO when stop loss is missing on BUY signal."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["signals"] = [
            {
                "symbol": "AAPL",
                "action": "BUY",
                "entry_price": 150.0,
                "risk_reward_ratio": 0,
                "position_size_pct": 5.0,
            }
        ]
        state["portfolio_state"] = {
            "total_value": 100000,
            "positions": {},
            "leverage": 1.0,
            "max_drawdown_pct": 2.0,
        }

        result = self.risk_agent.run(state)
        assert result["risk_verdict"] == RiskVerdict.VETOED.value

    def test_kill_switch_active_state(self):
        """Should return KILL_SWITCH when kill switch is already active."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["kill_switch_active"] = True

        result = self.risk_agent.run(state)
        assert result["kill_switch_active"] is True
        assert result["should_halt"] is True

    def test_override_impossible(self):
        """Risk assessment should always show override_possible = False."""
        state = create_initial_state(["AAPL"], "2025-03-01")
        state["signals"] = [
            {
                "symbol": "AAPL",
                "action": "BUY",
                "stop_loss": 145.0,
                "risk_reward_ratio": 2.5,
                "position_size_pct": 5.0,
            }
        ]
        state["portfolio_state"] = {
            "total_value": 100000,
            "positions": {},
            "leverage": 1.0,
            "max_drawdown_pct": 2.0,
        }

        result = self.risk_agent.run(state)
        assert result["risk_assessment"]["override_possible"] is False

    def test_tools_available(self):
        """Risk agent should have all risk tools."""
        tool_names = [t.name for t in self.risk_agent.tools]
        assert "compute_var" in tool_names
        assert "compute_cvar" in tool_names
        assert "check_drawdown" in tool_names
        assert "kelly_sizing" in tool_names
        assert "kill_switch" in tool_names
