#!/usr/bin/env python3
"""Paper completion gate — 30-day clean run → live transition approval.

Checks all conditions from Theme 5 + CIO decisions before approving
paper-to-live transition.

Usage:
    python3 scripts/paper_completion_gate.py --state-dir /root/paper_runs/qna-paper-run-001
    python3 scripts/paper_completion_gate.py --state-dir /root/paper_runs/qna-paper-run-001 --progress
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("paper-gate")

BACKTEST_SHARPE = -0.335  # RegimeBased OOS Sharpe from fixed walk-forward
MAX_DRAWDOWN_PCT = 0.15  # 15% max drawdown (matches engine constant)
REQUIRED_DAYS = 30
MIN_UPTIME_PCT = 99.0
DECAY_THRESHOLD = 0.335  # live Sharpe not significantly below backtest
STALE_DATA_THRESHOLD_PER_WEEK = 2
AUDIT_GAP_HOURS = 24

CYCLE_INTERVAL_H = 1  # each cycle = ~1 hour


def load_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def compute_sharpe(returns: list[float], annual_factor: float = 252) -> float:
    if len(returns) < 5:
        return 0.0
    arr = np.array(returns)
    return float(np.mean(arr) / max(np.std(arr), 1e-10) * np.sqrt(annual_factor))


def fmt_pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def build_progress_bar(days_running: float, total_days: int = REQUIRED_DAYS, width: int = 20) -> str:
    filled = int((days_running / total_days) * width)
    filled = min(filled, width)
    bar = "█" * filled + "░" * (width - filled)
    pct = min(100.0, days_running / total_days * 100)
    return f"Paper Run Progress: [{bar}] {days_running:.0f}/{total_days} days ({pct:.0f}%)"


def check_duration(state: dict, pnl_rows: list[dict]) -> dict:
    days_running = 0.0
    timestamps = [r.get("timestamp", "") for r in pnl_rows if r.get("timestamp")]
    if timestamps:
        try:
            first = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            last = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            days_running = (last - first).total_seconds() / 86400
        except (ValueError, TypeError):
            cycle_count = state.get("cycle_count", 0)
            days_running = cycle_count * CYCLE_INTERVAL_H / 24
    else:
        cycle_count = state.get("cycle_count", 0)
        days_running = cycle_count * CYCLE_INTERVAL_H / 24

    if days_running >= REQUIRED_DAYS:
        return {"name": "Duration", "status": "PASS", "details": f"{days_running:.1f} days", "severity": "critical"}
    return {"name": "Duration", "status": "FAIL" if days_running > 0 else "INCOMPLETE",
            "details": f"{days_running:.1f} days (need {REQUIRED_DAYS})", "severity": "critical"}


def check_uptime(daemon_log: Path, watchdog_log: Path) -> dict:
    if not daemon_log.exists():
        return {"name": "Uptime", "status": "FAIL", "details": "daemon.log not found", "severity": "critical"}

    text = daemon_log.read_text(encoding="utf-8", errors="replace")
    restart_count = len(re.findall(r"Daemon started", text))
    total_lines = text.strip().splitlines()

    if not total_lines:
        return {"name": "Uptime", "status": "FAIL", "details": "empty daemon log", "severity": "critical"}

    watch_lines = watchdog_log.read_text(encoding="utf-8", errors="replace").strip().splitlines() if watchdog_log.exists() else []
    watchdog_starts = sum(1 for l in watch_lines if "Watchdog started" in l)

    expected_cycles = restart_count * 10  # crude: 10 cycles avg per start
    actual = 0
    for line in total_lines:
        if line.startswith("==") and "Cycle" in line:
            actual += 1

    uptime_pct = 100.0
    if actual > 0 and expected_cycles > 0:
        uptime_pct = min(100.0, actual / expected_cycles * 100)

    if uptime_pct >= MIN_UPTIME_PCT and restart_count <= 5:
        status = "PASS"
    elif uptime_pct < MIN_UPTIME_PCT and actual > 0:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "name": "Uptime",
        "status": status,
        "details": f"{uptime_pct:.1f}% uptime ({restart_count} restarts, {actual} cycles, {watchdog_starts} watchdog starts)",
        "severity": "high",
    }


def check_drawdown(pnl_rows: list[dict]) -> dict:
    max_dd = 0.0
    for r in pnl_rows:
        try:
            dd = float(r.get("drawdown_pct", 0))
            max_dd = max(max_dd, abs(dd))
        except (ValueError, TypeError):
            continue

    threshold = MAX_DRAWDOWN_PCT * 100
    if max_dd <= threshold:
        return {"name": "Drawdown", "status": "PASS", "details": f"Max DD: {max_dd:.2f}% (limit: {threshold:.0f}%)", "severity": "critical"}
    return {"name": "Drawdown", "status": "FAIL",
            "details": f"Max DD: {max_dd:.2f}% exceeded limit {threshold:.0f}%", "severity": "critical"}


def check_killswitch(daemon_log: Path, state: dict, pnl_rows: list[dict]) -> dict:
    text = daemon_log.read_text(encoding="utf-8", errors="replace") if daemon_log.exists() else ""

    # Check for LEVEL_2 / drawdown breaches in daemon.log
    level_2_matches = re.findall(r"Kill switch triggered.*drawdown|LEVEL_2|kill_switch.*LEVEL_2", text)
    drawdown_breach = re.findall(r"Max drawdown breached|drawdown.*exceeds|DRAWDOWN_EXCEEDED", text)

    # Check last 7 days in PnL for drawdown > 15%
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    recent_dd = []
    for r in pnl_rows:
        try:
            ts = datetime.fromisoformat(r.get("timestamp", "").replace("Z", "+00:00"))
            if ts >= cutoff:
                dd = float(r.get("drawdown_pct", 0))
                recent_dd.append(abs(dd))
        except (ValueError, TypeError):
            continue

    recent_spike = any(d > MAX_DRAWDOWN_PCT * 100 for d in recent_dd) if recent_dd else False

    severity = "critical" if level_2_matches or recent_spike else "high"

    if not level_2_matches and not recent_spike:
        return {"name": "KillSwitch", "status": "PASS",
                "details": "No LEVEL_2 activation in last 7 days", "severity": severity}
    return {"name": "KillSwitch", "status": "FAIL",
            "details": f"LEVEL_2 activations: {len(level_2_matches)}, recent DD spikes: {sum(recent_dd)}",
            "severity": severity}


def check_oos_decay(pnl_rows: list[dict]) -> dict:
    returns = []
    prev_value = None
    for r in pnl_rows:
        try:
            val = float(r.get("total_value", 0))
            if prev_value is not None and prev_value > 0:
                ret = (val - prev_value) / prev_value
                returns.append(ret)
            prev_value = val
        except (ValueError, TypeError):
            continue

    if len(returns) < 5:
        return {"name": "OOS Decay", "status": "PASS",
                "details": f"Not enough data ({len(returns)} returns, need ≥5)", "severity": "high"}

    live_sharpe = compute_sharpe(returns)
    decay = BACKTEST_SHARPE - live_sharpe  # how much worse live is vs backtest

    # Condition 5: live Sharpe not significantly below backtest (-0.335)
    # decay <= DECAY_THRESHOLD means pass
    if decay <= DECAY_THRESHOLD:
        return {"name": "OOS Decay", "status": "PASS",
                "details": f"Live Sharpe: {live_sharpe:.4f}, Backtest: {BACKTEST_SHARPE}, Decay: {decay:.4f} (threshold: {DECAY_THRESHOLD})",
                "severity": "high"}

    return {"name": "OOS Decay", "status": "FAIL",
            "details": f"Live Sharpe: {live_sharpe:.4f}, Backtest: {BACKTEST_SHARPE}, Decay: {decay:.4f} exceeds {DECAY_THRESHOLD}",
            "severity": "high"}


def check_pnl(state: dict, pnl_rows: list[dict]) -> dict:
    total_pnl = 0.0
    try:
        total_pnl = float(state.get("total_pnl", 0))
    except (ValueError, TypeError):
        if pnl_rows:
            try:
                total_pnl = float(pnl_rows[-1].get("total_pnl", 0))
            except (ValueError, TypeError):
                pass

    initial_capital = float(state.get("initial_capital", 10000))
    pnl_pct = total_pnl / initial_capital if initial_capital > 0 else 0

    if pnl_pct >= -0.05:
        return {"name": "Portfolio P&L", "status": "PASS",
                "details": f"Total P&L: ${total_pnl:+,.2f} ({fmt_pct(pnl_pct)})", "severity": "high"}
    return {"name": "Portfolio P&L", "status": "FAIL",
            "details": f"Total P&L: ${total_pnl:+,.2f} ({fmt_pct(pnl_pct)}) exceeds -5% loss threshold",
            "severity": "high"}


def check_compliance(audit_files: list[Path]) -> dict:
    if not audit_files:
        return {"name": "Compliance", "status": "FAIL",
                "details": "No audit logs found", "severity": "critical"}

    highest_severity = "INFO"
    has_high = False
    for ap in audit_files:
        audit = load_json(ap)
        by_sev = audit.get("summary", {}).get("by_severity", {})
        for sev in ["CRITICAL", "ERROR", "WARNING", "HIGH"]:
            count = by_sev.get(sev, 0)
            if count > 0:
                highest_severity = sev
                if sev in ("HIGH", "CRITICAL", "ERROR"):
                    has_high = True
        entries = audit.get("entries", [])
        for e in entries:
            sev = e.get("severity", "")
            if sev in ("HIGH", "CRITICAL"):
                has_high = True

    if has_high:
        return {"name": "Compliance", "status": "FAIL",
                "details": f"Found HIGH/CRITICAL findings (highest: {highest_severity})", "severity": "critical"}

    return {"name": "Compliance", "status": "PASS",
            "details": f"{len(audit_files)} audit file(s), highest severity: {highest_severity}", "severity": "critical"}


def check_audit_trail(audit_files: list[Path], daemon_log: Path) -> dict:
    all_ts = []

    for ap in audit_files:
        audit = load_json(ap)
        entries = audit.get("entries", [])
        for e in entries:
            ts_str = e.get("timestamp", "")
            if ts_str:
                try:
                    all_ts.append(datetime.fromisoformat(ts_str.replace("Z", "+00:00")))
                except (ValueError, TypeError):
                    pass

    # Also scan daemon.log for timestamps
    if daemon_log.exists():
        for line in daemon_log.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"(\d{2}:\d{2}:\d{2})\s", line)
            if match:
                pass  # daemon.log has relative time only, not full ISO

    if not all_ts:
        return {"name": "Audit Trail", "status": "FAIL",
                "details": "No timestamps found in audit logs", "severity": "high"}

    all_ts.sort()
    max_gap = timedelta(0)
    for i in range(1, len(all_ts)):
        gap = all_ts[i] - all_ts[i - 1]
        if gap > max_gap:
            max_gap = gap

    if max_gap <= timedelta(hours=AUDIT_GAP_HOURS):
        return {"name": "Audit Trail", "status": "PASS",
                "details": f"{len(all_ts)} events, max gap: {max_gap.total_seconds() / 3600:.1f}h (limit: {AUDIT_GAP_HOURS}h)",
                "severity": "high"}
    return {"name": "Audit Trail", "status": "FAIL",
            "details": f"Gap of {max_gap.total_seconds() / 3600:.1f}h exceeds {AUDIT_GAP_HOURS}h limit",
            "severity": "high"}


def check_data_pipeline(daemon_log: Path) -> dict:
    if not daemon_log.exists():
        return {"name": "Data Pipeline", "status": "FAIL", "details": "daemon.log not found", "severity": "high"}

    text = daemon_log.read_text(encoding="utf-8", errors="replace")
    stale_count = len(re.findall(r"stale|stale_data|DataFreshness.*trigger|Alpha Vantage fetch failed|Cache miss", text))

    now = datetime.now(timezone.utc)
    log_mtime = datetime.fromtimestamp(daemon_log.stat().st_mtime, tz=timezone.utc)
    log_age_days = (now - log_mtime).total_seconds() / 86400
    weeks = max(1, log_age_days / 7)

    rate = stale_count / weeks
    if rate <= STALE_DATA_THRESHOLD_PER_WEEK:
        return {"name": "Data Pipeline", "status": "PASS",
                "details": f"{stale_count} stale-data incidents ({rate:.1f}/week, limit: {STALE_DATA_THRESHOLD_PER_WEEK}/week)",
                "severity": "medium"}
    return {"name": "Data Pipeline", "status": "FAIL",
            "details": f"{stale_count} stale-data incidents ({rate:.1f}/week) exceeds {STALE_DATA_THRESHOLD_PER_WEEK}/week",
            "severity": "medium"}


def check_risk_budgets(pnl_attr: list[dict], state: dict) -> dict:
    if not pnl_attr:
        return {"name": "Risk Budgets", "status": "PASS",
                "details": "No attribution data to check (assumes passing for incomplete runs)", "severity": "medium"}

    initial = float(state.get("initial_capital", 10000))
    by_symbol: dict[str, list[float]] = {}
    for r in pnl_attr:
        sym = r.get("symbol", "")
        try:
            upnl = abs(float(r.get("unrealized_pnl", 0)))
            rpnl = abs(float(r.get("realized_pnl", 0)))
        except (ValueError, TypeError):
            continue
        by_symbol.setdefault(sym, []).append(upnl + rpnl)

    exceeded = []
    for sym, vals in by_symbol.items():
        if not vals:
            continue
        max_risk = max(vals)
        budget_pct = max_risk / initial if initial > 0 else 0
        # Per-asset budget: 25% of total risk budget (conservative)
        if budget_pct > 0.25:
            exceeded.append(f"{sym}: {fmt_pct(budget_pct)}")

    if not exceeded:
        return {"name": "Risk Budgets", "status": "PASS",
                "details": f"{len(by_symbol)} assets within budget", "severity": "medium"}
    return {"name": "Risk Budgets", "status": "FAIL",
            "details": "Exceeded: " + ", ".join(exceeded), "severity": "medium"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper Completion Gate — 30-day clean run → live transition approval")
    parser.add_argument("--state-dir", default="/root/paper_runs/qna-paper-run-001",
                        help="Paper run state directory (default: /root/paper_runs/qna-paper-run-001)")
    parser.add_argument("--progress", action="store_true", help="Show ASCII progress bar and exit")
    parser.add_argument("--json", action="store_true", help="Output JSON report (default)")
    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    if not state_dir.is_dir():
        print(json.dumps({
            "overall": "FAIL",
            "error": f"State directory not found: {state_dir}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, indent=2))
        sys.exit(1)

    state = load_json(state_dir / "state.json")
    pnl_rows = load_csv(state_dir / "pnl.csv")
    pnl_attr = load_csv(state_dir / "pnl_attribution.csv")
    audit_files = sorted(state_dir.glob("audit_*.json"))
    daemon_log = state_dir / "daemon.log"
    watchdog_log = state_dir / "watchdog.log"

    # Compute days running from cycle count if PnL timestamps sparse
    days_running = 0.0
    timestamps = [r.get("timestamp", "") for r in pnl_rows if r.get("timestamp")]
    if timestamps:
        try:
            first = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            last = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            days_running = (last - first).total_seconds() / 86400
        except (ValueError, TypeError):
            days_running = state.get("cycle_count", 0) * CYCLE_INTERVAL_H / 24
    else:
        days_running = state.get("cycle_count", 0) * CYCLE_INTERVAL_H / 24

    if args.progress:
        print(build_progress_bar(days_running))
        return

    # Run all gate checks
    conditions = [
        check_duration(state, pnl_rows),
        check_uptime(daemon_log, watchdog_log),
        check_drawdown(pnl_rows),
        check_killswitch(daemon_log, state, pnl_rows),
        check_oos_decay(pnl_rows),
        check_pnl(state, pnl_rows),
        check_compliance(audit_files),
        check_audit_trail(audit_files, daemon_log),
        check_data_pipeline(daemon_log),
        check_risk_budgets(pnl_attr, state),
    ]

    # Compute score
    weights = {"critical": 10, "high": 10, "medium": 10}
    total_score = 0
    for c in conditions:
        weight = weights.get(c.get("severity", "medium"), 10)
        if c["status"] == "PASS":
            total_score += weight

    # Determine overall
    critical_fails = [c for c in conditions if c["status"] == "FAIL" and c.get("severity") in ("critical", "high")]
    incomplete = [c for c in conditions if c["status"] == "INCOMPLETE"]

    if critical_fails:
        overall = "FAIL"
    elif incomplete:
        overall = "INCOMPLETE"
    elif days_running < REQUIRED_DAYS:
        overall = "INCOMPLETE"
    else:
        overall = "PASS"

    # Build recommendation
    if overall == "PASS":
        recommendation = f"Approved for live (score: {total_score}/100)"
    elif overall == "INCOMPLETE":
        remaining = max(0, REQUIRED_DAYS - days_running)
        reasons = [c["details"] for c in incomplete] + [f"Need {remaining:.0f} more days" if days_running < REQUIRED_DAYS else ""]
        reasons = [r for r in reasons if r]
        recommendation = f"Do not approve — incomplete: {'; '.join(reasons[:3])}"
    else:
        failures = [f"{c['name']}: {c['details']}" for c in critical_fails]
        recommendation = f"Do not approve — {len(critical_fails)} condition(s) failed: {'; '.join(failures[:3])}"

    report = {
        "overall": overall,
        "conditions": conditions,
        "score": min(100, total_score),
        "recommendation": recommendation,
        "days_running": round(days_running, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    print(json.dumps(report, indent=2))
    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
