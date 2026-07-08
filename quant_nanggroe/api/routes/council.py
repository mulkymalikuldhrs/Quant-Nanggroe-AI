"""Council API routes — multi-agent governance."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from ._data import council_list

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/council", tags=["council"])


@router.get("/list")
async def list_sessions() -> dict[str, Any]:
    return {
        "sessions": council_list(),
        "module": "council",
        "endpoint": "list",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/{id}")
async def get_session(id: str) -> dict[str, Any]:
    sessions = {s["proposal_id"]: s for s in council_list()}
    return sessions.get(id, {"error": "not_found", "id": id})


@router.get("/vote/{session_id}")
async def get_vote_results(session_id: str) -> dict[str, Any]:
    sessions = {s["proposal_id"]: s for s in council_list()}
    s = sessions.get(session_id)
    if not s:
        return {"votes": [], "session_id": session_id, "error": "not_found"}
    return {
        "session_id": session_id,
        "votes": {
            "for": s["votes_for"],
            "against": s["votes_against"],
            "abstain": s["votes_abstain"],
        },
        "status": s["status"],
    }
