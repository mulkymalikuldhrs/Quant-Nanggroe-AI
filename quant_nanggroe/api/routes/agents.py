"""Agent API routes."""

from __future__ import annotations

import logging
from datetime import datetime
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


def _get_trading_graph(http_request: Request):
    """Retrieve or lazily create a TradingGraph instance from app state."""
    from quant_nanggroe.agents.graph import TradingGraph
    from quant_nanggroe.config.settings import get_settings

    if not hasattr(http_request.app.state, "_services"):
        http_request.app.state._services = {}

    if "trading_graph" not in http_request.app.state._services:
        settings = get_settings()
        graph = TradingGraph(
            llm_provider=settings.default_llm_provider,
            deep_think_model=settings.default_llm_model,
            quick_think_model="gpt-4o-mini",
            api_key=settings.openai_api_key,
        )
        http_request.app.state._services["trading_graph"] = graph
    return http_request.app.state._services["trading_graph"]


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest, http_request: Request) -> AgentRunResponse:
    """Run an agent pipeline for a symbol.

    Executes the full agent graph (market analysis → decision → risk check)
    for the given symbol using the TradingGraph.

    Args:
        request: AgentRunRequest with symbol and query.
        http_request: HTTP request for accessing app state.

    Returns:
        AgentRunResponse with agent trace and decision.
    """
    try:
        graph = _get_trading_graph(http_request)

        # Run the full trading pipeline
        result = graph.run(
            symbols=[request.symbol],
            market_data={"query": request.query, "timeframe": request.timeframe},
        )

        # Extract the trace from agent_outputs
        agent_trace = []
        agent_outputs = result.get("agent_outputs", {})
        for agent_name, output in agent_outputs.items():
            if isinstance(output, dict):
                agent_trace.append({
                    "agent": agent_name,
                    "content": output.get("content", ""),
                    "confidence": output.get("confidence", 0.0),
                    "success": output.get("success", True),
                })

        # Extract decision action from the decisions list
        decisions = result.get("decisions", [])
        decision_action = ""
        if decisions:
            first_decision = decisions[0] if isinstance(decisions[0], dict) else {}
            decision_action = first_decision.get("action", "")

        # Extract risk verdict
        risk_verdict = result.get("risk_verdict", "")

        # Extract strategy signal
        signals = result.get("signals", [])
        strategy_signal = ""
        if signals:
            first_signal = signals[0] if isinstance(signals[0], dict) else {}
            strategy_signal = first_signal.get("direction", "")

        error = result.get("error")

        return AgentRunResponse(
            status="completed" if not error else "failed",
            symbol=request.symbol,
            query=request.query,
            agent_trace=agent_trace,
            decision_action=decision_action,
            risk_verdict=risk_verdict,
            strategy_signal=strategy_signal,
            error=error,
        )
    except Exception as exc:
        logger.error("run_agent_failed symbol=%s error=%s", request.symbol, exc)
        return AgentRunResponse(
            status="error",
            symbol=request.symbol,
            query=request.query,
            error=str(exc),
        )


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status(http_request: Request) -> AgentStatusResponse:
    """Get agent system status.

    Queries the AgentRegistry for registered agent types and checks
    the kill switch state for system health reporting.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        AgentStatusResponse with system status.
    """
    from quant_nanggroe.agents.registry import AgentRegistry

    kill_switch_active = False
    try:
        from quant_nanggroe.services import get_kill_switch
        ks = get_kill_switch(http_request.app)
        kill_switch_active = ks.is_active
    except Exception:
        logger.exception("unhandled_error")
        pass

    # Build agent list from the AgentRegistry
    agents = []
    try:
        registered_names = AgentRegistry.list_agents()
        role_mapping = AgentRegistry.list_roles()

        for name in registered_names:
            # Find the role for this agent
            role_value = ""
            for agent_role, agent_name in role_mapping.items():
                if agent_name == name:
                    role_value = agent_role.value
                    break

            agents.append({
                "name": name,
                "role": role_value,
                "registered": True,
            })
    except Exception as exc:
        logger.warning("get_agent_status_registry_error: %s", exc)

    return AgentStatusResponse(
        agents=agents,
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
        logger.exception("unhandled_error")
        return KillSwitchStatusResponse(is_active=False, message="Status unavailable")
