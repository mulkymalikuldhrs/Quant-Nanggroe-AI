"""Credentials API — read/write all configurable credentials via UI."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/credentials", tags=["Credentials"])


def _cred_path() -> Path:
    """Path to credentials.json — next to the config dir."""
    base = Path(os.environ.get("QNAI_STATE_DIR", Path(__file__).resolve().parent.parent.parent.parent))
    return base / "config" / "credentials.json"


def _load() -> dict[str, Any]:
    p = _cred_path()
    if not p.exists():
        return _defaults()
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("credentials_load_fallback: %s", e)
        return _defaults()


def _save(data: dict[str, Any]) -> None:
    p = _cred_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, default=str))


def _defaults() -> dict[str, Any]:
    return {
        "apiKeys": [],
        "brokers": [],
        "exchanges": [],
        "riskLimits": {
            "maxPositionSize": 10,
            "maxSectorExposure": 40,
            "maxVaR": 10000,
            "maxDrawdown": 5,
            "maxLeverage": 2.0,
            "defaultStopLoss": 2,
            "defaultTakeProfit": 5,
        },
        "systemToggles": {
            "liveTrading": False,
            "autoRebalance": False,
            "killSwitchOnLoss": True,
            "emotionalLockout": True,
            "riskChecksRequired": True,
            "paperTradingMode": True,
        },
        "llmKeys": [],
    }


@router.get("")
def get_credentials() -> dict[str, Any]:
    return _load()


@router.put("")
def update_credentials(body: dict[str, Any]) -> dict[str, Any]:
    current = _load()
    # merge: keep keys not present in body, override present ones
    current.update(body)
    _save(current)
    logger.info("credentials_updated: %d top-level keys", len(body))
    return {"status": "saved", "keys": list(body.keys())}


@router.post("/test/{kind}/{cred_id}")
def test_connection(kind: str, cred_id: str) -> dict[str, Any]:
    """Lightweight connectivity test: pings a well-known endpoint."""
    import socket

    creds = _load()
    items = creds.get(kind, []) if kind in ("apiKeys", "brokers", "exchanges", "llmKeys") else []
    item = next((c for c in items if c.get("id") == cred_id), None)
    if not item:
        raise HTTPException(404, f"{kind}/{cred_id} not found")

    # ponytail: socket-based ping, full exchange handshake when MT5 bridge is wired
    host = item.get("server", item.get("host", ""))
    host = host.split(":")[0] if host else "api." + item.get("name", "example.com").lower().replace(" ", "")
    try:
        socket.setdefaulttimeout(5)
        socket.gethostbyname(host)
        return {"status": "ok", "message": f"DNS resolved: {host}", "cred_id": cred_id}
    except Exception as e:
        return {"status": "error", "message": str(e), "cred_id": cred_id}
