"""Autonomous Agent API Routes — LLM-routed, self-correcting trading pipeline."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from quant_nanggroe.engine.agentic import (
    AutonomousPipeline,
    SelfCorrection,
    discover_strategies,
    get_autonomous_pipeline,
    register_free_providers,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/autonomous", tags=["Autonomous"])


def _get_pipeline() -> AutonomousPipeline:
    p = get_autonomous_pipeline()
    if not p.list_available_strategies():
        p.load_strategies()
    return p


# -----------------------------------------------------------------------
# Strategy discovery
# -----------------------------------------------------------------------

@router.get("/strategies")
async def list_discovered_strategies():
    """List strategies auto-discovered from the strategies directory."""
    pipeline = _get_pipeline()
    return {
        "count": len(pipeline._strategies),
        "strategies": pipeline.list_available_strategies(),
    }


@router.post("/strategies/discover")
async def rediscover_strategies():
    """Force re-discovery of strategies."""
    pipeline = _get_pipeline()
    count = pipeline.load_strategies()
    return {"discovered": count, "strategies": pipeline.list_available_strategies()}


@router.get("/strategies/{name}")
async def get_strategy_info(name: str):
    """Get info about a specific strategy."""
    pipeline = _get_pipeline()
    if name not in pipeline._strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    cls = pipeline._strategies[name]
    return {
        "name": name,
        "class": cls.__name__,
        "module": cls.__module__,
        "methods": [m for m in dir(cls) if not m.startswith("_")],
    }


# -----------------------------------------------------------------------
# Self-correction / lessons
# -----------------------------------------------------------------------

@router.get("/lessons")
async def list_lessons(
    category: str | None = None,
    unresolved: bool = False,
    limit: int = 20,
):
    """List recorded lessons."""
    sc = SelfCorrection()
    return {"lessons": sc.list_lessons(category, unresolved, limit), "stats": sc.get_stats()}


@router.post("/lessons/record")
async def record_lesson(body: dict[str, Any]):
    """Record a new lesson."""
    sc = SelfCorrection()
    lesson = sc.record(
        category=body.get("category", "manual"),
        summary=body.get("summary", ""),
        detail=body.get("detail", ""),
        severity=body.get("severity", "info"),
        context=body.get("context"),
    )
    return {"id": lesson.id, "summary": lesson.summary, "occurred_at": lesson.occurred_at}


@router.post("/lessons/{lesson_id}/resolve")
async def resolve_lesson(lesson_id: str, body: dict[str, str] | None = None):
    """Mark a lesson as resolved."""
    sc = SelfCorrection()
    ok = sc.resolve(lesson_id, (body or {}).get("resolution", ""))
    if not ok:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")
    return {"id": lesson_id, "status": "resolved"}


# -----------------------------------------------------------------------
# Pipeline execution
# -----------------------------------------------------------------------

@router.post("/pipeline/run")
async def run_pipeline(body: dict[str, Any]):
    """Run the autonomous trading pipeline for one symbol.

    Body:
        symbol (required): Trading symbol (e.g. "BTC-USD").
        strategy: Optional strategy name to use.
        use_llm: Whether to route through LLM reasoning (default false).
    """
    symbol = body.get("symbol")
    if not symbol:
        raise HTTPException(status_code=400, detail="'symbol' is required")

    pipeline = _get_pipeline()
    result = await pipeline.run(
        symbol=symbol,
        strategy_name=body.get("strategy"),
        use_llm=body.get("use_llm", False),
    )
    return {
        "symbol": result.symbol,
        "success": result.success,
        "signal": result.signal,
        "confidence": result.confidence,
        "reason": result.reason,
        "timestamp": result.timestamp,
        "decision": result.decision,
        "steps": [{"name": s.name, "status": s.status, "duration_ms": s.duration_ms,
                    "result": s.result, "error": s.error} for s in result.steps],
    }


@router.post("/pipeline/batch")
async def run_batch_pipeline(body: dict[str, Any]):
    """Run the autonomous trading pipeline across multiple symbols.

    Body:
        symbols: List of symbols (default: ["BTC-USD", "ETH-USD", "SOL-USD"]).
        strategy: Optional strategy name.
        use_llm: Whether to use LLM reasoning (default false).
    """
    pipeline = _get_pipeline()
    symbols = body.get("symbols")
    results = await pipeline.run_batch(
        symbols=symbols,
        strategy_name=body.get("strategy"),
        use_llm=body.get("use_llm", False),
    )
    return {
        "results": [
            {
                "symbol": r.symbol,
                "success": r.success,
                "signal": r.signal,
                "confidence": r.confidence,
                "reason": r.reason,
                "steps": len(r.steps),
            }
            for r in results
        ],
        "total": len(results),
        "success_count": sum(1 for r in results if r.success),
    }


# -----------------------------------------------------------------------
# LLM provider management
# -----------------------------------------------------------------------

@router.post("/providers/register-free")
async def register_free_llm_providers():
    """Register free LLM providers (Groq, DeepSeek, HuggingFace, Nous)."""
    try:
        from quant_nanggroe.engine.llm_router import get_llm_router
        router = get_llm_router()
        register_free_providers(router)
        return {"status": "ok", "message": "Free providers registered (if API keys available)"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/providers/status")
async def get_provider_status():
    """Get LLM provider health status."""
    try:
        from quant_nanggroe.engine.llm_router import get_llm_router
        router = get_llm_router()
        return router.get_health()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
