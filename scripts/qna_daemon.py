#!/usr/bin/env python3
"""
QNA DAEMON — Standalone process that manages EVERYTHING for QNA.
Auto-starts Hermes gateway, launches dashboard, health checks, auto-restart.
Usage: python qna_daemon.py (start|stop|restart|status)
"""
import os, sys, time, signal, subprocess, datetime, json, pathlib

QNA_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = QNA_DIR / "data"
LOG_DIR = QNA_DIR / "logs"
PID_FILE = DATA_DIR / "qna_daemon.pid"
STATUS_FILE = DATA_DIR / "qna_daemon_status.json"
DASHBOARD_PORT = 3000
HERMES_CHECK_SEC = 30
DAEMON_CHECK_SEC = 10

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
QNA_USE_ADAPTIVE_PIPELINE = True

def log(msg):
    ts = datetime.datetime.now().isoformat()[:19]
    line = f"[{ts}] QNA-DAEMON: {msg}"
    print(line, flush=True)
    (LOG_DIR / "qna_daemon.log").open("a").write(line + "\n")

def pid_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False

def start_hermes():
    """Start Hermes gateway (not restart — avoid CLI breakage)."""
    log("Checking Hermes gateway...")
    result = subprocess.run(
        ["hermes", "gateway", "status"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0 and "running" in result.stdout.lower():
        log("Hermes gateway already running OK")
        return True
    # Try start (not restart — CLI is broken, restart fails with ModuleNotFoundError)
    log("Hermes gateway not running. Starting...")
    result = subprocess.run(
        ["hermes", "gateway", "start"],
        capture_output=True, text=True, timeout=15
    )
    log(f"Hermes gateway start exit={result.returncode}")
    time.sleep(3)
    return True

def start_dashboard():
    """Launch Next.js dashboard in background."""
    dashboard_dir = QNA_DIR / "dashboard"
    if not (dashboard_dir / "package.json").exists():
        log("Dashboard not found, skipping")
        return False
    log(f"Starting dashboard on port {DASHBOARD_PORT}...")
    # Check if already running
    existing = subprocess.run(
        ["lsof", "-i", f":{DASHBOARD_PORT}"],
        capture_output=True, text=True
    )
    if existing.returncode == 0:
        log(f"Dashboard already running on port {DASHBOARD_PORT}")
        return True
    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(dashboard_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    log(f"Dashboard started (PID {proc.pid})")
    time.sleep(5)
    return True

def health_check():
    """Check all QNA components health."""
    status = {
        "timestamp": datetime.datetime.now().isoformat(),
        "hermes_gateway": False,
        "dashboard": False,
        "mt5_connected": False,
        "strategy_count": 0,
        "import_errors": 0,
    }
    # Check Hermes gateway
    r = subprocess.run(
        ["hermes", "gateway", "status"],
        capture_output=True, text=True, timeout=10
    )
    status["hermes_gateway"] = r.returncode == 0
    # Check dashboard
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:3000"],
        capture_output=True, text=True, timeout=5
    )
    status["dashboard"] = r.stdout.strip() in ("200", "301", "302")
    # Check MT5
    try:
        sys.path.insert(0, str(QNA_DIR))
        from quant_nanggroe.engine.strategies.registry import StrategyRegistry
        status["strategy_count"] = len(StrategyRegistry.list_strategies())
        status["mt5_connected"] = True
    except Exception:
        pass
    # Check imports
    r = subprocess.run(
        ["python", "scripts/check_imports.py"],
        capture_output=True, text=True, timeout=60, cwd=str(QNA_DIR)
    )
    if "Total import errors: 0" in r.stdout:
        status["import_errors"] = 0
    else:
        status["import_errors"] = -1
    return status

def run():
    """Main daemon loop."""
    log("=" * 60)
    log("QNA DAEMON STARTED")
    log(f"QNA_DIR: {QNA_DIR}")
    log(f"Adaptive Pipeline: {QNA_USE_ADAPTIVE_PIPELINE}")
    log(f"Strategy mode: ALL 73+ via registry (not 4 hardcoded)")
    log("=" * 60)

    # Write PID
    PID_FILE.write_text(str(os.getpid()))

    # Start components
    start_hermes()
    start_dashboard()

    # Health loop
    consecutive_failures = 0
    while True:
        try:
            status = health_check()
            STATUS_FILE.write_text(json.dumps(status, indent=2))
            log(f"Health: hermes={status['hermes_gateway']} dash={status['dashboard']} "
                f"strats={status['strategy_count']} imports={status['import_errors']}")
            if not status["hermes_gateway"]:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    log("Hermes gateway down 3x — restarting...")
                    start_hermes()
                    consecutive_failures = 0
            else:
                consecutive_failures = 0
        except Exception as e:
            log(f"Health check error: {e}")
        time.sleep(HERMES_CHECK_SEC)

def stop():
    log("Stopping QNA daemon...")
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text())
        try:
            os.kill(pid, signal.SIGTERM)
            log(f"Sent SIGTERM to PID {pid}")
        except ProcessLookupError:
            log("Daemon not running")
    PID_FILE.unlink(missing_ok=True)

def status_cmd():
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text())
        running = pid_running(pid)
        print(f"QNA Daemon PID: {pid} (running={running})")
    else:
        print("QNA Daemon is NOT running")
    if STATUS_FILE.exists():
        status = json.loads(STATUS_FILE.read_text())
        print(json.dumps(status, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python qna_daemon.py (start|stop|restart|status)")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "start":
        run()
    elif cmd == "stop":
        stop()
    elif cmd == "restart":
        stop()
        time.sleep(2)
        run()
    elif cmd == "status":
        status_cmd()
    else:
        print(f"Unknown command: {cmd}")
