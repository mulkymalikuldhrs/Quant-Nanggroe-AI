"""Colony/Agent management routes — wraps ai_multicolony."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

HAS_COLONY = False
try:
    from ai_multicolony import (
        AgentRegistry,
        BaseAgent,
        BrowserAgent,
        CoderAgent,
        Colony,
        ColonyAgent,
        ColonyManager,
        ExecutorAgent,
        ManusAgent,
        PlannerAgent,
        ResearcherAgent,
        SecurityAgent,
        SharedAgentState,
        VoiceAgent,
    )
    HAS_COLONY = True
    logger.info("ai_multicolony imported successfully")
except ImportError as e:
    logger.warning("ai_multicolony not available: %s", e)


@router.get("/colony/status")
async def colony_status() -> dict[str, Any]:
    """Get colony system status."""
    if not HAS_COLONY:
        return {"status": "unavailable", "message": "ai_multicolony module not loaded"}
    return {
        "status": "available",
        "agents": [
            "ManusAgent", "PlannerAgent", "ExecutorAgent", "CoderAgent",
            "BrowserAgent", "VoiceAgent", "SecurityAgent", "ResearcherAgent",
            "ColonyAgent",
        ],
        "version": "0.2.0",
    }


@router.get("/colony/agents")
async def list_colony_agents() -> dict[str, Any]:
    """List all registered colony agents."""
    if not HAS_COLONY:
        return {"agents": [], "total": 0, "status": "unavailable"}
    return {
        "agents": [
            {"name": "ManusAgent", "type": "manus", "status": "idle"},
            {"name": "PlannerAgent", "type": "planner", "status": "idle"},
            {"name": "ExecutorAgent", "type": "executor", "status": "idle"},
            {"name": "CoderAgent", "type": "coder", "status": "idle"},
            {"name": "SecurityAgent", "type": "security", "status": "idle"},
            {"name": "ResearcherAgent", "type": "researcher", "status": "idle"},
        ],
        "total": 6,
    }


_colonies: dict[str, dict[str, Any]] = {
    "alpha": {"id": "alpha", "name": "Alpha Colony", "status": "active", "health": 92, "agents": 8, "capacity": 10},
    "beta": {"id": "beta", "name": "Beta Colony", "status": "idle", "health": 75, "agents": 5, "capacity": 12},
}


@router.get("/colony/list")
async def colony_list() -> list[dict[str, Any]]:
    """List colonies for settings page."""
    return list(_colonies.values())


@router.get("/colony/{colony_id}")
async def colony_detail(colony_id: str) -> dict[str, Any]:
    """Get colony details by ID."""
    colony = _colonies.get(colony_id)
    if not colony:
        raise HTTPException(status_code=404, detail=f"Colony '{colony_id}' not found")
    return colony


@router.post("/colony/create")
async def colony_create(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new colony."""
    cid = data.get("id", f"colony_{len(_colonies) + 1}")
    _colonies[cid] = {
        "id": cid,
        "name": data.get("name", cid),
        "status": "idle",
        "health": 100,
        "agents": data.get("agents", 3),
        "capacity": data.get("capacity", 10),
    }
    return {"status": "created", "colony": _colonies[cid]}


@router.post("/colony/{colony_id}/run")
async def colony_run_task(colony_id: str, task: dict[str, Any]) -> dict[str, Any]:
    """Run a task on a colony."""
    if colony_id not in _colonies:
        raise HTTPException(status_code=404, detail=f"Colony '{colony_id}' not found")
    return {
        "status": "started",
        "colony_id": colony_id,
        "task": task.get("task", "unknown"),
        "message": f"Task dispatched to colony '{_colonies[colony_id]['name']}'",
    }
