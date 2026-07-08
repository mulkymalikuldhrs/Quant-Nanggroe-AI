from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from ._data import geopolitics_events, geopolitics_regions, geopolitics_sanctions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/geopolitics", tags=["geopolitics"])


@router.get("/list")
async def list_events() -> dict[str, Any]:
    return {
        "events": geopolitics_events(),
        "module": "geopolitics",
        "endpoint": "list",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/sanctions")
async def list_sanctions() -> dict[str, Any]:
    return {
        "sanctions": geopolitics_sanctions(),
        "module": "geopolitics",
        "endpoint": "sanctions",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/regions")
async def regional_risk() -> dict[str, Any]:
    return {
        "regions": geopolitics_regions(),
        "module": "geopolitics",
        "endpoint": "regions",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }
