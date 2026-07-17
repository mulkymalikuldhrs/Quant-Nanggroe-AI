from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/geopolitics", tags=["geopolitics"])


@router.get("/list")
async def list_events() -> dict[str, Any]:
    # ponytail: no live geopolitical feed exists in the engine — reference data
    # lives at /api/data (e.g. /api/data/events), labeled synthetic_reference.
    raise HTTPException(
        status_code=501,
        detail="No live geopolitical data provider is configured. "
        "Synthetic reference datasets are available at /api/data/events, "
        "/api/data/sanctions, /api/data/regions.",
    )


@router.get("/sanctions")
async def list_sanctions() -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail="No live sanctions feed is configured. "
        "Synthetic reference data is available at /api/data/sanctions.",
    )


@router.get("/regions")
async def regional_risk() -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail="No live regional-risk feed is configured. "
        "Synthetic reference data is available at /api/data/regions.",
    )
