"""FRED economic data API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/series")
async def list_series() -> dict[str, Any]:
    """List available FRED economic indicator series."""
    # ponytail: static stub — wire to FRED API client when available.
    return {"items": [], "count": 0}


@router.get("/series/{series_id}")
async def get_series(series_id: str) -> dict[str, Any]:
    """Return values for a single FRED series by its ID (e.g. GDP, UNRATE)."""
    return {"id": series_id, "items": [], "count": 0}


@router.get("/search")
async def search_series(q: str = Query("", description="Search keyword")) -> dict[str, Any]:
    """Search FRED series by keyword."""
    return {"query": q, "items": [], "count": 0}
