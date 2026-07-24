"""
QNA Full Stack Launcher — starts everything:
1. Hermes Free Model Proxy (port 8420)
2. QNA FastAPI server (port 8000)
3. Pipeline Scheduler (auto-triggers every N minutes)
4. Ensemble voting (enabled by default)

Usage:
    python launch_full.py                    # paper mode
    python launch_full.py --live             # live MT5 trading
    python launch_full.py --interval 5       # custom scheduler interval
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROXY_SCRIPT = ROOT.parent / "Obsidian" / "DhaherLabs" / "_scripts" / "hermes_proxy.py"
QNA_ENTRY = ROOT / "qna.py"
ENV_FILE = ROOT / ".env"


def load_env():
    """Load .env file into os.environ."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def start_proxy(port: int = 8420) -> subprocess.Popen | None:
    """Start the Hermes free model proxy."""
    script = PROXY_SCRIPT if PROXY_SCRIPT.exists() else ROOT / "_scripts" / "hermes_proxy.py"
    if not script.exists():
        print(f"[WARN] Proxy script not found at {script}, skipping")
        return None

    print(f"[LAUNCH] Starting Hermes Proxy on port {port}...")
    proc = subprocess.Popen(
        [sys.executable, str(script), str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    time.sleep(2)
    if proc.poll() is None:
        print(f"[OK] Hermes Proxy running (PID={proc.pid})")
        return proc
    print("[WARN] Hermes Proxy failed to start")
    return None


def start_qna_server(live: bool = False) -> subprocess.Popen | None:
    """Start the QNA FastAPI server."""
    env = os.environ.copy()
    if live:
        env["QNA_LIVE_TRADING"] = "1"
        print("[WARN] LIVE TRADING MODE ENABLED")

    print("[LAUNCH] Starting QNA API server on port 8000...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "quant_nanggroe.api.app:create_app",
         "--factory", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    time.sleep(3)
    if proc.poll() is None:
        print(f"[OK] QNA Server running (PID={proc.pid})")
        return proc
    print("[WARN] QNA Server failed to start — check logs")
    return proc


def start_scheduler(interval: int = 15) -> None:
    """Start the pipeline scheduler in-process."""
    print(f"[LAUNCH] Starting Scheduler (interval={interval}min)...")
    try:
        from quant_nanggroe.engine.scheduler import PipelineScheduler
        scheduler = PipelineScheduler(interval_minutes=interval)
        scheduler.start()
        print(f"[OK] Scheduler running (every {interval} min)")
        return scheduler
    except Exception as e:
        print(f"[WARN] Scheduler failed: {e}")
        return None


def print_status(procs: dict, scheduler=None):
    """Print current status."""
    print("\n" + "=" * 60)
    print("  QNA FULL STACK STATUS")
    print("=" * 60)
    for name, proc in procs.items():
        if proc is None:
            status = "SKIPPED"
        elif proc.poll() is None:
            status = f"RUNNING (PID={proc.pid})"
        else:
            status = f"STOPPED (exit={proc.returncode})"
        print(f"  {name:20s} {status}")
    if scheduler:
        print(f"  {'Scheduler':20s} {'RUNNING' if scheduler.is_running else 'STOPPED'}")
    print(f"\n  API:       http://127.0.0.1:8000/docs")
    print(f"  Proxy:     http://127.0.0.1:8420/v1/models")
    print(f"  Ensemble:  POST http://127.0.0.1:8000/api/ensemble/vote")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="QNA Full Stack Launcher")
    parser.add_argument("--live", action="store_true", help="Enable live MT5 trading")
    parser.add_argument("--interval", type=int, default=15, help="Scheduler interval in minutes")
    parser.add_argument("--proxy-port", type=int, default=8420, help="Hermes proxy port")
    parser.add_argument("--no-proxy", action="store_true", help="Skip proxy startup")
    parser.add_argument("--no-scheduler", action="store_true", help="Skip scheduler startup")
    args = parser.parse_args()

    load_env()
    os.environ["QNA_SCHEDULER_ENABLED"] = "1"

    print("=" * 60)
    print("  QNA — Quant Nanggroe AI v5.1.0")
    print("  Autonomous Hedge Fund with Ensemble Voting")
    print("=" * 60)

    procs = {}

    # 1. Start proxy
    if not args.no_proxy:
        procs["Hermes Proxy"] = start_proxy(args.proxy_port)

    # 2. Start QNA server
    procs["QNA Server"] = start_qna_server(args.live)

    # 3. Start scheduler
    scheduler = None
    if not args.no_scheduler:
        scheduler = start_scheduler(args.interval)

    # Print status
    print_status(procs, scheduler)

    # Wait for interrupt
    def shutdown(sig=None, frame=None):
        print("\n[SHUTDOWN] Stopping all services...")
        for name, proc in procs.items():
            if proc and proc.poll() is None:
                print(f"  Stopping {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if scheduler:
            scheduler.stop()
        print("[OK] All services stopped")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("\n[READY] Press Ctrl+C to stop all services")
    try:
        while True:
            time.sleep(10)
            # Check if any process died
            for name, proc in procs.items():
                if proc and proc.poll() is not None and name != "QNA Server":
                    print(f"[WARN] {name} died (exit={proc.returncode}) — restarting...")
                    if name == "Hermes Proxy":
                        procs[name] = start_proxy(args.proxy_port)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
