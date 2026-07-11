"""Strategy registry API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/registry")
async def strategy_registry() -> dict[str, Any]:
    """Return registered strategies."""
    # ponytail: wire to backend loader once strategy registry parsing is active.
    return {
        "strategies": [
            {"id": "regimebased", "name": "RegimeBased", "status": "active", "sharpe": 1.8},
            {"id": "meanrev", "name": "MeanReversion", "status": "unknown", "sharpe": 1.2},
            {"id": "trend", "name": "TrendFollow", "status": "unknown", "sharpe": 1.5},
        ]
    }
