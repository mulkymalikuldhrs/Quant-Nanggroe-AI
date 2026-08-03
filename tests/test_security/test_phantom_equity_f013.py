"""F013: phantom-equity defaults must be removed from risk/execution modules."""
from __future__ import annotations

import pytest

from quant_nanggroe.engine.risk.constants import STARTING_CAPITAL
from quant_nanggroe.engine.risk.manager import RiskManager
from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
from quant_nanggroe.engine.execution.guards.max_position import MaxPositionGuard
from quant_nanggroe.agents.bridges.risk_gate_bridge import RiskGateBridge, GateResult, GateVerdict


def test_risk_manager_default_equity_is_starting_capital():
    rm = RiskManager()
    assert rm.state.current_equity == STARTING_CAPITAL
    assert rm.state.peak_equity == STARTING_CAPITAL


def test_drawdown_monitor_default_equity_is_starting_capital():
    dm = DrawdownMonitor()
    assert dm._peak == STARTING_CAPITAL
    assert dm._current_equity == STARTING_CAPITAL


def test_max_position_guard_default_portfolio_is_starting_capital():
    guard = MaxPositionGuard()
    assert guard._portfolio_value == STARTING_CAPITAL


def test_risk_gate_bridge_default_equity_is_starting_capital():
    bridge = RiskGateBridge()
    assert bridge.risk_manager.state.current_equity == STARTING_CAPITAL


def test_risk_manager_check_trade_resolves_none_balance():
    rm = RiskManager()
    result = rm.check_trade(
        symbol="EURUSD",
        direction="BUY",
        lot_size=0.01,
        entry=1.0856,
        stop_loss=1.0756,
        account_balance=None,
    )
    assert result["verdict"] in {"APPROVED", "VETOED", "KILL_SWITCH"}


def test_risk_gate_bridge_evaluate_without_account_balance():
    bridge = RiskGateBridge()
    result = bridge.evaluate(
        symbol="EURUSD",
        direction="BUY",
        lot_size=0.01,
        entry=1.0856,
        stop_loss=1.0756,
        account_balance=None,
    )
    assert isinstance(result, GateResult)
    assert result.verdict in {GateVerdict.APPROVED, GateVerdict.REJECTED, GateVerdict.KILL_SWITCH}
