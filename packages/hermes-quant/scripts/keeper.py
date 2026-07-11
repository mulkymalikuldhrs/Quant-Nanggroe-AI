#!/usr/bin/env python3
"""
HERMES QUANT OS - Keeper Daemon
================================
Cron-friendly health check + auto-restart.
Runs every minute via cron or Termux:Boot.
Lighter than watchdog - no persistent process needed.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
HERMES_SCRIPT = BASE_DIR / "src" / "hermes_quant.py"
WATCHDOG_SCRIPT = BASE_DIR / "src" / "watchdog.py"
PID_FILE = BASE_DIR / "hermes.pid"
WATCHDOG_PID_FILE = BASE_DIR / "watchdog.pid"
LOG_DIR = BASE_DIR / "logs"
CONFIG_ENV = BASE_DIR / "config" / ".env"

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"keeper_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] [{level}] {msg}"
    print(line, flush=True)
    with open(log_file, 'a') as f:
        f.write(line + '\n')


def is_process_running(pid_file, process_pattern):
    """Check if a process is running"""
    # Check PID file
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, OSError, ValueError):
            pid_file.unlink(missing_ok=True)

    # Fallback: check by process name
    result = subprocess.run(['pgrep', '-f', process_pattern],
                           capture_output=True, text=True)
    return result.returncode == 0


def start_watchdog():
    """Start the watchdog daemon"""
    log("Starting watchdog daemon...")
    subprocess.Popen(
        [sys.executable, str(WATCHDOG_SCRIPT)],
        stdout=open(LOG_DIR / "watchdog_stdout.log", 'a'),
        stderr=subprocess.STDOUT,
        cwd=str(BASE_DIR / "src"),
        start_new_session=True
    )
    log("Watchdog daemon started")


def start_hermes_direct():
    """Start Hermes directly (fallback if no watchdog)"""
    log("Starting Hermes Quant OS directly...")
    subprocess.Popen(
        [sys.executable, str(HERMES_SCRIPT)],
        stdout=open(LOG_DIR / "stdout.log", 'a'),
        stderr=subprocess.STDOUT,
        cwd=str(BASE_DIR / "src"),
        start_new_session=True
    )
    log("Hermes started")


def main():
    log("=" * 40)
    log("HERMES KEEPER CHECK")
    log("=" * 40)

    # Check if watchdog is running
    watchdog_running = is_process_running(WATCHDOG_PID_FILE, "watchdog.py")
    hermes_running = is_process_running(PID_FILE, "hermes_quant.py")

    log(f"Watchdog: {'RUNNING' if watchdog_running else 'NOT RUNNING'}")
    log(f"Hermes: {'RUNNING' if hermes_running else 'NOT RUNNING'}")

    if not watchdog_running:
        log("Watchdog not running! Starting watchdog...")
        start_watchdog()
        time.sleep(3)

        # Verify watchdog started
        if is_process_running(WATCHDOG_PID_FILE, "watchdog.py"):
            log("Watchdog started successfully!")
        else:
            log("Watchdog failed to start! Starting Hermes directly...", "WARN")
            if not hermes_running:
                start_hermes_direct()

    elif not hermes_running:
        log("Watchdog running but Hermes not detected. Watchdog should auto-restart.")
        # Don't double-start - let watchdog handle it

    else:
        log("All systems operational. Hermes Quant OS is eternal.")

    log("Keeper check complete.")



if __name__ == "__main__":
    main()
