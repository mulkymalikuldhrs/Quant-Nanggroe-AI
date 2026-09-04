"""tests/test_execution/test_metadata_forwarding.py — pin test for the live-fill
perStrategy/perRegime metadata contract.

Writer: quant_nanggroe/engine/agentic/autonomous.py::_make_decision sets
  metadata {"strategy", "strategy_name" (legacy), "regime", ...}.
Reader: quant_nanggroe/engine/execution/manager.py::metadata_overrides +
  execute_order forwards strategy/regime into RiskManager.check_trade.

Regression covered: writer used "strategy_name" only and no "regime" key,
while the reader read "strategy"/"regime" — both always None on live fills,
so perStrategy/perRegime overrides silently never applied.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.engine.execution.manager import ExecutionManager, GuardResult, metadata_overrides

# ── narrow seam: metadata_overrides() ─────────────────────────────────────────

def test_metadata_overrides_new_keys():
    out = metadata_overrides({"strategy": "kaufman_ama", "regime": "trending"})
    assert out == {"strategy": "kaufman_ama", "regime": "trending"}


def test_metadata_overrides_legacy_strategy_name_fallback():
    # Old orders carry only "strategy_name" — must still resolve the strategy.
    out = metadata_overrides({"strategy_name": "kaufman_ama"})
    assert out["strategy"] == "kaufman_ama"
    assert out["regime"] is None


def test_metadata_overrides_new_key_wins_over_legacy():
    out = metadata_overrides({"strategy": "kaufman_ama", "strategy_name": "stale", "regime": "ranging"})
    assert out["strategy"] == "kaufman_ama"
    assert out["regime"] == "ranging"


def test_metadata_overrides_missing_fail_closed():
    assert metadata_overrides(None) == {"strategy": None, "regime": None}
    assert metadata_overrides({}) == {"strategy": None, "regime": None}
    assert metadata_overrides("garbage") == {"strategy": None, "regime": None}


# ── full path: execute_order → RiskManager.check_trade kwargs ─────────────────

class _StubBroker:
    name = "stub"
    is_connected = True

    async def get_account(self):
        return SimpleNamespace(balance=10000.0)

    async def get_positions(self):
        return []

    async def submit_order(self, order):
        order.status = OrderStatus.FILLED
        order.metadata = {**(order.metadata or {}), "fill_price": 1.1000}
        return order


class _StubRiskManager:
    def __init__(self):
        self.state = SimpleNamespace(
            current_equity=10000.0, peak_equity=10000.0, daily_pnl=0.0, weekly_pnl=0.0
        )
        self.calls: list[dict] = []

    def check_trade(self, **kwargs):
        self.calls.append(kwargs)
        return {"verdict": "ALLOW"}


def _wired_manager(monkeypatch):
    em = ExecutionManager()
    em._kill_switch = None  # isolate metadata forwarding from kill-switch state
    monkeypatch.setattr(
        em, "_run_guards", lambda order: GuardResult(True, "test", "pinned")
    )
    risk = _StubRiskManager()
    em.set_risk_manager(risk)
    em.add_broker(_StubBroker(), primary=True)
    return em, risk


def _order(metadata: dict) -> Order:
    return Order(
        id=str(uuid.uuid4()),
        symbol="EURUSD.vxc",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.01,
        status=OrderStatus.PENDING,
        metadata=metadata,
    )


@pytest.mark.asyncio
async def test_execute_order_forwards_strategy_and_regime(monkeypatch):
    em, risk = _wired_manager(monkeypatch)
    fill = await em.execute_order(
        _order({"strategy": "kaufman_ama", "strategy_name": "kaufman_ama",
                "regime": "trending", "symbol": "EURUSD.vxc"})
    )
    assert fill is not None
    assert len(risk.calls) == 1
    assert risk.calls[0]["strategy"] == "kaufman_ama"
    assert risk.calls[0]["regime"] == "trending"


@pytest.mark.asyncio
async def test_execute_order_forwards_legacy_strategy_name(monkeypatch):
    em, risk = _wired_manager(monkeypatch)
    fill = await em.execute_order(_order({"strategy_name": "kaufman_ama"}))
    assert fill is not None
    assert len(risk.calls) == 1
    assert risk.calls[0]["strategy"] == "kaufman_ama"
    assert risk.calls[0]["regime"] is None
