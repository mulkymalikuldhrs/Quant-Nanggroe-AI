"""Channels API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list")
async def list_channels() -> dict[str, Any]:
    """Return configured communication channels."""
    # ponytail: static config likely owned by Telegram/Comms; return stub when wired to real configs.
    return {
        "channels": [
            {"name": "Telegram", "status": "unknown", "kind": "messaging"},
            {"name": "Discord", "status": "unknown", "kind": "messaging"},
            {"name": "Slack", "status": "unknown", "kind": "messaging"},
        ]
    }
