"""Debate API routes — multi-agent debate engine."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debate", tags=["debate"])


class DebateSession(BaseModel):
    topic: str
    participants: list[str]


@router.get("/list")
async def list_debates() -> dict[str, Any]:
    """Return all debate sessions."""
    return {"debates": [], "module": "debate"}


@router.get("/{debate_id}")
async def get_debate(debate_id: str) -> dict[str, Any]:
    """Return a single debate session by ID."""
    return {"debate_id": debate_id, "module": "debate"}


@router.post("/new")
async def create_debate(session: DebateSession) -> dict[str, Any]:
    """Create a new debate session."""
    return {
        "topic": session.topic,
        "participants": session.participants,
        "module": "debate",
    }
