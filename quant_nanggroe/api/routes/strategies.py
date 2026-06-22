"""API routes for strategy management, selection, and backtesting."""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from quant_nanggroe.engine.strategy.strategies import (
    create_strategy,
    list_strategies,
    get_strategy_metadata,
)
from quant_nanggroe.engine.strategy.strategy_selector import (
    StrategySelector,
    AdaptiveStrategyEngine,
)

router = APIRouter()


class StrategyToggle(BaseModel):
    name: str
    enabled: bool
    params: Optional[Dict] = None


class BacktestRequest(BaseModel):
    strategy_name: str
    params: Optional[Dict] = None
    symbol: str = "BTC"
    days: int = 365


# In-memory strategy config (toggles, params)
_strategy_config: Dict[str, StrategyToggle] = {}


@router.get("/list")
async def list_all_strategies():
    """List all registered strategies with metadata."""
    names = list_strategies()
    result = []
    for name in names:
        meta = get_strategy_metadata(name)
        config = _strategy_config.get(
            name, StrategyToggle(name=name, enabled=True)
        )
        result.append({
            "name": name,
            "description": meta.get("description", ""),
            "category": meta.get("category", ""),
            "asset_classes": meta.get("asset_classes", []),
            "timeframes": meta.get("timeframes", []),
            "enabled": config.enabled if hasattr(config, 'enabled') else True,
        })
    return {"strategies": result, "total": len(result)}


@router.post("/{name}/toggle")
async def toggle_strategy(name: str, toggle: StrategyToggle):
    """Enable or disable a strategy."""
    valid = list_strategies()
    if name not in valid:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    _strategy_config[name] = toggle
    return {"name": name, "enabled": toggle.enabled, "params": toggle.params or {}}


@router.get("/{name}")
async def get_strategy_detail(name: str):
    """Get detailed info about a specific strategy."""
    valid = list_strategies()
    if name not in valid:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    meta = get_strategy_metadata(name)
    config = _strategy_config.get(name, StrategyToggle(name=name, enabled=True))
    strategy = create_strategy(name)
    return {
        "name": name,
        "description": meta.get("description", ""),
        "category": meta.get("category", ""),
        "asset_classes": meta.get("asset_classes", []),
        "timeframes": meta.get("timeframes", []),
        "enabled": config.enabled,
        "warmup_period": strategy.warmup_period(),
        "required_columns": strategy.required_columns(),
        "params": strategy.params,
    }


@router.get("/selector/strategies")
async def get_selected_strategies(regime: str = "ranging", top_n: int = 3):
    """Get top N strategies for a given market regime."""
    selector = StrategySelector(top_n=top_n)
    selected = selector.select(regime)
    return {
        "regime": regime,
        "selected": [{"name": n, "score": s} for n, s in selected],
    }


@router.get("/toggles")
async def get_all_toggles():
    """Get all strategy toggle states."""
    return {
        name: {
            "enabled": cfg.enabled,
            "params": cfg.params or {},
        }
        for name, cfg in _strategy_config.items()
    }
