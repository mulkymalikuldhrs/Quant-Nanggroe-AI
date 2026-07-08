"""ML Signal Generator API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/signals", tags=["signals"])


class GenerateSignalRequest(BaseModel):
    """Request schema for generating a new ML signal."""

    strategy: str
    symbol: str
    timeframe: str


@router.get("/list")
async def list_signals() -> dict[str, Any]:
    """Return all generated signals."""
    # ponytail: static stub — wire to signal store when available.
    return {"items": [], "count": 0}


@router.get("/active")
async def active_signals() -> dict[str, Any]:
    """Return currently active signals."""
    # ponytail: static stub — wire to live signal watcher when available.
    return {"items": [], "count": 0}


@router.post("/generate")
async def generate_signal(body: GenerateSignalRequest) -> dict[str, Any]:
    """Generate a new ML signal for the given strategy, symbol and timeframe."""
    # ponytail: stub — wire to ML inference pipeline when available.
    logger.info(
        "generate_signal_request strategy=%s symbol=%s timeframe=%s",
        body.strategy, body.symbol, body.timeframe,
    )
    return {
        "strategy": body.strategy,
        "symbol": body.symbol,
        "timeframe": body.timeframe,
        "signal": None,
        "confidence": 0.0,
    }
