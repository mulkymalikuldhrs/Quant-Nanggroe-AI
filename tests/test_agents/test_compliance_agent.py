"""Tests for ComplianceAgent."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from quant_nanggroe.agents.compliance.agent import (
    ComplianceAgent,
    ComplianceVerdict,
    VerdictStatus,
)


@pytest.fixture
def agent():
    return ComplianceAgent()


class TestComplianceAgent:
    def test_trade_approval(self, agent):
        v = agent.check_trade("BTC/USDT", "BUY", 0.001, strategy="Momentum", equity=10000.0)
        assert v.status == VerdictStatus.APPROVED
        assert v.check_name == "trade_check"

    def test_trade_rejection_limit_exceeded(self, agent):
        v = agent.check_trade("BTC/USDT", "BUY", 100, strategy="Momentum", equity=10000.0)
        assert v.status == VerdictStatus.REJECT
        assert v.check_name == "position_limit"

    def test_portfolio_concentration_check(self, agent):
        positions = {
            "BTC/USDT": {"quantity": 1, "current_price": 7000},
            "ETH/USDT": {"quantity": 10, "current_price": 300},
        }
        result = agent.check_portfolio(positions, equity=10000.0)
        assert result["num_positions"] == 2
        assert "concentration_ratio" in result
        assert result["equity"] == 10000.0

    def test_portfolio_no_breaches(self, agent):
        positions = {
            "BTC/USDT": {"quantity": 0.01, "current_price": 70000},
        }
        result = agent.check_portfolio(positions, equity=10000.0)
        assert len(result["limit_breaches"]) == 0

    def test_portfolio_limit_breach(self, agent):
        positions = {
            "BTC/USDT": {"quantity": 2, "current_price": 70000},
        }
        result = agent.check_portfolio(positions, equity=10000.0)
        assert len(result["limit_breaches"]) >= 1

    def test_status_output(self, agent):
        s = agent.status()
        assert s["agent"] == "compliance"
        assert s["role"] == "compliance"
        assert "checks" in s
        assert "position_limit" in s["checks"]
        assert "timestamp" in s

    def test_unknown_strategy_flagged(self, agent):
        v = agent.check_trade("BTC/USDT", "BUY", 0.001, strategy="unknown_strat", equity=10000.0)
        assert v.status == VerdictStatus.FLAG
        assert v.check_name == "strategy_origin"

    def test_audit_log_check_no_audit(self, agent):
        result = agent.audit_log_check(MagicMock(entries=[]))
        assert isinstance(result, dict)
        assert "total_entries" in result

    def test_wall_violations_empty(self, agent):
        wall = MagicMock()
        wall._access_log = []
        result = agent.check_wall_violations(wall)
        assert result["violation_count"] == 0

    def test_compliance_verdict_dataclass(self):
        v = ComplianceVerdict(
            status=VerdictStatus.REJECT,
            reason="test rejection",
            severity="ERROR",
            check_name="test_check",
        )
        assert v.status == VerdictStatus.REJECT
        assert v.reason == "test rejection"
        assert v.check_name == "test_check"
        assert hasattr(v, "timestamp")
