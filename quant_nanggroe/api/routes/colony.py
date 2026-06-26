"""Colony/Agent management routes — wraps ai_multicolony."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

HAS_COLONY = False
try:
    from ai_multicolony import (
        Colony, ColonyManager, AgentRegistry, SharedAgentState,
        ManusAgent, PlannerAgent, ExecutorAgent, CoderAgent,
        BrowserAgent, VoiceAgent, SecurityAgent, ResearcherAgent,
        ColonyAgent, BaseAgent,
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
