"""
Agent Control Routes — Full agent pipeline & kill switch
=========================================================
Uses shared singletons from app.state so that kill switch
activation and risk state persist across requests.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Request

from quant_nanggroe_ai.api.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentStatusResponse,
    KillSwitchActivateRequest,
    KillSwitchResetRequest,
    KillSwitchStatusResponse,
)
from quant_nanggroe_ai.services import get_kill_switch

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory tracking of active agent runs
_active_runs: dict[str, dict[str, Any]] = {}


# ══════════════════════════════════════════════════════════════════════
# Agent Pipeline
# ══════════════════════════════════════════════════════════════════════

@router.post("/run", response_model=AgentRunResponse)
async def run_agent(request: Request, body: AgentRunRequest) -> AgentRunResponse:
    """
    Run the full agent pipeline for a symbol.

    Triggers the LangGraph trading graph:
    Researcher → Analyst → Strategist → Risk Manager → Trader → Portfolio Manager

    The graph respects kill switch state and will abort if trading is halted.
    """
    ks = get_kill_switch(request.app)

    # Check kill switch before allowing agent run
    if ks.is_active:
        logger.warning("agent_run_blocked", reason="kill_switch_active", symbol=body.symbol)
        return AgentRunResponse(
            status="BLOCKED",
            symbol=body.symbol,
            query=body.query,
            risk_verdict="KILL_SWITCH_ACTIVE",
            error="Kill switch is active — all trading halted",
        )

    run_id = str(uuid.uuid4())[:8]
    _active_runs[run_id] = {
        "id": run_id,
        "symbol": body.symbol,
        "query": body.query,
        "timeframe": body.timeframe,
        "status": "RUNNING",
        "started_at": datetime.now().isoformat(),
    }

    try:
        from quant_nanggroe_ai.agents.graph import get_trading_graph
        from quant_nanggroe_ai.agents.state import AgentState

        graph = get_trading_graph()

        initial_state = AgentState(
            symbol=body.symbol,
            query=body.query,
            timeframe=body.timeframe,
        )

        # Run the graph (may be sync or async depending on LangGraph version)
        result = await asyncio.to_thread(graph.invoke, initial_state.model_dump())
        result_state = AgentState(**result) if isinstance(result, dict) else result

        _active_runs[run_id]["status"] = "COMPLETED"
        _active_runs[run_id]["completed_at"] = datetime.now().isoformat()

        logger.info(
            "agent_run_completed",
            run_id=run_id,
            symbol=body.symbol,
            decision=result_state.decision_action.value,
            risk_verdict=result_state.risk_verdict,
        )

        return AgentRunResponse(
            status="COMPLETED",
            symbol=body.symbol,
            query=body.query,
            agent_trace=result_state.agent_trace,
            decision_action=result_state.decision_action.value,
            risk_verdict=result_state.risk_verdict,
            strategy_signal=result_state.strategy_signal,
        )

    except Exception as exc:
        _active_runs[run_id]["status"] = "FAILED"
        _active_runs[run_id]["error"] = str(exc)
        logger.error("agent_run_failed", run_id=run_id, symbol=body.symbol, error=str(exc))

        return AgentRunResponse(
            status="FAILED",
            symbol=body.symbol,
            query=body.query,
            error=str(exc),
        )


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status(request: Request) -> AgentStatusResponse:
    """
    Get current agent status.

    Returns active agent runs and kill switch state.
    """
    ks = get_kill_switch(request.app)

    active_agents = [
        {
            "id": run["id"],
            "symbol": run["symbol"],
            "status": run["status"],
            "started_at": run["started_at"],
        }
        for run in _active_runs.values()
        if run["status"] == "RUNNING"
    ]

    return AgentStatusResponse(
        agents=active_agents,
        active=len(active_agents) > 0,
        kill_switch_active=ks.is_active,
    )


@router.get("/history")
async def get_agent_history(limit: int = 20):
    """
    Get recent agent run history.

    Args:
        limit: Maximum number of entries to return (default 20).

    Returns:
        List of recent agent runs with status.
    """
    runs = sorted(
        _active_runs.values(),
        key=lambda r: r.get("started_at", ""),
        reverse=True,
    )[:limit]

    return {
        "runs": runs,
        "total_count": len(_active_runs),
        "limit": limit,
    }


# ══════════════════════════════════════════════════════════════════════
# Kill Switch
# ══════════════════════════════════════════════════════════════════════

@router.post("/kill-switch/activate", response_model=KillSwitchStatusResponse)
async def activate_kill_switch(request: Request, body: KillSwitchActivateRequest) -> KillSwitchStatusResponse:
    """
    Activate the kill switch — halts ALL trading.

    This is an emergency action. Once activated, no trades can be placed
    until an explicit manual reset with confirmation phrase.
    """
    ks = get_kill_switch(request.app)
    result = ks.activate(reason=body.reason)

    logger.critical(
        "kill_switch_activated",
        reason=body.reason,
        activated_at=result.get("activated_at"),
    )

    status = ks.status()
    return KillSwitchStatusResponse(
        is_active=status["is_active"],
        activated_at=status["activated_at"],
        activation_reason=status["activation_reason"],
        auto_triggers=status["auto_triggers"],
        manual_triggers=status["manual_triggers"],
        total_resets=status["total_resets"],
        message=status["message"],
    )


@router.post("/kill-switch/reset", response_model=KillSwitchStatusResponse)
async def reset_kill_switch(request: Request, body: KillSwitchResetRequest) -> KillSwitchStatusResponse:
    """
    Reset the kill switch (requires explicit confirmation).

    The confirmation phrase is deliberately long and explicit to prevent
    accidental resets: "CONFIRM_RESET_AFTER_REVIEW"
    """
    ks = get_kill_switch(request.app)
    result = ks.reset(confirmation=body.confirmation)

    logger.warning(
        "kill_switch_reset_attempt",
        success=result["status"] == "RESET",
        status=result["status"],
    )

    status = ks.status()
    return KillSwitchStatusResponse(
        is_active=status["is_active"],
        activated_at=status["activated_at"],
        activation_reason=status["activation_reason"],
        auto_triggers=status["auto_triggers"],
        manual_triggers=status["manual_triggers"],
        total_resets=status["total_resets"],
        message=result.get("message", status["message"]),
    )


@router.get("/kill-switch/status", response_model=KillSwitchStatusResponse)
async def kill_switch_status(request: Request) -> KillSwitchStatusResponse:
    """
    Get kill switch status.

    Returns the current activation state, trigger counts, and reset history.
    """
    ks = get_kill_switch(request.app)
    status = ks.status()

    return KillSwitchStatusResponse(
        is_active=status["is_active"],
        activated_at=status["activated_at"],
        activation_reason=status["activation_reason"],
        auto_triggers=status["auto_triggers"],
        manual_triggers=status["manual_triggers"],
        total_resets=status["total_resets"],
        message=status["message"],
    )
