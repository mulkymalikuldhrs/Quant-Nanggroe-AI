"""Monitor & Risk API routes — reads paper-run disk artifacts."""

from __future__ import annotations

import csv
import json
import logging
import os
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Request

logger = logging.getLogger(__name__)
router = APIRouter()


def _state_dir() -> Path:
    return Path(os.environ.get("QNAI_STATE_DIR", "/root/paper_runs/qna-paper-run-001"))


def _read_json(name: str) -> dict[str, Any]:
    p = _state_dir() / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as exc:
        logger.warning("read_json_failed name=%s error=%s", name, exc)
        return {}


def _read_csv(name: str) -> list[dict[str, Any]]:
    p = _state_dir() / name
    if not p.exists():
        return []
    try:
        text = p.read_text()
        reader = csv.DictReader(StringIO(text))
        return list(reader)
    except Exception as exc:
        logger.warning("read_csv_failed name=%s error=%s", name, exc)
        return []


def _read_jsonl_last(name: str) -> dict[str, Any] | None:
    p = _state_dir() / name
    if not p.exists():
        return None
    try:
        text = p.read_text().strip()
        if not text:
            return None
        last_line = text.splitlines()[-1]
        return json.loads(last_line)
    except Exception as exc:
        logger.warning("read_jsonl_last_failed name=%s error=%s", name, exc)
        return None


def _read_audit(severity: str | None, limit: int) -> list[dict[str, Any]]:
    sdir = _state_dir()
    today = date.today()
    entries: list[dict[str, Any]] = []
    for i in range(7):
        fname = f"audit_{today.strftime('%Y%m%d')}.json"
        p = sdir / fname
        if p.exists():
            try:
                data = json.loads(p.read_text())
                batch = data if isinstance(data, list) else [data]
                for e in batch:
                    if severity and e.get("severity", "").upper() != severity.upper():
                        continue
                    entries.append(e)
            except Exception as exc:
                logger.warning("read_audit_failed name=%s error=%s", fname, exc)
        today -= timedelta(days=1)
        if len(entries) >= limit:
            break
    return entries[:limit]


@router.get("/health")
async def health() -> dict[str, Any]:
    """Daemon health — reads state.json and checks daemon.pid."""
    state = _read_json("state.json")
    pid_path = _state_dir() / "daemon.pid"
    pid_alive = pid_path.exists()
    return {
        "status": "healthy" if state and pid_alive else "degraded",
        "daemon_pid": pid_path.read_text().strip() if pid_alive else None,
        "state": state,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Latest MonitorHub metrics from metrics.jsonl (last line)."""
    last = _read_jsonl_last("metrics.jsonl")
    if last is None:
        return {"metrics": None, "timestamp": datetime.now().isoformat()}
    return {"metrics": last, "timestamp": datetime.now().isoformat()}


@router.get("/pnl")
async def pnl() -> dict[str, Any]:
    """P&L summary from pnl.csv — last 24h, last 7 days, total."""
    rows = _read_csv("pnl.csv")
    now = datetime.now()
    total = 0.0
    last_24h = 0.0
    last_7d = 0.0
    count = len(rows)
    for r in rows:
        try:
            val = float(r.get("pnl", r.get("value", 0)))
        except (ValueError, TypeError):
            continue
        total += val
        ts_str = r.get("timestamp", r.get("time", ""))
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts >= now - timedelta(hours=24):
                    last_24h += val
                if ts >= now - timedelta(days=7):
                    last_7d += val
            except (ValueError, TypeError):
                pass
    return {
        "total_pnl": round(total, 4),
        "last_24h": round(last_24h, 4),
        "last_7d": round(last_7d, 4),
        "total_cycles": count,
        "timestamp": now.isoformat(),
    }


@router.get("/pnl/attribution")
async def pnl_attribution(
    limit: int = Query(100, ge=1, le=10000),
) -> list[dict[str, Any]]:
    """Per-symbol P&L from pnl_attribution.csv (last N rows)."""
    rows = _read_csv("pnl_attribution.csv")
    return rows[-limit:] if limit < len(rows) else rows


@router.get("/regime")
async def regime() -> dict[str, Any]:
    """Current regime from regime_state.json."""
    data = _read_json("regime_state.json")
    if not data:
        return {"regime": None, "timestamp": datetime.now().isoformat()}
    return {**data, "timestamp": datetime.now().isoformat()}


@router.get("/risk")
async def risk() -> dict[str, Any]:
    """Risk status from state.json — drawdown and kill switch state."""
    state = _read_json("state.json")
    return {
        "drawdown": {
            "current": state.get("drawdown", state.get("current_drawdown", 0.0)),
            "max": state.get("max_drawdown", 0.0),
        },
        "kill_switch_active": state.get("kill_switch", state.get("kill_switch_active", False)),
        "overall_status": state.get("status", state.get("overall_status", "unknown")),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/audit")
async def audit(
    severity: str | None = Query(None),
    limit: int = Query(10, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """Filtered audit entries from daily audit_YYYYMMDD.json files."""
    return _read_audit(severity, limit)


@router.get("/summary")
async def summary() -> dict[str, Any]:
    """All monitor/risk data combined."""
    return {
        "health": await health(),
        "metrics": await metrics(),
        "pnl": await pnl(),
        "regime": await regime(),
        "risk": await risk(),
        "timestamp": datetime.now().isoformat(),
    }
