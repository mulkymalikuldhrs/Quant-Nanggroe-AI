"""Geopolitical risk API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/geopolitics", tags=["geopolitics"])


@router.get("/list")
async def list_events() -> dict[str, Any]:
    """Return geopolitical events / risks."""
    return {
        "events": [],
        "module": "geopolitics",
        "endpoint": "list",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sanctions")
async def list_sanctions() -> dict[str, Any]:
    """Return sanctions data."""
    return {
        "sanctions": [],
        "module": "geopolitics",
        "endpoint": "sanctions",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/regions")
async def regional_risk() -> dict[str, Any]:
    """Return regional risk assessments."""
    return {
        "regions": [],
        "module": "geopolitics",
        "endpoint": "regions",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
