"""Council API routes — wired to real CouncilDecisionLogger."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/council", tags=["council"])


def _get_council_logger() -> Any:
    """Lazy-load the CouncilDecisionLogger."""
    try:
        from quant_nanggroe.agents.debate.council_logger import CouncilDecisionLogger
        return CouncilDecisionLogger()
    except Exception as exc:
        logger.warning("CouncilDecisionLogger unavailable: %s", exc)
        return None


@router.get("/list")
async def list_decisions(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    """List recent council decisions from the real audit log."""
    cl = _get_council_logger()
    if cl is None:
        return {
            "sessions": [],
            "count": 0,
            "module": "council",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "no_council_logger",
        }
    decisions = cl.get_recent_decisions(limit=limit)
    return {
        "sessions": decisions,
        "count": len(decisions),
        "module": "council",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stats")
async def council_stats() -> dict[str, Any]:
    """Get council decision statistics."""
    cl = _get_council_logger()
    if cl is None:
        return {"total_decisions": 0, "module": "council"}
    return cl.get_stats()


@router.get("/query")
async def query_decisions(
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    min_confidence: float = 0.0,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Query council decisions with filters."""
    cl = _get_council_logger()
    if cl is None:
        return {"items": [], "count": 0}
    results = cl.query_decisions(
        symbol=symbol,
        direction=direction,
        min_confidence=min_confidence,
        limit=limit,
    )
    return {"items": results, "count": len(results)}


@router.get("/{decision_id}")
async def get_decision(decision_id: str) -> dict[str, Any]:
    """Get a specific council decision by ID."""
    cl = _get_council_logger()
    if cl is None:
        raise HTTPException(status_code=404, detail="Council logger unavailable")
    decisions = cl.query_decisions(limit=10000)
    for d in decisions:
        if d.get("decision_id") == decision_id:
            return d
    raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found")
