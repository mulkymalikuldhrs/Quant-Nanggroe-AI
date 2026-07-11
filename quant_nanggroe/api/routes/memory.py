"""Memory API routes."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple in-memory key-value store (can be swapped for real vector DB later)
_memory_store: dict[str, Any] = {}

@router.get("/search")
async def search_memory(q: str = "") -> dict[str, Any]:
    """Search memory entries."""
    results = []
    query = q.lower().strip()
    for key, value in _memory_store.items():
        if not query or query in key.lower() or query in str(value).lower():
            results.append({"key": key, "value": value, "matched": True})
    return {"results": results, "count": len(results)}

@router.post("/store")
async def store_memory(data: dict[str, Any]) -> dict[str, Any]:
    """Store a memory entry."""
    key = data.get("key", str(datetime.now().timestamp()))
    value = data.get("value", "")
    _memory_store[key] = value
    return {"status": "stored", "key": key}
