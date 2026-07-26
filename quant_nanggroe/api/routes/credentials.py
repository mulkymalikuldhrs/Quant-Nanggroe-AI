"""Credentials API — read/write all configurable credentials via UI."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/credentials", tags=["Credentials"])


# ponytail: env mapping for the most common credential types.
# Add when a new provider appears.
_PROVIDER_ENV_MAP = {
    "openai": "QNAI_OPENAI_API_KEY",
    "anthropic": "QNAI_ANTHROPIC_API_KEY",
    "google": "QNAI_GOOGLE_API_KEY",
    "groq": "QNAI_GROQ_API_KEY",
    "nvidia": "QNAI_NVIDIA_API_KEY",
    "cohere": "QNAI_COHERE_API_KEY",
    "mistral": "QNAI_MISTRAL_API_KEY",
}


def bootstrap_env(creds: dict[str, Any] | None = None) -> int:
    """Load credentials from *creds* (or credentials.json) into os.environ.

    Returns number of env vars set. Idempotent — existing env vars are
    NOT overwritten unless they are empty.
    """
    if creds is None:
        try:
            creds = _load()
        except Exception:
            return 0
    count = 0
    # API keys
    api_keys = creds.get("apiKeys", [])
    if api_keys and api_keys[0].get("key"):
        key = api_keys[0]["key"]
        if not os.environ.get("QNAI_API_KEY"):
            os.environ["QNAI_API_KEY"] = key
            count += 1
    # LLM keys → QNAI_{PROVIDER}_API_KEY
    for k in creds.get("llmKeys", []):
        prov = (k.get("provider") or "").lower().strip()
        env = _PROVIDER_ENV_MAP.get(prov)
        if env and k.get("key") and not os.environ.get(env):
            os.environ[env] = k["key"]
            count += 1
    # Brokers → MT5_LOGIN_*/PASS_*/SERVER_*
    for b in creds.get("brokers", []):
        name = (b.get("name") or "").upper().replace(" ", "_")
        if not name:
            continue
        for field, prefix in [("login", "MT5_LOGIN_"), ("password", "MT5_PASS_"), ("server", "MT5_SERVER_")]:
            val = b.get(field)
            env = prefix + name
            if val and not os.environ.get(env):
                os.environ[env] = str(val)
                count += 1
    return count


# ── I/O ──────────────────────────────────────────────────────────────────────


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
def get_credentials(request: Request) -> dict[str, Any]:
    # FIX S3: Require ADMIN role for credential access
    from quant_nanggroe.security.auth import UserRole
    if hasattr(request.state, "user_role") and request.state.user_role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return _load()


@router.put("")
def update_credentials(body: dict[str, Any], request: Request) -> dict[str, Any]:
    # FIX S3: Require ADMIN role for credential modification
    from quant_nanggroe.security.auth import UserRole
    if hasattr(request.state, "user_role") and request.state.user_role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
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


@router.post("/apply")
def apply_credentials() -> dict[str, Any]:
    """Apply current credentials.json to os.environ.
    
    Call this after editing via UI so the system picks up new keys without
    a full restart. Idempotent — existing env vars are not overwritten.
    """
    count = bootstrap_env()
    return {"status": "applied", "env_vars_set": count}
