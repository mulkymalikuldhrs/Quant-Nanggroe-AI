"""Agent API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from quant_nanggroe.api.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentStatusResponse,
    KillSwitchActivateRequest,
    KillSwitchResetRequest,
    KillSwitchStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    """Run an agent pipeline for a symbol.

    Executes the full agent graph (market analysis → decision → risk check)
    for the given symbol.

    Args:
        request: AgentRunRequest with symbol and query.

    Returns:
        AgentRunResponse with agent trace and decision.
    """
    # Placeholder — would invoke the trading graph
    return AgentRunResponse(
        status="pending",
        symbol=request.symbol,
        query=request.query,
    )


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status(http_request: Request) -> AgentStatusResponse:
    """Get agent system status.

    Returns current status of all agents, kill switch state, and
    system health.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        AgentStatusResponse with system status.
    """
    kill_switch_active = False
    try:
        from quant_nanggroe.services import get_kill_switch
        ks = get_kill_switch(http_request.app)
        kill_switch_active = ks.is_active
    except Exception:
        pass

    return AgentStatusResponse(
        agents=[],
        active=True,
        kill_switch_active=kill_switch_active,
    )


@router.post("/kill-switch/activate", response_model=KillSwitchStatusResponse)
async def activate_kill_switch(
    request: KillSwitchActivateRequest,
    http_request: Request,
) -> KillSwitchStatusResponse:
    """Activate the kill switch — HALT all trading immediately.

    This is an emergency action. All trading stops until manually reset.

    Args:
        request: KillSwitchActivateRequest with reason.
        http_request: HTTP request for accessing app state.

    Returns:
        KillSwitchStatusResponse with updated status.
    """
    try:
        from quant_nanggroe.services import get_kill_switch
        ks = get_kill_switch(http_request.app)
        ks.activate(request.reason)
        status = ks.status()
        return KillSwitchStatusResponse(
            is_active=True,
            activated_at=status.get("activated_at"),
            activation_reason=status.get("activation_reason"),
            auto_triggers=status.get("auto_triggers", 0),
            manual_triggers=status.get("manual_triggers", 0),
            total_resets=status.get("total_resets", 0),
            message="Kill switch activated. All trading halted.",
        )
    except Exception as exc:
        logger.error("kill_switch_activate_failed", extra={"error": str(exc)})
        return KillSwitchStatusResponse(is_active=False, message=f"Failed: {exc}")


@router.post("/kill-switch/reset", response_model=KillSwitchStatusResponse)
async def reset_kill_switch(
    request: KillSwitchResetRequest,
    http_request: Request,
) -> KillSwitchStatusResponse:
    """Reset the kill switch — resume trading.

    Requires confirmation string "CONFIRM" to prevent accidental resets.

    Args:
        request: KillSwitchResetRequest with confirmation.
        http_request: HTTP request for accessing app state.

    Returns:
        KillSwitchStatusResponse with updated status.
    """
    if request.confirmation != "CONFIRM":
        return KillSwitchStatusResponse(
            is_active=True,
            message="Reset requires confirmation string 'CONFIRM'",
        )

    try:
        from quant_nanggroe.services import get_kill_switch
        ks = get_kill_switch(http_request.app)
        ks.reset()
        status = ks.status()
        return KillSwitchStatusResponse(
            is_active=False,
            message="Kill switch reset. Trading resumed.",
        )
    except Exception as exc:
        logger.error("kill_switch_reset_failed", extra={"error": str(exc)})
        return KillSwitchStatusResponse(is_active=True, message=f"Failed: {exc}")


@router.get("/kill-switch/status", response_model=KillSwitchStatusResponse)
async def get_kill_switch_status(http_request: Request) -> KillSwitchStatusResponse:
    """Get kill switch status.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        KillSwitchStatusResponse with current status.
    """
    try:
        from quant_nanggroe.services import get_kill_switch
        ks = get_kill_switch(http_request.app)
        status = ks.status()
        return KillSwitchStatusResponse(
            is_active=status.get("is_active", False),
            activated_at=status.get("activated_at"),
            activation_reason=status.get("activation_reason"),
            auto_triggers=status.get("auto_triggers", 0),
            manual_triggers=status.get("manual_triggers", 0),
            total_resets=status.get("total_resets", 0),
            message=status.get("message", ""),
        )
    except Exception:
        return KillSwitchStatusResponse(is_active=False, message="Status unavailable")
