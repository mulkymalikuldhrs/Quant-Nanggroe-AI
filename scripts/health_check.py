#!/usr/bin/env python3
"""QNA Health Check — reports state of all major system components."""

import csv
import json
import os
import subprocess
import sys

PAPER_STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paper_state")
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")

errors = []


def ok(label, detail):
    print(f"  {label:16s} \u2705 {detail}")


def fail(label, detail):
    print(f"  {label:16s} \u274c {detail}")
    errors.append(label)


def check_daemon():
    pid_path = os.path.join(PAPER_STATE, "daemon.pid")
    if not os.path.isfile(pid_path):
        fail("Daemon", "daemon.pid not found")
        return
    try:
        with open(pid_path) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
    except (ValueError, OSError):
        fail("Daemon", f"PID {pid} not running (stale pidfile?)")
        return
    cycles = 0
    state_path = os.path.join(PAPER_STATE, "state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path) as f:
                state = json.load(f)
                cycles = state.get("cycle_count", 0)
        except (json.JSONDecodeError, OSError):
            pass
    ok("Daemon", f"PID {pid} ({cycles} cycles)")


def check_pnl():
    pnl_path = os.path.join(PAPER_STATE, "pnl.csv")
    if not os.path.isfile(pnl_path):
        fail("PnL data", "pnl.csv not found")
        return
    try:
        with open(pnl_path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if len(rows) < 2:
            fail("PnL data", "pnl.csv has header only, no data rows")
            return
        last_row = rows[-1]
        total_idx = rows[0].index("total_pnl")
        total_pnl = float(last_row[total_idx])
        ok("PnL data", f"{len(rows) - 1} rows, ${total_pnl:+,.2f} PnL")
    except (OSError, csv.Error, ValueError, IndexError) as e:
        fail("PnL data", str(e))


def check_dashboard():
    dash_path = os.path.join(DASHBOARD_DIR, "qnai_dashboard.html")
    if not os.path.isfile(dash_path):
        fail("Dashboard", "qnai_dashboard.html not found")
        return
    try:
        with open(dash_path) as f:
            lines = f.readlines()
        ok("Dashboard", f"qnai_dashboard.html ({len(lines)} lines)")
    except OSError as e:
        fail("Dashboard", str(e))


def check_test_runner():
    runner_path = os.path.join(SCRIPTS_DIR, "test_runner.py")
    if not os.path.isfile(runner_path):
        fail("Test runner", "test_runner.py not found")
        return
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", runner_path],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        ok("Test runner", "syntax OK")
    else:
        fail("Test runner", f"syntax error: {result.stderr.strip()}")


def check_exchange_prep():
    ex_path = os.path.join(SCRIPTS_DIR, "check_exchange_ready.py")
    if os.path.isfile(ex_path):
        ok("Exchange prep", "check_exchange_ready.py exists")
    else:
        fail("Exchange prep", "check_exchange_ready.py not found")


def check_state_files():
    if not os.path.isdir(PAPER_STATE):
        fail("State files", "paper_state/ directory not found")
        return
    files = [f for f in os.listdir(PAPER_STATE) if os.path.isfile(os.path.join(PAPER_STATE, f))]
    ok("State files", f"{len(files)} files in paper_state/")


def main():
    print("\u2554\u2550\u2550 QNA Health Check \u2550\u2550\u2550\u2557")
    check_daemon()
    check_pnl()
    check_dashboard()
    check_test_runner()
    check_exchange_prep()
    check_state_files()
    total = 6
    passed = total - len(errors)
    status = "\u2705" if passed == total else "\u274c"
    print(f"\u255a\u2550\u2550 ALL SYSTEMS: {passed}/{total} {status} \u2550\u2550\u255d")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
