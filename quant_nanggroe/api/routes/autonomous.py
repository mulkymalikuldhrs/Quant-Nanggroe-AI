"""Autonomous Agent API Routes — LLM-routed, self-correcting trading pipeline."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from quant_nanggroe.engine.agentic import (
    AutonomousPipeline,
    SelfCorrection,
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

@router.get("/last-result")
async def get_last_pipeline_result():
    """Return the last pipeline run result (cached)."""
    p = _get_pipeline()
    if p._last_result is None:
        raise HTTPException(status_code=404, detail="No pipeline run yet. POST /pipeline/run first.")
    r = p._last_result
    return {
        "symbol": r.symbol, "success": r.success,
        "signal": r.signal, "confidence": r.confidence,
        "reason": r.reason, "timestamp": r.timestamp,
        "steps": [{"name": s.name, "status": s.status, "duration_ms": s.duration_ms}
                  for s in r.steps],
        "decision": r.decision,
    }


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


# -----------------------------------------------------------------------
# SLA metrics
# -----------------------------------------------------------------------

@router.get("/sla")
async def get_sla_metrics():
    """Get SLA metrics from the pipeline and trade lifecycle manager.

    Returns:
        Dict with pipeline SLA, trade lifecycle SLA, PnL strategy stats,
        and self-correction stats.
    """
    pipeline = _get_pipeline()
    result: dict[str, Any] = {}

    # Pipeline SLA (last result)
    if pipeline._last_result is not None:
        sla = pipeline._last_result.sla
        result["pipeline"] = {
            "symbol": pipeline._last_result.symbol,
            "success": pipeline._last_result.success,
            "total_duration_ms": sla.total_duration_ms,
            "data_to_signal_ms": sla.data_to_signal_ms,
            "signal_to_risk_ms": sla.signal_to_risk_ms,
            "risk_to_exec_ms": sla.risk_to_exec_ms,
            "closed_trade_to_eval_ms": sla.closed_trade_to_eval_ms,
            "eval_to_evolve_ms": sla.eval_to_evolve_ms,
            "cycle_time_ms": sla.cycle_time_ms,
            "trades_evaluated": sla.trades_evaluated,
            "evolutions_triggered": sla.evolutions_triggered,
            "lessons_recorded": sla.lessons_recorded,
            "avg_eval_time_ms": sla.avg_eval_time_ms,
            "sla_breached": sla.sla_breached,
            "sla_threshold_ms": sla.sla_threshold_ms,
        }
    else:
        result["pipeline"] = {"message": "No pipeline run yet. POST /api/autonomous/pipeline/run first."}

    # Trade lifecycle SLA
    if pipeline._trade_lifecycle is not None:
        result["trade_lifecycle"] = pipeline._trade_lifecycle.get_lifecycle_stats()
        result["recent_cycles"] = pipeline._trade_lifecycle.get_recent_cycles(limit=10)
    else:
        result["trade_lifecycle"] = {"message": "TradeLifecycleManager not initialized"}
        result["recent_cycles"] = []

    # PnL strategy stats
    if pipeline._pnl_evaluator is not None:
        try:
            result["strategy_stats"] = pipeline._pnl_evaluator.get_all_strategy_stats()
        except Exception as exc:
            result["strategy_stats"] = {"error": str(exc)}
    else:
        result["strategy_stats"] = {}

    # Self-correction stats
    result["self_correction"] = pipeline.correction.get_stats()

    return result


# -----------------------------------------------------------------------
# Evolution
# -----------------------------------------------------------------------

@router.post("/evolve")
async def trigger_evolution(body: dict[str, Any]):
    """Trigger strategy evolution based on PnL feedback and lessons.

    Scans PnLEvaluator stats for underperforming strategies (win_rate < 40%,
    total_pnl < 0), reviews unresolved SelfCorrection lessons, and returns
    a list of strategies flagged for evolution.

    Body:
        strategy: Optional strategy name to evolve (evolves all if omitted).
        force: If true, force evolution regardless of performance (default false).

    Returns:
        Dict with strategies_evaluated, evolutions_triggered, lessons_reviewed.
    """
    pipeline = _get_pipeline()
    strategy_name = body.get("strategy", "")
    force = body.get("force", False)

    result: dict[str, Any] = {
        "strategies_evaluated": 0,
        "evolutions_triggered": 0,
        "lessons_reviewed": 0,
        "strategies_to_evolve": [],
    }

    # 1. Scan PnLEvaluator for underperforming strategies
    if pipeline._pnl_evaluator is not None:
        try:
            all_stats = pipeline._pnl_evaluator.get_all_strategy_stats()
            for sname, stats in all_stats.items():
                if strategy_name and sname != strategy_name:
                    continue
                result["strategies_evaluated"] += 1
                needs_evolve = force or (
                    stats.get("win_rate", 1.0) < 0.4 and stats.get("total_pnl", 0) < 0
                )
                if needs_evolve:
                    result["strategies_to_evolve"].append({
                        "strategy": sname,
                        "win_rate": stats.get("win_rate", 0),
                        "total_pnl": stats.get("total_pnl", 0),
                        "sharpe": stats.get("sharpe", 0),
                    })
                    result["evolutions_triggered"] += 1
        except Exception as exc:
            logger.warning("PnLEvaluator strategy scan failed: %s", exc)

    # 2. Review unresolved lessons
    try:
        sc = SelfCorrection()
        lessons = sc.list_lessons(unresolved_only=True, limit=100)
        for lesson in lessons:
            if strategy_name and strategy_name not in str(lesson.get("context", {})):
                continue
            result["lessons_reviewed"] += 1
            if force or lesson.get("severity") in ("error", "critical"):
                sc.resolve(lesson["id"], "Evolved via /api/autonomous/evolve")
    except Exception as exc:
        logger.warning("Lesson review failed: %s", exc)

    return result
