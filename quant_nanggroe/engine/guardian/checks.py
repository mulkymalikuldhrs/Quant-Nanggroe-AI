"""Individual health checks for the QNA Guardian.

Each check returns a CheckResult. Checks NEVER raise — they catch and
downgrade to a result so the guardian loop keeps running.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# ponytail: canonical surfaces
API_BASE = os.environ.get("QNA_API_URL", "http://localhost:8000")
UI_URL = os.environ.get("QNA_UI_URL", "http://localhost:3000")
API_KEY = os.environ.get("QNA_API_KEY", os.environ.get("NEXT_PUBLIC_API_KEY", ""))


class Severity:
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class CheckResult:
    name: str
    ok: bool
    severity: str
    detail: str
    hint: str = ""  # suggested fix / agent instruction
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "severity": self.severity,
            "detail": self.detail,
            "hint": self.hint,
            "timestamp": self.timestamp,
        }


# ── low-level helpers ──────────────────────────────────────────────
def _http_get(url: str, timeout: int = 5, with_key: bool = False) -> tuple[int, str]:
    """Return (status, body). status 0 = connection failure."""
    try:
        req = urllib.request.Request(url, method="GET")
        if with_key and API_KEY:
            req.add_header("Authorization", f"ApiKey {API_KEY}")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")[:4000]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:2000]
    except Exception as e:  # connection refused / timeout / etc.
        return 0, str(e)


def _safe_json(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except Exception:
        return None


# ── checks ─────────────────────────────────────────────────────────
def check_api_health() -> CheckResult:
    st, body = _http_get(f"{API_BASE}/health", timeout=5)
    if st == 200:
        return CheckResult("api_health", True, Severity.INFO, "API /health OK", "")
    if st == 0:
        return CheckResult(
            "api_health", False, Severity.CRITICAL,
            f"API unreachable at {API_BASE} ({body})",
            "Restart the QNA API (cli.py serve / uvicorn api.app:app). The backend is down.",
        )
    return CheckResult(
        "api_health", False, Severity.WARNING,
        f"API /health returned {st}",
        f"Inspect {API_BASE}/health response: {body[:500]}",
    )


def check_ui_canonical() -> CheckResult:
    """The single canonical UI must be alive on :3000."""
    st, body = _http_get(UI_URL, timeout=5)
    if st in (200, 301, 302, 307):
        return CheckResult("ui_canonical", True, Severity.INFO, "UI :3000 reachable", "")
    if st == 0:
        return CheckResult(
            "ui_canonical", False, Severity.CRITICAL,
            f"Canonical UI unreachable at {UI_URL} ({body})",
            "Start the Next.js dashboard: cd dashboard && npm run dev (or next start). "
            "This is the ONLY UI now that :8000 static dashboards were removed.",
        )
    return CheckResult(
        "ui_canonical", False, Severity.WARNING,
        f"Canonical UI returned {st}", f"Investigate {UI_URL} response.",
    )


def check_kill_switch() -> CheckResult:
    """Detects the silent AUTO_DAILY_LIMIT veto: looks healthy, trades nothing."""
    st, body = _http_get(f"{API_BASE}/api/agents/kill-switch/status", timeout=5, with_key=True)
    if st == 0:
        return CheckResult("kill_switch", False, Severity.WARNING,
                           f"Kill-switch status endpoint unreachable ({body})",
                           "API may be down; restart and re-check /api/agents/kill-switch/status.")
    if st in (401, 403):
        return CheckResult("kill_switch", False, Severity.WARNING,
                           f"Kill-switch auth required (HTTP {st}) — set QNA_API_KEY",
                           "Provide QNA_API_KEY env so the guardian can read kill-switch state.")
    data = _safe_json(body)
    if data is None:
        return CheckResult("kill_switch", False, Severity.WARNING,
                           f"Kill-switch returned non-JSON ({body[:300]})", "Inspect endpoint.")
    active = bool(data.get("active", False))
    reason = data.get("reason", "") or ""
    if active:
        # CRITICAL: the known footgun is AUTO_DAILY_LIMIT firing silently after restart
        is_silent_veto = "AUTO_DAILY_LIMIT" in reason or not reason
        sev = Severity.CRITICAL if is_silent_veto else Severity.WARNING
        return CheckResult(
            "kill_switch", False, sev,
            f"Kill-switch ACTIVE (reason={reason!r}) — all trading vetoed",
            "This is likely the silent AUTO_DAILY_LIMIT bug. Reset via "
            "/api/agents/kill-switch/reset with admin key, or investigate why it fired.",
        )
    return CheckResult("kill_switch", True, Severity.INFO, "Kill-switch inactive (trading enabled)", "")


def check_strategy_registry() -> CheckResult:
    """Strategy registry liveness — must expose >0 strategies via the decorator API."""
    st, body = _http_get(f"{API_BASE}/api/backtest/strategies", timeout=8, with_key=True)
    if st != 200:
        return CheckResult("strategy_registry", False, Severity.WARNING,
                           f"/api/backtest/strategies -> {st}",
                           "Verify StrategyRegistry is populated and the route is wired.")
    data = _safe_json(body)
    count = 0
    if isinstance(data, dict):
        count = len(data.get("strategies", data.get("data", [])))
    elif isinstance(data, list):
        count = len(data)
    if count == 0:
        return CheckResult("strategy_registry", False, Severity.CRITICAL,
                           "Strategy registry EMPTY (0 strategies loaded)",
                           "Run AutoRegistry scan; ensure all strategy modules are imported by "
                           "engine/strategies/__init__.py and QNA_USE_ADAPTIVE_PIPELINE=1.")
    return CheckResult("strategy_registry", True, Severity.INFO,
                       f"Strategy registry live: {count} strategies", "")


def check_mt5() -> CheckResult:
    """MT5 connectivity. Paper mode -> INFO (no broker needed). Live -> CRITICAL if down."""
    paper = os.environ.get("PAPER_TRADE", "true").lower() in ("1", "true", "yes")
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception:
        if paper:
            return CheckResult("mt5", True, Severity.INFO,
                               "MT5 lib not installed but PAPER_TRADE=true (acceptable)", "")
        return CheckResult("mt5", False, Severity.CRITICAL,
                           "MetaTrader5 not installed and PAPER_TRADE != true",
                           "Install MetaTrader5 or set PAPER_TRADE=true for paper mode.")
    try:
        if not mt5.initialize():
            if paper:
                return CheckResult("mt5", True, Severity.WARNING,
                                   "MT5 terminal not connected (paper mode tolerant)",
                                   "Relaunch the MT5 terminal if live trading is intended.")
            return CheckResult("mt5", False, Severity.CRITICAL,
                               "mt5.initialize() failed — terminal not running / not logged in",
                               "Relaunch MetaTrader5 terminal, enable AutoTrading, then re-run the "
                               "trading engine. The guardian cannot trade without a live terminal.")
        ti = mt5.terminal_info()
        ai = mt5.account_info()
        trade_allowed = getattr(ti, "trade_allowed", False) if ti else False
        if not trade_allowed:
            return CheckResult("mt5", False, Severity.CRITICAL,
                               "MT5 terminal connected but trade_allowed=False (AutoTrading OFF)",
                               "Enable AutoTrading in the MT5 terminal (Ctrl+E).")
        login = getattr(ai, "login", None) if ai else None
        return CheckResult("mt5", True, Severity.INFO,
                           f"MT5 connected (login={login}, trade_allowed=True)", "")
    except Exception as e:
        return CheckResult("mt5", False, Severity.CRITICAL,
                           f"MT5 probe error: {e}",
                           "Restart the trading engine and re-initialize MT5.")


def check_wiring() -> CheckResult:
    """Sample critical API endpoints — a 500/404 here means broken wiring."""
    critical = [
        "/api/version",
        "/api/backtest/engines",
        "/api/trading/positions",
        "/api/agents/status",
    ]
    failures = []
    for ep in critical:
        st, _ = _http_get(f"{API_BASE}{ep}", timeout=5, with_key=True)
        if st not in (200, 401, 403):  # 401/403 = wired but needs auth
            failures.append(f"{ep}:{st}")
    if failures:
        return CheckResult("wiring", False, Severity.CRITICAL,
                           f"Broken endpoints: {', '.join(failures)}",
                           "Run a full wiring audit; these routes returned non-2xx/non-auth.")
    return CheckResult("wiring", True, Severity.INFO, "Critical API endpoints wired (200/auth)", "")


def check_error_logs(root: str, max_age_min: int = 30) -> CheckResult:
    """Scan recent stderr/error logs for fresh Tracebacks / ERROR lines."""
    now = time.time()
    patterns = ("Traceback (most recent call last)", "Error:", "Exception:", "FATAL")
    hits = []
    candidates = [
        os.path.join(root, "api_stderr.log"),
        os.path.join(root, "api_stdout.log"),
        os.path.join(root, "dashboard", "dash_err.log"),
        os.path.join(root, "quant_nanggroe", "logs", "guardian.log"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            mtime = os.path.getmtime(path)
            if now - mtime > max_age_min * 60:
                continue  # stale, skip
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-200:]
            for ln in lines:
                if any(p in ln for p in patterns):
                    hits.append(ln.strip()[:160])
        except Exception:
            continue
    if hits:
        uniq = list(dict.fromkeys(hits))[:5]
        return CheckResult("error_logs", False, Severity.WARNING,
                           f"{len(hits)} error markers in recent logs: " + " | ".join(uniq),
                           "Investigate the most recent traceback in the logs. "
                           "Dispatch a coding agent to root-cause and patch.")
    return CheckResult("error_logs", True, Severity.INFO, "No fresh error markers in logs", "")


def check_disk(root: str, min_free_mb: int = 500) -> CheckResult:
    try:
        import shutil
        free = shutil.disk_usage(root).free / (1024 * 1024)
        if free < min_free_mb:
            return CheckResult("disk", False, Severity.WARNING,
                               f"Low disk: {free:.0f} MB free (< {min_free_mb} MB)",
                               "Free disk space; clean logs/archive or expand volume.")
        return CheckResult("disk", True, Severity.INFO, f"Disk OK: {free:.0f} MB free", "")
    except Exception as e:
        return CheckResult("disk", False, Severity.INFO, f"Disk check skipped: {e}", "")


def check_journal(root: str) -> CheckResult:
    """Trade observability guard.

    The live journal (data/qna_live.db, table `trades`) is created lazily by
    LiveEngine on first cycle. We only flag a problem when the system is
    ACTIVELY trading but cannot record itself (amnesiac), or the schema is
    broken. A merely-absent db with no open positions is EXPECTED (not a bug).
    """
    import sqlite3

    db_path = os.path.join(root, "data", "qna_live.db")
    if not os.path.exists(db_path):
        # Absent is fine UNLESS MT5 shows live open positions.
        try:
            import MetaTrader5 as mt5  # type: ignore
            if mt5.initialize():
                positions = mt5.positions_get() or []
                mt5.shutdown()
                if positions:
                    return CheckResult("journal", False, Severity.CRITICAL,
                                       f"Journal db missing BUT MT5 has {len(positions)} open positions — trades unrecorded",
                                       "Call LiveEngine() once to CREATE the journal, or ensure the "
                                       "production runner initializes the db before trading.")
        except Exception:
            pass
        return CheckResult("journal", True, Severity.INFO,
                           "Journal db not yet created (no cycle run) — acceptable", "")
    try:
        c = sqlite3.connect(db_path)
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        if "trades" not in tables:
            return CheckResult("journal", False, Severity.CRITICAL,
                               "Journal db exists but 'trades' table MISSING",
                               "Recreate the trades table via LiveEngine schema "
                               "(CREATE TABLE IF NOT EXISTS trades ...).")
        return CheckResult("journal", True, Severity.INFO, "Journal db present with 'trades' table", "")
    except Exception as e:
        return CheckResult("journal", False, Severity.WARNING,
                           f"Journal db unreadable: {e}", "Check file permissions / sqlite integrity.")


def all_checks(root: str) -> List[CheckResult]:
    return [
        check_api_health(),
        check_ui_canonical(),
        check_kill_switch(),
        check_strategy_registry(),
        check_mt5(),
        check_wiring(),
        check_journal(root),
        check_error_logs(root),
        check_disk(root),
    ]

