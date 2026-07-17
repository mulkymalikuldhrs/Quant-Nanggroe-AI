"""Verification for stub-route fixes: /api/data wiring, options real pricing,
RL real training step, geopolitics honest 501.

Run: pytest tests/test_stub_routes_fix.py -q
"""
from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from quant_nanggroe.api.app import create_app


API_KEY = "dev-local-key-123"


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app, headers={"Authorization": f"ApiKey {API_KEY}"})


def test_api_data_wired_and_lists(client):
    r = client.get("/api/data")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "synthetic_reference"
    for name in ("events", "sanctions", "regions", "options_positions"):
        assert name in body["datasets"]


def test_api_data_dataset_returns_items(client):
    r = client.get("/api/data/regions")
    assert r.status_code == 200
    assert r.json()["status"] == "synthetic_reference"
    assert len(r.json()["items"]) >= 1


def test_api_data_unknown_is_404(client):
    assert client.get("/api/data/nope").status_code == 404


def test_geopolitics_is_honest_501(client):
    for path in ("/api/geopolitics/list", "/api/geopolitics/sanctions",
                 "/api/geopolitics/regions"):
        r = client.get(path)
        assert r.status_code == 501, path
        assert "synthetic" not in r.json().get("status", "")


def test_options_analyze_real_pricing(client):
    r = client.post(
        "/api/options/analyze",
        json={"symbol": "AAPL", "type": "call", "strike": 200,
              "expiry": "2026-12-31", "spot": 210, "volatility": 0.3},
    )
    assert r.status_code == 200
    a = r.json()["analysis"]
    assert "theoretical_price" in a and a["theoretical_price"] > 0
    # put-call parity sanity via engine directly
    from quant_nanggroe.engine.options.analyzer import OptionsAnalyzer
    bs = OptionsAnalyzer().analyze(S=210, K=200, T=1.0, r=0.05, sigma=0.3)
    parity = bs["call_price"] - bs["put_price"]
    assert abs(parity - (210 - 200 * np.exp(-0.05))) < 1e-6


def test_options_analyze_rejects_bad_type(client):
    r = client.post(
        "/api/options/analyze",
        json={"symbol": "AAPL", "type": "nope", "strike": 200,
              "expiry": "2026-12-31", "spot": 210},
    )
    assert r.status_code == 400


def test_rl_train_real_loss(client):
    r = client.post("/api/rl/train", json={"agent_type": "ppo", "episodes": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["avg_loss"] is not None
    assert body["avg_loss"] != 0.0


def test_rl_inference_wiring(client):
    # sanity that the create_agent(name=...) fix didn't break inference
    r = client.post("/api/rl/inference", json={"symbol": "BTCUSDT", "agent_type": "ppo"})
    assert r.status_code == 200
    assert r.json()["action_label"] in ("hold", "buy", "sell")
