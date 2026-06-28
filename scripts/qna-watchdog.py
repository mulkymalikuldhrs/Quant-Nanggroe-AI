#!/usr/bin/env python3
"""qna-watchdog.py — Non-monetary auto-fix watchdog (~90 lines).

Approved per Theme 5 council decision:
- Restart daemon if crashed
- Rotate stale data cache
- Clear stuck PIDs
- Re-enable feed after cooldown

VETOED: any monetary auto-fix (position close, exposure reduce, trailing stop modify).
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("qna-watchdog")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DAEMON_SCRIPT = PROJECT_ROOT / "scripts" / "qna-paper-daemon.py"
STATE_DIR = Path("/root/paper_runs/qna-paper-run-001")
CACHE_DIR = PROJECT_ROOT / "data" / "cached_ohlcv"
COOLDOWN_FILE = STATE_DIR / ".feed_cooldown"
DECAY_CHECK_FILE = STATE_DIR / ".decay_check"
STALE_HOURS = 72
RESTART_COOLDOWN = 300
DECAY_CHECK_INTERVAL = 21600  # 6 hours


def daemon_pid() -> int | None:
    pid_file = STATE_DIR / "daemon.pid"
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError, ProcessLookupError):
        return None


def check_stuck_pids() -> None:
    for f in STATE_DIR.glob("*.pid"):
        try:
            pid = int(f.read_text().strip())
            os.kill(pid, 0)
            proc = Path(f"/proc/{pid}")
            if proc.exists():
                created = datetime.fromtimestamp(proc.stat().st_mtime, tz=timezone.utc)
                if (datetime.now(timezone.utc) - created) > timedelta(days=7):
                    os.kill(pid, 9)
                    f.unlink()
                    logger.warning("Cleared stuck PID %d (age >7d)", pid)
        except (ValueError, OSError, ProcessLookupError):
            f.unlink(missing_ok=True)


def check_data_staleness() -> bool:
    if not CACHE_DIR.exists():
        return False
    max_age = timedelta(hours=STALE_HOURS)
    now = datetime.now(timezone.utc)
    stale = False
    for f in sorted(CACHE_DIR.glob("*.csv")):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if (now - mtime) > max_age:
            logger.warning("Stale cache: %s (age %dh)", f.name, int((now - mtime).total_seconds() / 3600))
            stale = True
    return stale


def refresh_cache() -> bool:
    logger.info("Triggering cache refresh...")
    try:
        subprocess.run(
            [sys.executable, "-c", """
import requests, os, csv, sys
from datetime import datetime, timezone
key = os.environ.get("QNAI_ALPHA_VANTAGE_API_KEY", "QHZWJNDI1TNNLWV3")
symbols = {"BTC": "BTC", "ETH": "ETH", "SOL": "SOL", "XRP": "XRP"}
base = "/sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/data/cached_ohlcv"
for sym, av_sym in symbols.items():
    url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={av_sym}&market=USD&apikey={key}"
    try:
        resp = requests.get(url, timeout=10).json()
        ts = resp.get("Meta Data", {}).get("3. Last Refreshed", "")
        series = resp.get("Time Series (Digital Currency Daily)", {})
        if not series:
            sys.stderr.write(f"No data for {sym}\\n")
            continue
        path = f"{base}/{sym}.csv"
        exists = os.path.exists(path)
        rows = []
        if exists:
            with open(path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        existing_dates = {r["date"] for r in rows}
        new_count = 0
        for date, vals in sorted(series.items()):
            if date not in existing_dates:
                rows.append({"date": date, "open": vals["1a. open (USD)"],
                             "high": vals["2a. high (USD)"], "low": vals["3a. low (USD)"],
                             "close": vals["4a. close (USD)"], "volume": vals["5. volume"]})
                new_count += 1
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date","open","high","low","close","volume"])
            w.writeheader()
            w.writerows(rows)
        sys.stderr.write(f"{sym}: {new_count} new rows\\n")
    except Exception as e:
        sys.stderr.write(f"{sym} failed: {e}\\n")
"""],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
        )
        return True
    except Exception as e:
        logger.error("Cache refresh failed: %s", e)
        return False


def restart_daemon() -> None:
    launcher = Path("/root/start_paper_run.py")
    if launcher.exists():
        logger.info("Restarting daemon...")
        subprocess.run([sys.executable, str(launcher)], capture_output=True, timeout=30)


def run() -> None:
    logger.info("Watchdog started")
    while True:
        pid = daemon_pid()
        if pid is None:
            logger.warning("Daemon not running — restarting")
            restart_daemon()
        else:
            logger.debug("Daemon running: PID %d", pid)

        check_stuck_pids()

        if check_data_staleness():
            cooldown = COOLDOWN_FILE.stat().st_mtime if COOLDOWN_FILE.exists() else 0
            if time.time() - cooldown > RESTART_COOLDOWN:
                if refresh_cache():
                    COOLDOWN_FILE.write_text(str(time.time()))
            else:
                logger.info("Cache refresh cooldown active")

        dc_time = DECAY_CHECK_FILE.stat().st_mtime if DECAY_CHECK_FILE.exists() else 0
        if time.time() - dc_time > DECAY_CHECK_INTERVAL:
            pnl_csv = STATE_DIR / "pnl.csv"
            if pnl_csv.exists():
                try:
                    result = subprocess.run(
                        [sys.executable, str(PROJECT_ROOT / "scripts" / "oos_decay_tracker.py"),
                         "--pnl-csv", str(pnl_csv), "--json"],
                        capture_output=True, text=True, timeout=30,
                    )
                    if result.returncode == 0:
                        logger.info("OOS Decay: %s", result.stdout.strip())
                        DECAY_CHECK_FILE.write_text(str(time.time()))
                except Exception as e:
                    logger.debug("OOS decay check failed: %s", e)

        time.sleep(300)


if __name__ == "__main__":
    run()
