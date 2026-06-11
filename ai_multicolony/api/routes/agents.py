"""Agent API routes.

Endpoints:
* POST /api/v1/agents        – create agent
* GET  /api/v1/agents        – list agents
* GET  /api/v1/agents/{id}   – agent status
* POST /api/v1/agents/{id}/execute – execute task
* DELETE /api/v1/agents/{id} – terminate agent
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..schemas import (
    AgentCreateRequest,
    AgentCreateResponse,
    AgentStatusResponse,
    AgentListResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentDeleteResponse,
)

logger = logging.getLogger(__name__)


class AgentRoutes:
    """Route handlers for agent operations."""

    def __init__(self, registry: Any = None):
        self._registry = registry

    async def create_agent(self, request: Optional[AgentCreateRequest] = None, **kwargs: Any) -> AgentCreateResponse:
        """POST /api/v1/agents – create a new agent."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = AgentCreateRequest(
                agent_type=data.get("agent_type", "manus"),
                colony_id=data.get("colony_id"),
                autonomy_level=data.get("autonomy_level", 1),
                capabilities=data.get("capabilities", []),
                required_tools=data.get("required_tools", []),
            )

        if self._registry and hasattr(self._registry, "create_agent"):
            from ...types import AgentType
            try:
                agent_type = AgentType(request.agent_type)
            except ValueError:
                agent_type = AgentType.MANUS

            agent = self._registry.create_agent(agent_type)
            if agent and hasattr(agent, "agent_id"):
                return AgentCreateResponse(
                    agent_id=agent.agent_id,
                    agent_type=request.agent_type,
                    colony_id=request.colony_id,
                )

        # Fallback when no registry
        import uuid
        return AgentCreateResponse(
            agent_id=uuid.uuid4().hex[:12],
            agent_type=request.agent_type,
            colony_id=request.colony_id,
        )

    async def list_agents(self, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/agents – list all agents."""
        if self._registry and hasattr(self._registry, "list_agent_info"):
            infos = self._registry.list_agent_info()
            agents = []
            for info in infos:
                agents.append(AgentStatusResponse(
                    agent_id=info.agent_id if hasattr(info, "agent_id") else str(info.get("agent_id", "")),
                    agent_type=info.agent_type.value if hasattr(info, "agent_type") else str(info.get("agent_type", "")),
                    state=info.state.value if hasattr(info, "state") else str(info.get("state", "registered")),
                    autonomy_level=info.autonomy_level.value if hasattr(info, "autonomy_level") else info.get("autonomy_level", 1),
                    colony_id=info.colony_id if hasattr(info, "colony_id") else info.get("colony_id"),
                    health_score=info.health_score if hasattr(info, "health_score") else info.get("health_score", 1.0),
                    tasks_completed=info.tasks_completed if hasattr(info, "tasks_completed") else info.get("tasks_completed", 0),
                    tasks_failed=info.tasks_failed if hasattr(info, "tasks_failed") else info.get("tasks_failed", 0),
                ).model_dump(mode="json"))
            return AgentListResponse(agents=agents, total=len(agents)).model_dump(mode="json")

        return AgentListResponse().model_dump(mode="json")

    async def get_agent(self, agent_id: str, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/agents/{id} – get agent status."""
        if self._registry and hasattr(self._registry, "get_agent"):
            agent = self._registry.get_agent(agent_id)
            if agent:
                info = agent.info if hasattr(agent, "info") else agent
                return AgentStatusResponse(
                    agent_id=agent_id,
                    agent_type=info.agent_type.value if hasattr(info, "agent_type") else str(info.get("agent_type", "")),
                    state=info.state.value if hasattr(info, "state") else str(info.get("state", "registered")),
                    autonomy_level=info.autonomy_level.value if hasattr(info, "autonomy_level") else info.get("autonomy_level", 1),
                    colony_id=info.colony_id if hasattr(info, "colony_id") else info.get("colony_id"),
                    health_score=info.health_score if hasattr(info, "health_score") else info.get("health_score", 1.0),
                ).model_dump(mode="json")

        return {"error": f"Agent {agent_id} not found", "code": "AGENT_NOT_FOUND"}

    async def execute_task(self, agent_id: str, request: Optional[AgentExecuteRequest] = None, **kwargs: Any) -> Dict[str, Any]:
        """POST /api/v1/agents/{id}/execute – execute a task on an agent."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = AgentExecuteRequest(
                description=data.get("description", ""),
                payload=data.get("payload", {}),
                priority=data.get("priority", 2),
            )

        if self._registry and hasattr(self._registry, "get_agent"):
            agent = self._registry.get_agent(agent_id)
            if agent and hasattr(agent, "submit_task"):
                from ...types import Task, TaskPriority
                task = Task(
                    description=request.description,
                    payload=request.payload,
                    priority=TaskPriority(request.priority),
                    assigned_agent=agent_id,
                    timeout_ms=request.timeout_ms,
                    required_capabilities=request.required_capabilities,
                )
                result = await agent.submit_task(task)
                return AgentExecuteResponse(
                    task_id=task.task_id,
                    agent_id=agent_id,
                    status="submitted",
                ).model_dump(mode="json")

        return {"error": f"Agent {agent_id} not found", "code": "AGENT_NOT_FOUND"}

    async def terminate_agent(self, agent_id: str, **kwargs: Any) -> Dict[str, Any]:
        """DELETE /api/v1/agents/{id} – terminate an agent."""
        if self._registry and hasattr(self._registry, "get_agent"):
            agent = self._registry.get_agent(agent_id)
            if agent:
                if hasattr(agent, "terminate"):
                    await agent.terminate()
                if hasattr(self._registry, "remove_agent"):
                    self._registry.remove_agent(agent_id)
                return AgentDeleteResponse(agent_id=agent_id).model_dump(mode="json")

        return {"error": f"Agent {agent_id} not found", "code": "AGENT_NOT_FOUND"}
