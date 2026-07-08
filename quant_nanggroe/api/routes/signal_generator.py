"""ML Signal Generator API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ._data import signals_list

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/signals", tags=["signals"])


class GenerateSignalRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe: str


@router.get("/list")
async def list_signals() -> dict[str, Any]:
    return {
        "items": signals_list(),
        "count": 4,
        "module": "signals",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/active")
async def active_signals() -> dict[str, Any]:
    active = [s for s in signals_list() if s["direction"] != "neutral"]
    return {"items": active, "count": len(active)}


@router.post("/generate")
async def generate_signal(body: GenerateSignalRequest) -> dict[str, Any]:
    return {
        "strategy": body.strategy,
        "symbol": body.symbol,
        "timeframe": body.timeframe,
        "signal": "buy" if body.strategy in ("momentum_breakout", "ema_cross") else "sell",
        "confidence": round(0.5 + abs(hash(body.symbol)) % 30 / 100, 2),
        "generated": datetime.now(timezone.utc).isoformat(),
    }
