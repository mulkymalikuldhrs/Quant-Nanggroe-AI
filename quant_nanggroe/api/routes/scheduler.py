"""Scheduler Control API — start/stop/status of autonomous trading pipeline."""

from __future__ import annotations

import os
import logging
from typing import Any

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])


@router.get("/status")
async def scheduler_status() -> dict[str, Any]:
    """Get current scheduler status."""
    try:
        from quant_nanggroe.engine.scheduler import _default_scheduler
        if _default_scheduler is None:
            return {"running": False, "reason": "not started"}
        return {
            "running": _default_scheduler.is_running,
            "interval_minutes": _default_scheduler.interval_minutes,
            "symbols": _default_scheduler.symbols,
        }
    except Exception as exc:
        return {"running": False, "error": str(exc)}


@router.post("/start")
async def start_scheduler(request: Request, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Start the autonomous trading scheduler."""
    from quant_nanggroe.security.auth import UserRole
    if hasattr(request.state, 'user_role') and request.state.user_role not in (UserRole.ADMIN, UserRole.TRADER):
        return {"error": "Trader+ role required for scheduler control", "status": "forbidden"}
    from quant_nanggroe.engine.scheduler import start_default_scheduler
    body = body or {}
    interval = body.get("interval_minutes", int(os.environ.get("QNA_SCHEDULER_INTERVAL", "15")))
    symbols = body.get("symbols")
    try:
        scheduler = start_default_scheduler(interval_minutes=interval, symbols=symbols)
        return {
            "status": "started",
            "interval_minutes": scheduler.interval_minutes,
            "symbols": scheduler.symbols,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/stop")
async def stop_scheduler(request: Request) -> dict[str, Any]:
    """Stop the autonomous trading scheduler."""
    from quant_nanggroe.security.auth import UserRole
    if hasattr(request.state, 'user_role') and request.state.user_role not in (UserRole.ADMIN, UserRole.TRADER):
        return {"error": "Trader+ role required for scheduler control", "status": "forbidden"}
    from quant_nanggroe.engine.scheduler import stop_default_scheduler
    try:
        stop_default_scheduler(timeout=3.0)
        return {"status": "stopped"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/cycle")
async def trigger_cycle(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Manually trigger one pipeline cycle."""
    from quant_nanggroe.engine.agentic import get_autonomous_pipeline
    body = body or {}
    pipeline = get_autonomous_pipeline()
    if not pipeline.list_available_strategies():
        pipeline.load_strategies()
    symbols = body.get("symbols", ["BTC-USD", "ETH-USD", "SOL-USD"])
    results = await pipeline.run_batch(symbols=symbols)
    return {
        "total": len(results),
        "success_count": sum(1 for r in results if r.success),
        "results": [
            {"symbol": r.symbol, "success": r.success, "signal": r.signal,
             "confidence": r.confidence, "reason": r.reason}
            for r in results
        ],
    }
