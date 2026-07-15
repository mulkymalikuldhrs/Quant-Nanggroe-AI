"""Tools API routes — list real agent tool modules + safe execute dispatch.

Lists the actual tool packages in quant_nanggroe.agents.tools (no fake
seed data). Execute returns a graceful result for known tool ids; unknown
ids return an honest error rather than fabricated metrics.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tools"])

# Real tool modules registered in quant_nanggroe/agents/tools/__init__.py
_KNOWN_TOOLS: dict[str, str] = {
    "backtest": "Backtest engine runner",
    "competition_tool": "Competition/tournament analysis",
    "emotional_tool": "Emotional state lockout tool",
    "execution": "Order execution tool",
    "flow_tool": "Order-flow analysis",
    "forecast_tool": "Price forecast tool",
    "geopolitical_tool": "Geopolitical risk tool",
    "intermarket_tool": "Intermarket correlation tool",
    "market_data": "Market data fetch tool",
    "screener_tool": "Asset screener tool",
    "sentiment": "Sentiment analysis tool",
    "skill_tool": "Skill/strategy loader tool",
    "technical": "Technical indicator tool",
}


@router.get("/tools/list")
async def tools_list() -> dict[str, Any]:
    """Return the real registered agent tool set (no mock fallback)."""
    tools = [
        {
            "id": tid,
            "name": tid.replace("_", " ").title(),
            "description": desc,
            "status": "active",
            "category": "agent",
            "executions": 0,
            "lastUsed": None,
        }
        for tid, desc in sorted(_KNOWN_TOOLS.items())
    ]
    return {"tools": tools, "total": len(tools), "source": "agent_toolkit"}


@router.post("/tools/{tool_id}/execute")
async def tools_execute(tool_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Dispatch an execution request to a known tool.

    Returns an honest result envelope. Real execution wiring depends on the
    target tool's callable; this entrypoint validates membership and returns
    a structured response instead of fabricated success metrics.
    """
    if tool_id not in _KNOWN_TOOLS:
        return {"success": False, "tool_id": tool_id, "error": "unknown_tool"}
    params = (payload or {}).get("params", {})
    return {
        "success": True,
        "tool_id": tool_id,
        "executed": False,
        "message": "Tool recognized. Wire concrete callable in agents.tools dispatch.",
        "params_received": bool(params),
        "source": "agent_toolkit",
    }
