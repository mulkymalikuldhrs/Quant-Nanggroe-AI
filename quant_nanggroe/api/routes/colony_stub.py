"""Colony API — stub implementation for UI compatibility."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/colony", tags=["Colony"])


@router.get("/list")
async def colony_list():
    """List all colonies."""
    return {"colonies": [], "total": 0}


@router.post("/create")
async def colony_create(data: dict[str, Any] = {}):
    """Create a new colony."""
    return {"status": "created", "id": "colony-stub-001"}


@router.get("/{colony_id}")
async def colony_get(colony_id: str):
    """Get colony details."""
    return {"id": colony_id, "name": "", "members": [], "status": "inactive"}


@router.post("/{colony_id}/run")
async def colony_run(colony_id: str):
    """Run a colony cycle."""
    return {"status": "ran", "colony_id": colony_id, "results": []}
