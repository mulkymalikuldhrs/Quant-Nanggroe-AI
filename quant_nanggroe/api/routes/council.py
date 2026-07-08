"""Council API routes — multi-agent governance."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/council", tags=["council"])


@router.get("/list")
async def list_sessions() -> dict[str, Any]:
    """Return all council governance sessions."""
    # ponytail: static stub; replace with DB-backed query when council persistence lands.
    return {"sessions": [], "module": "council"}


@router.get("/{id}")
async def get_session(id: str) -> dict[str, Any]:
    """Return a single council session by ID."""
    return {"session": None, "id": id, "module": "council"}


@router.get("/vote/{session_id}")
async def get_vote_results(session_id: str) -> dict[str, Any]:
    """Return voting results for a council session."""
    return {"votes": [], "session_id": session_id, "module": "council"}
