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

@router.delete("/entry/{entry_id:path}")
async def delete_memory(entry_id: str) -> dict[str, Any]:
    """Delete a memory entry by key or ID."""
    if entry_id in _memory_store:
        del _memory_store[entry_id]
        return {"status": "deleted", "key": entry_id}
    # Try matching by key prefix
    matched = [k for k in _memory_store.keys() if entry_id in k]
    for k in matched:
        del _memory_store[k]
    return {"status": "deleted" if matched else "not_found", "matched": len(matched)}
