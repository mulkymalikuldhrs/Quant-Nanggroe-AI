"""Unit tests for the vector /status P0 rolling-mean fix (no MT5, no network).

api/routes/vector.py keeps the last HISTORY_N manifold snapshots and uses
their mean as P0 (observability-only — never wired to execution).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from quant_nanggroe.api.routes import vector as vector_mod
from quant_nanggroe.api.routes.vector import HISTORY_N, reset_history, vector_status

BASE_RATES = {
    "EURUSD.vx": 1.08, "USDJPY.vx": 137.01, "EURJPY.vx": 147.5,
    "USDCHF.vx": 0.90, "EURCHF.vx": 0.97,
    "USDCAD.vx": 1.36, "EURCAD.vx": 1.47,
}


@pytest.fixture(autouse=True)
def _clean():
    reset_history()
    yield
    reset_history()


@pytest.fixture
def fake_mt5(monkeypatch):
    """Stub build_graph_from_mt5 with controllable rates."""
    import quant_nanggroe.engine.currency_graph as cg

    state = {"rates": dict(BASE_RATES)}

    def _fake(all_pairs=False):
        return SimpleNamespace(rates=dict(state["rates"]))

    monkeypatch.setattr(cg, "build_graph_from_mt5", _fake)
    return state


@pytest.mark.asyncio
async def test_first_call_warming_up_never_triggers(fake_mt5):
    out = await vector_status()
    assert out["warming_up"] is True
    assert out["p0_source"] == "current"
    assert out["history_len"] == 1
    assert out["mispricing"], "expected manifold points"
    for _label, m in out["mispricing"].items():
        assert m["is_trigger"] is False
        assert m["reason"] == "warming up"
        assert m["d"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_rolling_mean_enables_real_trigger(fake_mt5):
    # stable history, then a shock on EURUSD (z-axis of every point)
    for _ in range(5):
        out = await vector_status()
    assert out["warming_up"] is False
    assert out["p0_source"] == "rolling_mean"
    fake_mt5["rates"]["EURUSD.vx"] = 1.30  # +0.22 shock, box sigma=0.05
    out = await vector_status()
    assert out["warming_up"] is False
    assert any(m["is_trigger"] for m in out["mispricing"].values())
    assert all(m["reason"] == "ok" for m in out["mispricing"].values())


@pytest.mark.asyncio
async def test_history_buffer_bounded(fake_mt5):
    for _ in range(HISTORY_N + 10):
        await vector_status()
    assert len(vector_mod._history) == HISTORY_N


def test_vector_route_is_observability_only():
    """vector.py must never wire trade-gate modules (no live-trade path)."""
    src = open(vector_mod.__file__, encoding="utf-8").read()
    import_lines = [ln for ln in src.splitlines()
                    if ln.strip().startswith(("import ", "from "))]
    for banned in ("execution", "broker", "kill_switch", "order"):
        assert not any(banned in ln for ln in import_lines), f"banned import: {banned}"
