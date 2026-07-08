"""FRED economic data API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

from ._data import fred_series

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/series")
async def list_series() -> dict[str, Any]:
    return {
        "items": fred_series(),
        "count": 5,
        "module": "fred",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/series/{series_id}")
async def get_series(series_id: str) -> dict[str, Any]:
    series = {s["id"].lower(): s for s in fred_series()}
    return series.get(series_id.lower(), {"error": "not_found", "id": series_id})


@router.get("/search")
async def search_series(q: str = Query("", description="Search keyword")) -> dict[str, Any]:
    results = [s for s in fred_series() if q.lower() in s["title"].lower()] if q else []
    return {"query": q, "items": results, "count": len(results)}
