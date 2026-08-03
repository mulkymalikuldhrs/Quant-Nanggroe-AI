"""Tests: hedge fund _pipeline_execute() reports honest execution status.

execute() outcomes must map to:
  - order id returned      → status "executed",     executed True
  - None returned          → status "order_failed", executed False
  - RuntimeError raised    → status "paper_blocked", executed False
"""

from __future__ import annotations

from quant_nanggroe.hedge_fund.portfolio import main as hf_main


def test_execute_returns_order_id_status_executed(monkeypatch):
    """When _execute_order_sync returns an order id, status must be 'executed'."""
    monkeypatch.setattr(hf_main, "_execute_order_sync", lambda signal, symbol: "order-123")
    result = {"_signal": {"bias": "buy", "confidence": 0.8, "price": 1.1, "sl": 1.09}, "symbol": "EURUSD"}
    out = hf_main._pipeline_execute(result)
    assert out["status"] == "executed"
    assert out["executed"] is True
    assert out["order_id"] == "order-123"


def test_execute_returns_none_status_order_failed(monkeypatch):
    """When _execute_order_sync returns None, status must be 'order_failed'."""
    monkeypatch.setattr(hf_main, "_execute_order_sync", lambda signal, symbol: None)
    result = {"_signal": {"bias": "buy", "confidence": 0.8, "price": 1.1, "sl": 1.09}, "symbol": "EURUSD"}
    out = hf_main._pipeline_execute(result)
    assert out["status"] == "order_failed"
    assert out["executed"] is False


def test_execute_raises_runtimeerror_status_paper_blocked(monkeypatch):
    """When _execute_order_sync raises RuntimeError, status must be 'paper_blocked'."""

    def _blocked(signal, symbol):
        raise RuntimeError("Paper trade blocked — no real price available. Failing closed.")

    monkeypatch.setattr(hf_main, "_execute_order_sync", _blocked)
    result = {"_signal": {"bias": "buy", "confidence": 0.8, "price": 1.1, "sl": 1.09}, "symbol": "EURUSD"}
    out = hf_main._pipeline_execute(result)
    assert out["status"] == "paper_blocked"
    assert out["executed"] is False
