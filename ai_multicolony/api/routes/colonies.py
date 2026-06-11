"""Colony API routes."""

from __future__ import annotations
import logging
from typing import Any, Dict

from fastapi import HTTPException

from ..schemas import ColonyCreateRequest, ColonyCreateResponse

logger = logging.getLogger(__name__)


class ColonyRoutes:
    def __init__(self, colony_manager: Any = None):
        self._colony_manager = colony_manager

    async def create_colony(self, request: ColonyCreateRequest) -> ColonyCreateResponse:
        if self._colony_manager:
            from ...types import ColonyConfig
            config = ColonyConfig(name=request.name, goal=request.goal, max_agents=request.max_agents)
            colony = await self._colony_manager.create_colony(config)
            return ColonyCreateResponse(colony_id=colony.colony_id, name=request.name)
        logger.error(
            "colony_create_stub - ColonyManager not injected, raising 503. "
            "Colony creation is unavailable without a ColonyManager."
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Colony service unavailable - ColonyManager not configured",
                "code": "SERVICE_UNAVAILABLE",
            },
        )

    async def list_colonies(self) -> Dict[str, Any]:
        if self._colony_manager:
            return {"colonies": self._colony_manager.list_colonies()}
        logger.warning("colony_list_stub - ColonyManager not injected, raising 503")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Colony service unavailable - ColonyManager not configured",
                "code": "SERVICE_UNAVAILABLE",
                "warning": "ColonyManager not configured",
            },
        )

    async def get_colony(self, colony_id: str) -> Dict[str, Any]:
        if self._colony_manager:
            colony = self._colony_manager.get_colony(colony_id)
            if colony:
                return colony.get_status()
        logger.error("colony_get_stub - ColonyManager not injected, colony %s not available, raising 503", colony_id)
        raise HTTPException(
            status_code=503,
            detail={
                "error": f"Colony {colony_id} not found (service unavailable)",
                "code": "SERVICE_UNAVAILABLE",
            },
        )

    async def shutdown_colony(self, colony_id: str) -> Dict[str, Any]:
        if self._colony_manager:
            success = await self._colony_manager.shutdown_colony(colony_id)
            return {"status": "shutdown" if success else "not_found"}
        logger.error("colony_shutdown_stub - ColonyManager not injected, cannot shut down colony %s, raising 503", colony_id)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ColonyManager not configured",
                "code": "SERVICE_UNAVAILABLE",
            },
        )
