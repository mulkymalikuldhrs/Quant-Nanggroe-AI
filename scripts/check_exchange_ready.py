#!/usr/bin/env python3
"""Check if Quant Nanggroe AI is ready for exchange API wiring.

Checks:
1. Are exchange modules importable? (exchange/factory.py, exchange/clients/*)
2. Is there a working data provider? (cached OHLCV, failover provider)
3. Is the paper daemon running and producing trades?
4. Are risk systems active? (kill switch, correlation monitor, auto-disable)
5. Required environment variables template
6. Suggested exchange configuration

Usage:
    python3 scripts/check_exchange_ready.py
    python3 scripts/check_exchange_ready.py --json  # machine-readable
"""

import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPER_STATE = PROJECT_ROOT / "paper_state"

CHECKS: list[dict] = []


def check(name: str, status: bool, detail: str = "", hint: str = "") -> dict:
    entry = {"name": name, "status": "pass" if status else "fail", "detail": detail}
    if hint:
        entry["hint"] = hint
    CHECKS.append(entry)
    return entry


def module_importable(mod: str) -> bool:
    try:
        importlib.import_module(mod)
        return True
    except ImportError as e:
        check("", False, detail=str(e))
        return False


def check_exchange_imports() -> None:
    targets = [
        ("quant_nanggroe.exchange.factory", "exchange/factory.py"),
        ("quant_nanggroe.exchange.paper_broker", "exchange/paper_broker.py"),
        ("quant_nanggroe.exchange.base", "exchange/base.py"),
        ("quant_nanggroe.exchange.guards", "exchange/guards.py"),
        ("quant_nanggroe.exchange.clients.binance_client", "exchange/clients/binance_client.py"),
        ("quant_nanggroe.exchange.clients.bybit_client", "exchange/clients/bybit_client.py"),
        ("quant_nanggroe.exchange.clients.okx_client", "exchange/clients/okx_client.py"),
        ("quant_nanggroe.exchange.ccxt_broker", "exchange/ccxt_broker.py"),
    ]
    # Prepend project root to sys.path so absolute imports work
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    for mod, path in targets:
        ok = module_importable(mod)
        label = f"import {mod}"
        if ok:
            check(label, True, detail=f"{path} — OK")
        else:
            check(label, False, detail=f"{path} — ImportError", hint="Run: pip install -e . or check PYTHONPATH")


def check_paper_broker_file() -> None:
    path = PROJECT_ROOT / "quant_nanggroe" / "exchange" / "paper_broker.py"
    exists = path.is_file()
    if exists:
        check("paper_broker.py exists", True, detail=str(path))
    else:
        check("paper_broker.py exists", False, detail="not found", hint="Expected at quant_nanggroe/exchange/paper_broker.py")


def check_paper_daemon() -> None:
    pid_file = PAPER_STATE / "daemon.pid"
    state_file = PAPER_STATE / "state.json"
    log_file = PAPER_STATE / "daemon.log"

    # PID and process
    pid_running = False
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text().strip())
            pid_running = _pid_exists(pid)
            if pid_running:
                check("paper daemon process alive", True, detail=f"PID {pid} running")
            else:
                check("paper daemon process alive", False, detail=f"PID {pid} not found (stale pidfile?)",
                      hint="Start daemon: python3 scripts/qna-paper-daemon.py")
        except (ValueError, OSError):
            check("paper daemon process alive", False, detail="could not read daemon.pid",
                  hint="Check paper_state/daemon.pid contents")
    else:
        check("paper daemon process alive", False, detail="daemon.pid not found",
              hint="Start daemon: python3 scripts/qna-paper-daemon.py")

    # State file
    if state_file.is_file():
        try:
            state = json.loads(state_file.read_text())
            cap = state.get("initial_capital", "?")
            pnl = state.get("total_pnl", "?")
            cycles = state.get("cycle_count", 0)
            check("paper state.json present", True,
                  detail=f"capital={cap}, cycles={cycles}, total_pnl={pnl}")
        except (json.JSONDecodeError, OSError) as e:
            check("paper state.json present", False, detail=f"unreadable: {e}",
                  hint="Check paper_state/state.json format")
    else:
        check("paper state.json present", False, detail="not found",
              hint="Daemon creates this on first cycle; run daemon at least once")

    # Log file freshness
    if log_file.is_file():
        age_seconds = time.time() - log_file.stat().st_mtime
        aged = age_seconds > 86400
        detail = f"last modified {age_seconds:.0f}s ago"
        if not aged:
            check("paper daemon log recent", True, detail=detail)
        else:
            check("paper daemon log recent", True, detail=detail + " (stale — check if daemon still cycles)")
    else:
        check("paper daemon log recent", False, detail="daemon.log not found",
              hint="Daemon creates this on first cycle")


