"""Tests: hedge fund run_once() reports honest execution status.

execute() outcomes must map to:
  - order id returned      → status "executed",     executed True
  - None returned          → status "order_failed", executed False
  - RuntimeError raised    → status "paper_blocked", executed False
"""

from __future__ import annotations

from quant_nanggroe.hedge_fund.portfolio import main as hf_main


def _stub_cycle(monkeypatch, tmp_path):
    """Stub every external call down to execute()."""
    monkeypatch.setattr(hf_main, "_pipeline_connect", lambda result: result)

    gate_file = tmp_path / "gate.json"
    gate_file.write_text('{"pass": true}')
    monkeypatch.setattr(hf_main, "GATE_FILE", gate_file)

    monkeypatch.setattr(hf_main, "_market_snapshot", lambda: (0.0, 0.0))
    monkeypatch.setattr(hf_main, "_build_causal_context", lambda dxy_pct=0.0, zb_pct=0.0: None)
    monkeypatch.setattr(
        hf_main,
        "aggregate",
        lambda symbol, ctx=None, tracker=None, providers=None: {
            "bias": "buy", "confidence": 0.8, "price": 1.1, "sl": 1.09, "votes": [],
        },
    )
    monkeypatch.setattr(hf_main, "calc_atr", lambda symbol: 0.001)
    monkeypatch.setattr(hf_main, "calculate_position_size", lambda signal, balance, atr=None: {"volume": 0.01})
    monkeypatch.setattr(hf_main, "risk_guard_approve", lambda proposal: {"status": "APPROVED", "risk_score": 0.5})


def test_execute_returns_order_id_status_executed(monkeypatch, tmp_path):
    _stub_cycle(monkeypatch, tmp_path)
    monkeypatch.setattr(hf_main, "_execute_order_sync", lambda sig, symbol: 987654)
    result = hf_main.run_once(target_symbol="EURUSD")
    assert result["status"] == "executed"
    assert result["executed"] is True
    assert result["order_id"] == 987654


def test_execute_returns_none_status_order_failed(monkeypatch, tmp_path):
    _stub_cycle(monkeypatch, tmp_path)
    monkeypatch.setattr(hf_main, "_execute_order_sync", lambda sig, symbol: None)
    result = hf_main.run_once(target_symbol="EURUSD")
    assert result["status"] == "order_failed"
    assert result["executed"] is False


def test_execute_raises_runtimeerror_status_paper_blocked(monkeypatch, tmp_path):
    _stub_cycle(monkeypatch, tmp_path)

    def _blocked(sig, symbol):
        raise RuntimeError("Paper trade blocked — no real price available. Failing closed.")

    monkeypatch.setattr(hf_main, "_execute_order_sync", _blocked)
    result = hf_main.run_once(target_symbol="EURUSD")
    assert result["status"] == "paper_blocked"
    assert result["executed"] is False
