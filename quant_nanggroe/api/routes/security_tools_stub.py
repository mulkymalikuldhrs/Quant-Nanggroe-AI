"""Security & Tools API — stub implementation for UI compatibility."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Security"])


@router.get("/security/events")
async def security_events(limit: int = 50):
    """List security events."""
    return {"events": [], "total": 0}


@router.get("/tools/list")
async def tools_list():
    """List available tools."""
    return {"tools": [], "total": 0}


@router.post("/tools/{tool_id}/execute")
async def tools_execute(tool_id: str, data: dict[str, Any] = {}):
    """Execute a tool."""
    return {"status": "executed", "tool_id": tool_id, "result": None}


@router.get("/monitor/system")
async def monitor_system():
    """System health monitor."""
    return {"cpu": 0, "memory": 0, "disk": 0, "status": "ok"}


@router.get("/monitor/agents")
async def monitor_agents():
    """Agent status monitor."""
    return {"agents": [], "total": 0}


@router.get("/signals/list")
async def signals_list():
    """List recent signals."""
    return {"signals": [], "total": 0}