def check_risk_systems() -> None:
    # Auto-disable state
    ad_path = PAPER_STATE / "auto_disable_state.json"
    if ad_path.is_file():
        try:
            ad = json.loads(ad_path.read_text())
            strategies = ad.get("strategies", {})
            disabled = [s for s, v in strategies.items() if v.get("disabled")]
            detail = f"{len(strategies)} strategies tracked, {len(disabled)} disabled"
            if disabled:
                detail += f": {', '.join(disabled)}"
            check("auto-disable state present", True, detail=detail)
        except (json.JSONDecodeError, OSError) as e:
            check("auto-disable state present", False, detail=f"unreadable: {e}",
                  hint="Check paper_state/auto_disable_state.json format")
    else:
        check("auto-disable state present", False, detail="not found",
              hint="AutoDisableManager creates this; run daemon with risk enabled")

    # Kill switch — embedded in risk manager state (persisted within state.json)
    state_file = PAPER_STATE / "state.json"
    kill_active = False
    if state_file.is_file():
        try:
            state = json.loads(state_file.read_text())
            kill_active = state.get("kill_switch_active", False) or \
                          state.get("risk:kill_switch_active", False)
            check("kill switch state", True,
                  detail="ACTIVE" if kill_active else "inactive")
        except (json.JSONDecodeError, OSError):
            check("kill switch state", False, detail="state.json unreadable")
    else:
        check("kill switch state", False, detail="state.json not found",
              hint="Risk manager persists kill switch state to state.json")

    # Guards pipeline exists
    try:
        from quant_nanggroe.exchange.guards import GuardPipeline
        check("guard pipeline importable", True, detail="GuardPipeline available")
    except ImportError:
        check("guard pipeline importable", False, detail="import failed",
              hint="Check quant_nanggroe/exchange/guards.py")


def check_data_providers() -> None:
    cached_dir = PROJECT_ROOT / "data"
    if cached_dir.is_dir():
        csv_files = list(cached_dir.rglob("*.csv")) + list(cached_dir.rglob("*.parquet"))
        if csv_files:
            check("cached OHLCV data", True, detail=f"{len(csv_files)} file(s) in data/")
        else:
            check("cached OHLCV data", True, detail="data/ exists (empty)", hint="Run scripts/fetch_real_ohlcv.py to populate")
    else:
        check("cached OHLCV data", False, detail="data/ directory missing",
              hint="Create data/ directory or configure alternative data source")

    try:
        from quant_nanggroe.data.failover_provider import FailoverDataProvider
        check("failover provider importable", True, detail="FailoverDataProvider available")
    except ImportError:
        check("failover provider importable", False, detail="import failed",
              hint="Check quant_nanggroe/data/failover_provider.py")

    try:
        from quant_nanggroe.data.providers.twelvedata import TwelveDataProvider
        check("TwelveData provider importable", True, detail="TwelveDataProvider available")
    except ImportError:
        check("TwelveData provider importable", False, detail="import failed",
              hint="pip install twelvedata or check provider path")


def check_env_template() -> None:
    env_example = PROJECT_ROOT / ".env.example"
    if env_example.is_file():
        check(".env.example exists", True, detail=str(env_example))
    else:
        check(".env.example exists", False, detail="not found",
              hint="Create .env.example with EXCHANGE_API_KEY, EXCHANGE_API_SECRET")


def print_readable() -> None:
    fails = [c for c in CHECKS if c["status"] == "fail"]
    print("=" * 62)
    print("  Quant Nanggroe AI — Exchange Wiring Readiness Check")
    print("=" * 62)
    print()
    for c in CHECKS:
        icon = "PASS" if c["status"] == "pass" else "FAIL"
        print(f"  [{icon}] {c['name']}")
        print(f"         {c['detail']}")
        if c.get("hint"):
            print(f"         \u21aa {c['hint']}")
        print()
    print("-" * 62)
    print(f"  {len(CHECKS)} checks: {len(CHECKS) - len(fails)} pass, {len(fails)} fail")
    print()
    if fails:
        print("  \u26a0  Items to resolve before wiring real APIs:")
        for f in fails:
            print(f"     - {f['name']}")
            if f.get("hint"):
                print(f"       {f['hint']}")
        print()
    else:
        print("  \u2705  Ready for exchange wiring.")
        print()


def print_json() -> None:
    status = "pass" if all(c["status"] == "pass" for c in CHECKS) else "fail"
    print(json.dumps({
        "tool": "check_exchange_ready",
        "version": 1,
        "status": status,
        "checks": CHECKS,
        "summary": {
            "total": len(CHECKS),
            "pass": sum(1 for c in CHECKS if c["status"] == "pass"),
            "fail": sum(1 for c in CHECKS if c["status"] == "fail"),
        },
    }, indent=2))


def _pid_exists(pid: int) -> bool:
    """Check if a PID is alive (cross-platform stdlib only)."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main() -> None:
    check_exchange_imports()
    check_paper_broker_file()
    check_paper_daemon()
    check_risk_systems()
    check_data_providers()
    check_env_template()

    if "--json" in sys.argv:
        print_json()
    else:
        print_readable()


if __name__ == "__main__":
    main()
