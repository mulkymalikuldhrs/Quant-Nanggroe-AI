"""Colony API routes.

Endpoints:
* POST /api/v1/colonies          – create colony
* GET  /api/v1/colonies          – list colonies
* GET  /api/v1/colonies/{id}     – colony status
* POST /api/v1/colonies/{id}/scale – scale colony
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..schemas import (
    ColonyCreateRequest,
    ColonyCreateResponse,
    ColonyStatusResponse,
    ColonyListResponse,
    ColonyScaleRequest,
    ColonyScaleResponse,
)

logger = logging.getLogger(__name__)


class ColonyRoutes:
    """Route handlers for colony operations."""

    def __init__(self, colony_manager: Any = None):
        self._colony_manager = colony_manager

    async def create_colony(self, request: Optional[ColonyCreateRequest] = None, **kwargs: Any) -> Dict[str, Any]:
        """POST /api/v1/colonies – create a new colony."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = ColonyCreateRequest(
                name=data.get("name", "default"),
                goal=data.get("goal", ""),
                scale=data.get("scale", "medium"),
                max_agents=data.get("max_agents", 50),
                routing_strategy=data.get("routing_strategy", "least-loaded"),
            )

        if self._colony_manager and hasattr(self._colony_manager, "create_colony"):
            from ...types import ColonyConfig, ColonyScale, RoutingStrategy
            try:
                scale = ColonyScale(request.scale)
            except ValueError:
                scale = ColonyScale.MEDIUM

            try:
                routing = RoutingStrategy(request.routing_strategy)
            except ValueError:
                routing = RoutingStrategy.LEAST_LOADED

            config = ColonyConfig(
                name=request.name,
                goal=request.goal,
                scale=scale,
                max_agents=request.max_agents,
                routing_strategy=routing,
            )
            colony = await self._colony_manager.create_colony(config)
            return ColonyCreateResponse(
                colony_id=colony.colony_id,
                name=request.name,
                scale=scale.value,
            ).model_dump(mode="json")

        return ColonyCreateResponse(colony_id="stub", name=request.name).model_dump(mode="json")

    async def list_colonies(self, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/colonies – list all colonies."""
        if self._colony_manager and hasattr(self._colony_manager, "list_colonies"):
            colonies_raw = self._colony_manager.list_colonies()
            colonies = []
            for c in colonies_raw:
                colonies.append(ColonyStatusResponse(
                    colony_id=c.get("colony_id", ""),
                    name=c.get("name", ""),
                    goal=c.get("goal", ""),
                    status=c.get("status", "active"),
                    scale=c.get("scale", "medium"),
                    agent_count=c.get("agent_count", 0),
                    task_count=c.get("task_count", 0),
                    overseer_id=c.get("overseer_id"),
                    created_at=c.get("created_at"),
                    routing_strategy=c.get("routing_strategy", "least-loaded"),
                    hand_status=c.get("hand_status", {}),
                ).model_dump(mode="json"))
            return ColonyListResponse(colonies=colonies, total=len(colonies)).model_dump(mode="json")

        return ColonyListResponse().model_dump(mode="json")

    async def get_colony(self, colony_id: str, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/colonies/{id} – get colony status."""
        if self._colony_manager and hasattr(self._colony_manager, "get_colony"):
            colony = self._colony_manager.get_colony(colony_id)
            if colony:
                status = colony.get_status()
                return ColonyStatusResponse(
                    colony_id=status.get("colony_id", ""),
                    name=status.get("name", ""),
                    goal=status.get("goal", ""),
                    status=status.get("status", "active"),
                    scale=status.get("scale", "medium"),
                    agent_count=status.get("agent_count", 0),
                    task_count=status.get("task_count", 0),
                    overseer_id=status.get("overseer_id"),
                    created_at=status.get("created_at"),
                    routing_strategy=status.get("routing_strategy", "least-loaded"),
                    hand_status=status.get("hand_status", {}),
                ).model_dump(mode="json")

        return {"error": f"Colony {colony_id} not found", "code": "COLONY_NOT_FOUND"}

    async def scale_colony(self, colony_id: str, request: Optional[ColonyScaleRequest] = None, **kwargs: Any) -> Dict[str, Any]:
        """POST /api/v1/colonies/{id}/scale – scale a colony."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = ColonyScaleRequest(scale=data.get("scale", "medium"))

        if self._colony_manager and hasattr(self._colony_manager, "scale_colony"):
            from ...types import ColonyScale
            try:
                scale = ColonyScale(request.scale)
            except ValueError:
                return {"error": f"Invalid scale: {request.scale}", "code": "INVALID_SCALE"}

            colony = await self._colony_manager.scale_colony(colony_id, scale)
            return ColonyScaleResponse(
                colony_id=colony_id,
                scale=scale.value,
                max_agents=colony.config.max_agents,
            ).model_dump(mode="json")

        return {"error": f"Colony {colony_id} not found", "code": "COLONY_NOT_FOUND"}
