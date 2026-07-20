"""Memory API — stub implementation for UI compatibility."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["Memory"])


@router.get("/search")
async def memory_search(q: str = "", limit: int = 10):
    """Search memories — returns empty results until full implementation."""
    return {"results": [], "query": q, "total": 0}


@router.post("/store")
async def memory_store(data: dict[str, Any] = {}):
    """Store a memory entry."""
    return {"status": "stored", "id": "stub-001"}


@router.get("/entry/{entry_id}")
async def memory_entry(entry_id: str):
    """Get a specific memory entry."""
    return {"id": entry_id, "content": "", "metadata": {}, "created_at": ""}


@router.get("/list")
async def memory_list(limit: int = 50):
    """List all memories."""
    return {"entries": [], "total": 0}
