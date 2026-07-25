"""Strategy registry API routes.

Provides discovery of live strategy registry via the StrategyRegistry singleton.
Supports listing and metadata queries for all registered trading strategies.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from quant_nanggroe.engine.strategies.registry import StrategyRegistry, get_strategy_metadata

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/registry")
async def strategy_registry() -> dict[str, Any]:
    """Return all registered strategies from the live StrategyRegistry.

    Wired to the real @StrategyRegistry.register decorator-based loader
    so the API always reflects what the engine can actually run.
    """
    names = StrategyRegistry.list_strategies()
    strategies = []
    for name in sorted(names):
        try:
            meta = get_strategy_metadata(name)
            strategies.append({
                "id": name,
                "name": meta.get("name", name),
                "description": meta.get("description", ""),
            })
        except ValueError:
            strategies.append({"id": name, "name": name, "description": ""})
    return {"strategies": strategies, "count": len(strategies)}


@router.get("/registry/{name}")
async def strategy_detail(name: str) -> dict[str, Any]:
    """Return metadata for a single registered strategy."""
    try:
        return get_strategy_metadata(name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
