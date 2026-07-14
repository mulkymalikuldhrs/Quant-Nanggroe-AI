"""Tests for /api/brokers per-account MT5 endpoints (no real MT5 needed).

Uses a minimal FastAPI app with only the brokers router mounted, so the
suite doesn't pay the cost of importing the full app (ccxt + 28 routers).
"""
import sys

sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from quant_nanggroe.api.routes.brokers import router
from quant_nanggroe.exchange.manager import ExchangeManager
from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker


def _make_client():
    app = FastAPI()
    app.include_router(router, prefix="/api/brokers")
    em = ExchangeManager()
    em.register("exness_1", PaperExchangeBroker(initial_capital=10000), role="primary")
    em.register("valutrades_1", PaperExchangeBroker(initial_capital=5000), role="failover")
    app.state._services = {"exchange_manager": em}
    return TestClient(app)


def test_list_brokers():
    c = _make_client()
    r = c.get("/api/brokers/")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert {a["name"] for a in body["accounts"]} == {"exness_1", "valutrades_1"}


def test_account_endpoint_offline_ok():
    c = _make_client()
    r = c.get("/api/brokers/exness_1/account")
    # offline MT5 returns 200 with offline flag, not 502
    assert r.status_code == 200
    assert r.json().get("offline") is True


def test_register_account():
    c = _make_client()
    r = c.post("/api/brokers/register", json={
        "name": "exness_2", "login": "999", "password": "x", "server": "Exness-MT5Real2",
    })
    assert r.status_code in (200, 409)


def test_positions_endpoint():
    c = _make_client()
    r = c.get("/api/brokers/valutrades_1/positions")
    assert r.status_code == 200
    assert "positions" in r.json()


def test_unknown_account_404():
    c = _make_client()
    r = c.get("/api/brokers/nonexistent/positions")
    assert r.status_code == 404
