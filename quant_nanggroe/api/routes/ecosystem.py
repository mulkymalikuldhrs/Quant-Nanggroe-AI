"""Ecosystem API routes — dashboard frontend integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status")
async def ecosystem_status() -> dict[str, Any]:
    """Overall ecosystem status."""
    return {
        "status": "online",
        "modules": {
            "quant_nanggroe": "running",
            "hermes_quant": "archived",
            "autonomous_organism": "archived",
        },
        "version": "0.2.0",
        "timestamp": datetime.now().isoformat(),
    }

@router.get("/overview")
async def ecosystem_overview() -> dict[str, Any]:
    """Combined ecosystem overview."""
    return {
        "trading": {"active": True, "mode": "paper"},
        "agents": {"total": 9, "active": 4},
        "risk": {"status": "OK"},
        "backtest": {"running": 0, "completed": 0},
    }
