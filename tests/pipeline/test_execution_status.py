"""Tests: UnifiedExecutionRouter always reports an honest 'executed' flag.

Every return path of execute() must include the "executed" key, and it
may only be True when a fill/order is actually confirmed.
"""

from __future__ import annotations

from quant_nanggroe.pipeline.execution import UnifiedExecutionRouter


class _KillSwitchStub:
    def __init__(self, allow: bool = True):
        self._allow = allow

    def can_trade(self) -> bool:
        return self._allow


class _RiskManagerStub:
    def check_trade(self, **kwargs):
        return {"verdict": "APPROVED"}


def _disable_backends(router, monkeypatch):
    monkeypatch.setattr(router, "_lazy_production", lambda: None)
    monkeypatch.setattr(router, "_lazy_mt5", lambda: None)
    monkeypatch.setattr(router, "_lazy_paper", lambda: None)
    monkeypatch.setattr(router, "_lazy_engine", lambda: None)


def test_reject_dict_has_executed_false():
    router = UnifiedExecutionRouter()
    rej = router._reject("EURUSD", "buy", 1.1, 0.01, "test")
    assert rej["executed"] is False
    assert rej["status"] == "rejected"


def test_kill_switch_reject_includes_executed():
    router = UnifiedExecutionRouter()
    router._kill_switch = _KillSwitchStub(allow=False)
    result = router.execute("EURUSD", "buy", 1.1)
    assert result["status"] == "rejected"
    assert result["executed"] is False


def test_live_zero_balance_fails_closed(monkeypatch):
    router = UnifiedExecutionRouter(allow_live=True)
    router._kill_switch = _KillSwitchStub()
    monkeypatch.setattr(router, "get_balance", lambda: 0.0)
    result = router.execute("EURUSD", "buy", 1.1)
    assert result["status"] == "rejected"
    assert result["executed"] is False
    assert "failing closed" in result["error"]


def test_paper_zero_balance_uses_synthetic_but_no_backend_executed_false(monkeypatch):
    router = UnifiedExecutionRouter(allow_live=False)
    router._kill_switch = _KillSwitchStub()
    router._risk_manager = _RiskManagerStub()
    monkeypatch.setattr(router, "get_balance", lambda: 0.0)
    _disable_backends(router, monkeypatch)
    result = router.execute("EURUSD", "buy", 1.1)
    assert result["mode"] == "no_backend"
    assert result["status"] == "rejected"
    assert result["executed"] is False


def test_mt5_live_path_executed_true(monkeypatch):
    router = UnifiedExecutionRouter(allow_live=True)
    router._kill_switch = _KillSwitchStub()
    router._risk_manager = _RiskManagerStub()
    monkeypatch.setattr(router, "get_balance", lambda: 5000.0)
    monkeypatch.setattr(router, "_lazy_production", lambda: None)
    monkeypatch.setattr(router, "_lazy_mt5", lambda: None)

    class FakeMT5:
        def place_order(self, order):
            return 12345

    router._mt5 = FakeMT5()
    result = router.execute("EURUSD", "buy", 1.1, qty=0.01)
    assert result["mode"] == "mt5-live"
    assert result["ticket"] == 12345
    assert result["executed"] is True


def test_engine_path_executed_true(monkeypatch):
    router = UnifiedExecutionRouter(allow_live=False)
    router._kill_switch = _KillSwitchStub()
    router._risk_manager = _RiskManagerStub()
    monkeypatch.setattr(router, "get_balance", lambda: 5000.0)
    monkeypatch.setattr(router, "_lazy_production", lambda: None)
    monkeypatch.setattr(router, "_lazy_mt5", lambda: None)
    monkeypatch.setattr(router, "_lazy_paper", lambda: None)
    monkeypatch.setattr(router, "_lazy_engine", lambda: None)

    class FakeFill:
        id = "fill-1"

    class FakeEngine:
        def execute_order(self, order):
            return FakeFill()

    router._engine = FakeEngine()
    result = router.execute("EURUSD", "buy", 1.1, qty=0.01)
    assert result["mode"] == "engine"
    assert result["fill_id"] == "fill-1"
    assert result["executed"] is True


def test_production_fallback_dict_not_marked_executed(monkeypatch):
    """ProductionExecutionManager 'fallback' mode has no fill — executed must be False."""
    router = UnifiedExecutionRouter(allow_live=False)
    router._kill_switch = _KillSwitchStub()
    router._risk_manager = _RiskManagerStub()
    monkeypatch.setattr(router, "get_balance", lambda: 5000.0)
    monkeypatch.setattr(router, "_lazy_production", lambda: None)

    class FakeProduction:
        def execute_signal(self, sig, price, balance):
            # mirrors the bridge's "fallback" dict: no ticket/fill_id/status
            return {"symbol": sig.symbol, "side": sig.side, "qty": 0.01,
                    "price": price, "strategy": sig.strategy, "mode": "fallback"}

    router._production = FakeProduction()
    result = router.execute("EURUSD", "buy", 1.1, qty=0.01)
    assert result["mode"] == "fallback"
    assert result["executed"] is False
