"""Debate API routes — multi-agent debate engine."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ._data import debate_list

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debate", tags=["debate"])


class DebateSession(BaseModel):
    topic: str
    participants: list[str]


@router.get("/list")
async def list_debates() -> dict[str, Any]:
    return {
        "debates": debate_list(),
        "module": "debate",
        "endpoint": "list",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/{debate_id}")
async def get_debate(debate_id: str) -> dict[str, Any]:
    debates = {d["id"]: d for d in debate_list()}
    return debates.get(debate_id, {"error": "not_found", "debate_id": debate_id})


@router.post("/new")
async def create_debate(session: DebateSession) -> dict[str, Any]:
    return {
        "id": f"deb-{datetime.now(timezone.utc).timestamp():.0f}",
        "topic": session.topic,
        "participants": session.participants,
        "status": "created",
        "module": "debate",
    }
