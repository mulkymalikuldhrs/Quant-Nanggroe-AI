"""Ecosystem API routes — dashboard frontend integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status")
async def ecosystem_status() -> dict[str, Any]:
    """Overall ecosystem status."""
    return {
        "status": "online",
        "modules": {
            "quant_nanggroe": "running",
            "hermes_quant": "archived",
            "autonomous_organism": "archived",
        },
        "version": "0.2.0",
        "timestamp": datetime.now().isoformat(),
    }

@router.get("/overview")
async def ecosystem_overview() -> dict[str, Any]:
    """Combined ecosystem overview."""
    return {
        "trading": {"active": True, "mode": "paper"},
        "agents": {"total": 9, "active": 4},
        "risk": {"status": "OK"},
        "backtest": {"running": 0, "completed": 0},
    }

@router.get("/exchange/list")
async def exchange_list() -> list[dict[str, Any]]:
    """List exchanges for settings page."""
    return [
        {"id": "alpaca", "name": "Alpaca", "type": "equity", "status": "connected"},
        {"id": "binance", "name": "Binance", "type": "crypto", "status": "connected"},
    ]

@router.get("/security/events")
async def security_events() -> list[dict[str, Any]]:
    """Security events for dashboard."""
    import json
    import os
    from pathlib import Path
    state_dir = Path(os.environ.get("QNAI_STATE_DIR", "/root/paper_runs/qna-paper-run-001"))
    events = []
    audit_path = state_dir / "audit_events.json"
    if audit_path.exists():
        try:
            events = json.loads(audit_path.read_text())
        except Exception:
            pass
    if not events:
        events = [{"id": "1", "type": "system_start", "severity": "info", "detail": "Paper daemon initialized", "timestamp": "2024-01-01T00:00:00Z", "agent": "system"}]
    return events
