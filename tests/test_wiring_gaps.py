"""Tests for W-gap wiring: alerting->kill switch, quality->fallback, features API."""

import pandas as pd
import pytest


# ---- W-gap-1: alerting wired into graph kill switch (fail-soft) ----
def test_graph_imports_with_alerting_wired():
    import os
    graph_file = os.path.join(
        os.path.dirname(__file__), "..", "quant_nanggroe", "agents", "graph.py"
    )
    src = open(graph_file, encoding="utf-8").read()
    # _alert_manager must be imported + used at the kill-switch / emergency exit
    assert "_alert_manager" in src
    assert "_alert_manager.critical" in src
    assert "EMERGENCY EXIT activated" in src


# ---- W-gap-2: quality wired into fallback_chain.fetch (fail-soft) ----
def test_fallback_chain_quality_gate_present():
    import os
    fc_file = os.path.join(
        os.path.dirname(__file__), "..", "quant_nanggroe", "engine", "data",
        "fallback_chain.py",
    )
    src = open(fc_file, encoding="utf-8").read()
    assert "W-gap-2" in src
    assert "_assess_quality" in src


# ---- W-gap-3: features API route registered ----
def test_features_route_registered():
    import quant_nanggroe.api.app as app_mod
    src = open(app_mod.__file__, encoding="utf-8").read()
    assert "features.router" in src
    assert "/api/features" in src


def test_features_endpoint_computes():
    """Spin up TestClient and POST OHLCV -> features (JWT with app's real secret)."""
    try:
        from fastapi.testclient import TestClient
    except Exception:
        pytest.skip("fastapi testclient unavailable")
    from contextlib import asynccontextmanager
    from quant_nanggroe.security.auth import JWTAuth, UserRole
    from quant_nanggroe.config import settings
    import quant_nanggroe.api.app as app_mod
    app = app_mod.create_app()

    @asynccontextmanager
    async def _ctx(a):
        yield
    app.router.lifespan_context = _ctx
    from quant_nanggroe.config import get_settings
    jwt = JWTAuth(secret_key=get_settings().jwt_secret)
    token = jwt.create_token("pytest", UserRole.ADMIN)
    client = TestClient(app, headers={"Authorization": f"Bearer {token}"}, raise_server_exceptions=False)
    rng = __import__("numpy").random.default_rng(3)
    close = 100 + rng.normal(0, 1, 40).cumsum()
    rows = [
        {"open": float(close[i]), "high": float(close[i] + 0.5),
         "low": float(close[i] - 0.5), "close": float(close[i]), "volume": 1000.0}
        for i in range(40)
    ]
    resp = client.post("/api/features", json={"symbol": "TEST", "ohlcv": rows})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "rsi_14" in body["features"]
    assert body["rows"] == 40
