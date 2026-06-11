"""Colony API routes."""

from __future__ import annotations
from typing import Any, Dict
from ..schemas import ColonyCreateRequest, ColonyCreateResponse


class ColonyRoutes:
    def __init__(self, colony_manager: Any = None):
        self._colony_manager = colony_manager

    async def create_colony(self, request: ColonyCreateRequest) -> ColonyCreateResponse:
        if self._colony_manager:
            from ...types import ColonyConfig
            config = ColonyConfig(name=request.name, goal=request.goal, max_agents=request.max_agents)
            colony = await self._colony_manager.create_colony(config)
            return ColonyCreateResponse(colony_id=colony.colony_id, name=request.name)
        return ColonyCreateResponse(colony_id="stub", name=request.name)

    async def list_colonies(self) -> Dict[str, Any]:
        if self._colony_manager:
            return {"colonies": self._colony_manager.list_colonies()}
        return {"colonies": []}

    async def get_colony(self, colony_id: str) -> Dict[str, Any]:
        if self._colony_manager:
            colony = self._colony_manager.get_colony(colony_id)
            if colony:
                return colony.get_status()
        return {"error": "Colony not found"}

    async def shutdown_colony(self, colony_id: str) -> Dict[str, Any]:
        if self._colony_manager:
            success = await self._colony_manager.shutdown_colony(colony_id)
            return {"status": "shutdown" if success else "not_found"}
        return {"status": "not_found"}
