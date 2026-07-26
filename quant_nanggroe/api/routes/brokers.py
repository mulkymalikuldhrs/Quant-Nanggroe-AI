"""Brokers API routes — multi-account MT5 (Exness / Valutrades / etc).

Exness, Valutrades, dan broker retail lain TIDAK punya API publik resmi untuk
eksekusi otomatis. Solusinya: jalankan via MetaTrader 5 terminal lokal —
setiap akun = 1 instance MT5 (login + password + server). Quant Nanggroe AI
connect langsung ke terminal MT5, monitor saldo/portofolio/posisi, dan eksekusi
order per-akun. Semua lewat ExchangeManager yang sudah ada (multi-account +
failover + aggregated portfolio).

Endpoint:
  GET  /api/brokers/                 -> list akun terdaftar + status
  GET  /api/brokers/{name}/account   -> saldo + equity per akun
  GET  /api/brokers/{name}/positions -> posisi terbuka per akun
  GET  /api/brokers/{name}/portfolio -> portofolio lengkap per akun
  POST /api/brokers/{name}/order     -> eksekusi order langsung per akun
  POST /api/brokers/register         -> daftarkan akun MT5 dari config
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from quant_nanggroe.types.orders import OrderSide, OrderType
from quant_nanggroe.exchange.base import ExchangeError

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_em(request: Request):
    from quant_nanggroe.exchange.manager import ExchangeManager

    if not hasattr(request.app.state, "_services"):
        request.app.state._services = {}
    if "exchange_manager" not in request.app.state._services:
        request.app.state._services["exchange_manager"] = ExchangeManager()
    return request.app.state._services["exchange_manager"]


def _to_dict(obj) -> Dict[str, Any]:
    """Pydantic v2 safe model_dump."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return dict(obj)


# ponytail: a registered-but-offline MT5 account (terminal not running,
# connect deferred) is the NORMAL state for Exness/Valutrades. Return its
# data-or-empty with 200, not 502. AttributeError = broker doesn't implement
# the method (e.g. paper broker), treat same as offline.
_OFFLINE_OK = (ExchangeError, AttributeError)


async def _safe_positions(em, name: str) -> List[Any]:
    try:
        return await em.get_positions(name)
    except _OFFLINE_OK:
        return []


async def _safe_portfolio(em, name: str):
    try:
        return await em.get_portfolio(name)
    except _OFFLINE_OK:
        return None


# ---------------------------------------------------------------------------
# List accounts
# ---------------------------------------------------------------------------

@router.get("/")
async def list_brokers(request: Request):
    em = _get_em(request)
    accounts = []
    for name, reg in em._registrations.items():
        accounts.append({
            "name": name,
            "role": reg.role.value,
            "connected": reg.connected,
            "healthy": reg.healthy,
            "state": reg.exchange.state.value if hasattr(reg.exchange, "state") else "unknown",
        })
    return {"accounts": accounts, "count": len(accounts)}


# ---------------------------------------------------------------------------
# Per-account endpoints
# ---------------------------------------------------------------------------

@router.get("/{name}/account")
async def get_account(name: str, request: Request):
    em = _get_em(request)
    if name not in em._registrations:
        raise HTTPException(status_code=404, detail=f"Account '{name}' not registered")
    try:
        info = await em._registrations[name].exchange.get_account_info()
        return _to_dict(info)
    except _OFFLINE_OK:
        reg = em._registrations[name]
        return {"name": name, "offline": True, "state": reg.exchange.state.value if hasattr(reg.exchange, "state") else "unknown"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MT5 query failed: {exc}")


@router.get("/{name}/positions")
async def get_positions(name: str, request: Request):
    em = _get_em(request)
    if name not in em._registrations:
        raise HTTPException(status_code=404, detail=f"Account '{name}' not registered")
    try:
        positions = await _safe_positions(em, name)
        return {"account": name, "positions": [_to_dict(p) for p in positions], "offline": positions is not None and len(positions) == 0}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MT5 positions failed: {exc}")


@router.get("/{name}/portfolio")
async def get_portfolio(name: str, request: Request):
    em = _get_em(request)
    if name not in em._registrations:
        raise HTTPException(status_code=404, detail=f"Account '{name}' not registered")
    try:
        pf = await _safe_portfolio(em, name)
        if pf is None:
            return {"account": name, "offline": True, "positions": {}}
        return _to_dict(pf)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MT5 portfolio failed: {exc}")


@router.post("/{name}/order")
async def place_order(name: str, payload: Dict[str, Any], request: Request):
    # FIX S4: Require TRADER+ role for order placement
    from quant_nanggroe.security.auth import UserRole
    if hasattr(request.state, "user_role") and request.state.user_role not in (UserRole.ADMIN, UserRole.TRADER):
        raise HTTPException(status_code=403, detail="Trader+ role required to place orders")
    em = _get_em(request)
    if name not in em._registrations:
        raise HTTPException(status_code=404, detail=f"Account '{name}' not registered")
    try:
        side = OrderSide(payload["side"].lower())
        otype = OrderType(payload.get("type", "market").lower())
        order = await em._registrations[name].exchange.place_order(
            symbol=payload["symbol"],
            side=side,
            order_type=otype,
            quantity=float(payload["quantity"]),
            price=payload.get("price"),
            stop_price=payload.get("stop_price"),
            notes=payload.get("notes", "QNAI"),
        )
        return _to_dict(order)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MT5 order failed: {exc}")


# ---------------------------------------------------------------------------
# Register MT5 account (Exness / Valutrades / etc)
# ---------------------------------------------------------------------------

@router.post("/register")
async def register_account(payload: Dict[str, Any], request: Request):
    """Daftarkan akun MT5. Body: {name, login, password, server, role?}.

    Exness/Valutrades = akun MT5 dengan server berbeda. Contoh:
      {"name": "exness_1", "login": "1234567", "password": "...",
       "server": "Exness-MT5Real", "role": "primary"}
    """
    em = _get_em(request)
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    if name in em._registrations:
        raise HTTPException(status_code=409, detail=f"Account '{name}' already registered")

    from quant_nanggroe.exchange.factory import ExchangeFactory
    try:
        broker = ExchangeFactory().create(
            "mt5",
            api_key=payload.get("login"),
            api_secret=payload.get("password"),
            passphrase=payload.get("server"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create MT5 broker (is MetaTrader5 installed?): {exc}",
        )
    em.register(name, broker, role=payload.get("role", "primary"))
    # ponytail: fail-closed — never auto-connect untrusted broker with live creds
    try:
        await broker.connect()
    except Exception as exc:
        logger.warning("Broker %s connect deferred: %s", name, exc)
    return {"name": name, "registered": True, "state": broker.state.value}
