"""Memory API routes.

Endpoints:
* POST /api/v1/memory/store   – store to memory
* POST /api/v1/memory/query   – query memory
* POST /api/v1/memory/compact – trigger compaction
* GET  /api/v1/memory/pages   – list pages
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..schemas import (
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryCompactRequest,
    MemoryCompactResponse,
    MemoryPagesResponse,
)

logger = logging.getLogger(__name__)


class MemoryRoutes:
    """Route handlers for memory operations."""

    def __init__(self, memory_manager: Any = None):
        self._memory_manager = memory_manager

    async def store(self, request: Optional[MemoryStoreRequest] = None, **kwargs: Any) -> Dict[str, Any]:
        """POST /api/v1/memory/store – store data to memory."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = MemoryStoreRequest(
                key=data.get("key", ""),
                value=data.get("value"),
                tier=data.get("tier", "t1_letta"),
                agent_id=data.get("agent_id", ""),
                colony_id=data.get("colony_id", ""),
            )

        if self._memory_manager and hasattr(self._memory_manager, "store"):
            from ...types import MemoryTier
            try:
                tier = MemoryTier(request.tier)
            except ValueError:
                tier = MemoryTier.T1_LETTA

            store_id = await self._memory_manager.store(
                request.key,
                request.value,
                tier=tier,
            )
            return MemoryStoreResponse(store_id=store_id).model_dump(mode="json")

        # Fallback
        import uuid
        return MemoryStoreResponse(store_id=uuid.uuid4().hex[:12]).model_dump(mode="json")

    async def query(self, request: Optional[MemoryQueryRequest] = None, **kwargs: Any) -> Dict[str, Any]:
        """POST /api/v1/memory/query – query memory."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = MemoryQueryRequest(
                query=data.get("query", ""),
                limit=data.get("limit", 10),
            )

        if self._memory_manager and hasattr(self._memory_manager, "search"):
            results = await self._memory_manager.search(request.query, limit=request.limit)
            return MemoryQueryResponse(results=results, total=len(results)).model_dump(mode="json")

        return MemoryQueryResponse().model_dump(mode="json")

    async def compact(self, request: Optional[MemoryCompactRequest] = None, **kwargs: Any) -> Dict[str, Any]:
        """POST /api/v1/memory/compact – trigger memory compaction."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = MemoryCompactRequest(
                agent_id=data.get("agent_id"),
                colony_id=data.get("colony_id"),
                strategy=data.get("strategy", "summary"),
            )

        if self._memory_manager and hasattr(self._memory_manager, "compact"):
            try:
                result = await self._memory_manager.compact(
                    agent_id=request.agent_id,
                    strategy=request.strategy,
                )
                pages_compacted = result.get("pages_compacted", 0) if isinstance(result, dict) else 0
                tokens_saved = result.get("tokens_saved", 0) if isinstance(result, dict) else 0
                return MemoryCompactResponse(
                    pages_compacted=pages_compacted,
                    tokens_saved=tokens_saved,
                ).model_dump(mode="json")
            except Exception as exc:
                return MemoryCompactResponse(
                    status="error",
                    pages_compacted=0,
                    tokens_saved=0,
                ).model_dump(mode="json")

        return MemoryCompactResponse().model_dump(mode="json")

    async def list_pages(self, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/memory/pages – list memory pages."""
        if self._memory_manager and hasattr(self._memory_manager, "list_pages"):
            pages = await self._memory_manager.list_pages()
            return MemoryPagesResponse(pages=pages, total=len(pages)).model_dump(mode="json")

        return MemoryPagesResponse().model_dump(mode="json")
