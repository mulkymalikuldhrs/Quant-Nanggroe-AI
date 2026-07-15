"""Security API routes — real audit events + kill-switch status.

No mock data: reads the live AuditLogger (from app.state) and the shared
KillSwitch instance. Falls back to empty (not fake) when state is absent.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["security"])


def _get_audit_logger(request: Request):
    try:
        from quant_nanggroe.services import get_audit_logger
        return get_audit_logger(request.app)
    except Exception:
        return None


def _get_kill_switch(request: Request):
    try:
        from quant_nanggroe.services import get_kill_switch
        return get_kill_switch(request.app)
    except Exception:
        return None


@router.get("/security/events")
async def security_events(request: Request, limit: int = 50) -> dict[str, Any]:
    """Return real audit events as security events (honest, no fallback seed)."""
    al = _get_audit_logger(request)
    if al is None or not getattr(al, "entries", None):
        return {"events": [], "total": 0, "source": "none"}
    sev_map = {
        "INFO": "info", "WARNING": "warning",
        "ERROR": "critical", "CRITICAL": "critical",
    }
    events = []
    for e in al.entries[-limit:]:
        events.append({
            "id": str(e.get("id", "")),
            "type": str(e.get("layer", "system")).lower(),
            "severity": sev_map.get(e.get("severity", "INFO"), "info"),
            "message": e.get("message", ""),
            "timestamp": e.get("timestamp", ""),
            "detail": str(e.get("details", ""))[:200],
            "agent": str(e.get("layer", "system")).lower(),
        })
    return {"events": events, "total": len(events), "source": "audit_logger"}


@router.get("/security/status")
async def security_status(request: Request) -> dict[str, Any]:
    """Return real kill-switch status."""
    ks = _get_kill_switch(request)
    if ks is None:
        return {"kill_switch_active": False, "level": "none", "status": "inactive", "source": "none"}
    st = ks.status()
    return {
        "kill_switch_active": st.get("is_active", False),
        "level": st.get("current_level", "none"),
        "status": st.get("status", "inactive"),
        "reason": st.get("activation_reason", ""),
        "total_activations": st.get("total_activations", 0),
        "source": "kill_switch",
    }
