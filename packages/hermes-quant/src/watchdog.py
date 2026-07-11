#!/usr/bin/env python3
"""
HERMES QUANT OS - Watchdog Daemon
===================================
Keeps Hermes Quant OS running 24/7 with:
- Automatic restart on crash
- Exponential backoff (5s → 10s → 20s → 40s → max 120s)
- Crash loop detection (max 10 restarts/hour)
- Health checks every 10 seconds
- Telegram alerts on crash/restart
- PID management
- Log rotation
"""

import os
import sys
import time
import signal
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent.parent.resolve()
HERMES_SCRIPT = BASE_DIR / "src" / "hermes_quant.py"
LOG_DIR = BASE_DIR / "logs"
PID_FILE = BASE_DIR / "hermes.pid"
WATCHDOG_PID_FILE = BASE_DIR / "watchdog.pid"
HEALTH_FILE = BASE_DIR / ".hermes" / "health.json"
CONFIG_ENV = BASE_DIR / "config" / ".env"

# Watchdog Parameters
CHECK_INTERVAL = 10        # seconds between health checks
MAX_RESTARTS_PER_HOUR = 10  # safety limit for crash loops
BASE_DELAY = 5             # initial restart delay
MAX_DELAY = 120            # maximum restart delay (exponential backoff cap)
HEALTH_TIMEOUT = 60        # seconds before considering process unresponsive

# Telegram (loaded from .env)
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""


def load_env():
    """Load environment variables from .env"""
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    if CONFIG_ENV.exists():
        with open(CONFIG_ENV) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key == "TELEGRAM_BOT_TOKEN":
                        TELEGRAM_BOT_TOKEN = value
                    elif key == "TELEGRAM_CHAT_ID":
                        TELEGRAM_CHAT_ID = value


def send_telegram(text):
    """Send Telegram alert"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        import urllib.request
        import urllib.error
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            pass
    except Exception:
        pass


class HermesWatchdog:
    """Watchdog daemon that keeps Hermes Quant OS alive"""

    def __init__(self):
        self.running = True
        self.restart_count = 0
        self.restart_history = []  # timestamps of recent restarts
        self.current_delay = BASE_DELAY
        self.last_crash = None
        self.hermes_pid = None
        self.start_count = 0

        # Setup directories
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / ".hermes").mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.log_file = LOG_DIR / f"watchdog_{datetime.now().strftime('%Y%m%d')}.log"

        # Save watchdog PID
        WATCHDOG_PID_FILE.write_text(str(os.getpid()))

        # Load env
        load_env()

    def log(self, msg, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {msg}"
        print(log_msg, flush=True)
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_msg + '\n')
        except Exception:
            pass

    def signal_handler(self, signum, frame):
        self.log(f"Watchdog received signal {signum}, shutting down...", "WARN")
        self.running = False

    def is_hermes_running(self):
        """Check if Hermes process is alive"""
        try:
            # Check PID file first
            if PID_FILE.exists():
                pid = int(PID_FILE.read_text().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    return True
                except (ProcessLookupError, OSError):
                    # PID file stale
                    PID_FILE.unlink(missing_ok=True)
                    return False

            # Fallback: check by process name
            result = subprocess.run(
                ['pgrep', '-f', 'hermes_quant.py'],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception as e:
            self.log(f"Error checking Hermes status: {e}", "ERROR")
            return False

    def get_hermes_pid(self):
        """Get Hermes process PID"""
        try:
            if PID_FILE.exists():
                return int(PID_FILE.read_text().strip())
            result = subprocess.run(
                ['pgrep', '-f', 'hermes_quant.py'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                return int(pids[0]) if pids else None
        except Exception:
            pass
        return None

    def calculate_backoff_delay(self):
        """Exponential backoff: 5 → 10 → 20 → 40 → 80 → 120 (cap)"""
        delay = min(BASE_DELAY * (2 ** min(self.restart_count, 6)), MAX_DELAY)
        return int(delay)

    def prune_restart_history(self):
        """Remove restarts older than 1 hour"""
        cutoff = datetime.now() - timedelta(hours=1)
        self.restart_history = [t for t in self.restart_history if t > cutoff]

    def check_crash_loop(self):
        """Check if we're in a crash loop"""
        self.prune_restart_history()
        return len(self.restart_history) >= MAX_RESTARTS_PER_HOUR

    def start_hermes(self):
        """Start Hermes Quant OS"""
        try:
            # Check crash loop limit
            if self.check_crash_loop():
                self.log(f"CRASH LOOP DETECTED: {len(self.restart_history)} restarts in last hour. "
                         f"Waiting 5 minutes...", "CRITICAL")
                send_telegram(
                    "HERMES QUANT OS - CRASH LOOP DETECTED\n\n"
                    f"Restarts: {len(self.restart_history)}/hour\n"
                    f"Cooling down for 5 minutes...\n"
                    f"Manual check recommended."
                )
                time.sleep(300)  # 5 min cooldown
                self.restart_history = []

            # Kill any existing Hermes processes
            subprocess.run(['pkill', '-f', 'hermes_quant.py'], capture_output=True)
            time.sleep(2)

            # Start Hermes
            self.log(f"Starting Hermes Quant OS... (attempt #{self.start_count + 1})")

            stdout_file = LOG_DIR / "stdout.log"

            with open(stdout_file, 'a') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Hermes Start: {datetime.now().isoformat()}\n")
                f.write(f"Watchdog Restart #: {self.start_count + 1}\n")
                f.write(f"{'='*50}\n")

            process = subprocess.Popen(
                [sys.executable, str(HERMES_SCRIPT)],
                stdout=open(stdout_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=str(BASE_DIR / "src"),
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )

            # Save PID
            self.hermes_pid = process.pid
            PID_FILE.write_text(str(process.pid))

            self.start_count += 1
            self.restart_count += 1
            self.restart_history.append(datetime.now())

            self.log(f"Hermes started with PID: {process.pid} "
                     f"(restart #{self.restart_count}, delay: {self.current_delay}s)")

            # Wait for initialization
            time.sleep(5)

            # Verify process started
            if self.is_hermes_running():
                # Reset backoff on successful start
                self.current_delay = BASE_DELAY
                return True
            else:
                self.log("Hermes failed to start properly!", "ERROR")
                return False

        except Exception as e:
            self.log(f"Failed to start Hermes: {e}", "ERROR")
            return False

    def update_health(self, status: str, details: dict = None):
        """Update health status file"""
        health = {
            "status": status,
            "hermes_pid": self.hermes_pid,
            "watchdog_pid": os.getpid(),
            "restart_count": self.restart_count,
            "start_count": self.start_count,
            "last_crash": str(self.last_crash) if self.last_crash else None,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        try:
            HEALTH_FILE.write_text(json.dumps(health, indent=2))
        except Exception:
            pass

    def rotate_logs(self):
        """Rotate log files older than 7 days"""
        try:
            cutoff = datetime.now() - timedelta(days=7)
            for log_path in LOG_DIR.glob("hermes_quant_*.log"):
                # Parse date from filename
                date_str = log_path.stem.split('_')[-1]
                try:
                    log_date = datetime.strptime(date_str, '%Y%m%d')
                    if log_date < cutoff:
                        log_path.unlink()
                except ValueError:
                    pass
        except Exception:
            pass

    def run(self):
        """Main watchdog loop"""
        self.log("=" * 60)
        self.log("HERMES QUANT OS WATCHDOG STARTED")
        self.log(f"Check Interval: {CHECK_INTERVAL}s")
        self.log(f"Max Restarts/Hour: {MAX_RESTARTS_PER_HOUR}")
        self.log(f"Backoff: {BASE_DELAY}s → {MAX_DELAY}s (exponential)")
        self.log(f"Hermes Script: {HERMES_SCRIPT}")
        self.log(f"PID File: {PID_FILE}")
        self.log("=" * 60)

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Initial start
        if not self.is_hermes_running():
            self.log("Hermes not running, starting...")
            if not self.start_hermes():
                self.log("Initial start failed! Retrying...", "ERROR")
                time.sleep(10)
                if not self.start_hermes():
                    self.log("FATAL: Cannot start Hermes!", "CRITICAL")
                    send_telegram("HERMES QUANT OS FATAL: Cannot start! Manual intervention required!")
                    # Don't exit - keep trying

        self.update_health("running")

        # Main loop
        while self.running:
            try:
                if self.is_hermes_running():
                    self.update_health("running", {"hermes_alive": True})

                    # Reset restart count on stable run (5 min uptime)
                    if self.restart_count > 0 and self.restart_history:
                        last_restart = self.restart_history[-1]
                        if datetime.now() - last_restart > timedelta(minutes=5):
                            self.restart_count = 0
                            self.current_delay = BASE_DELAY
                            self.log("Hermes stable for 5 min, reset restart counter")

                    time.sleep(CHECK_INTERVAL)
                else:
                    self.last_crash = datetime.now()
                    self.log("HERMES DIED! Initiating restart sequence...", "WARN")

                    # Calculate backoff
                    self.current_delay = self.calculate_backoff_delay()
                    self.log(f"Restart delay: {self.current_delay}s (exponential backoff)")

                    # Alert
                    send_telegram(
                        f"HERMES QUANT OS CRASHED\n\n"
                        f"Restart #{self.restart_count + 1}\n"
                        f"Delay: {self.current_delay}s\n"
                        f"Auto-restarting..."
                    )

                    # Wait with backoff
                    time.sleep(self.current_delay)

                    # Attempt restart
                    if self.start_hermes():
                        self.update_health("restarted", {"restart_reason": "crash"})
                        self.log("Hermes restarted successfully!")
                    else:
                        self.update_health("restart_failed")
                        self.log("Restart failed! Will retry next cycle.", "ERROR")

                # Rotate logs periodically
                if datetime.now().minute == 0:  # Every hour
                    self.rotate_logs()

            except Exception as e:
                self.log(f"Watchdog error: {e}", "ERROR")
                self.update_health("watchdog_error", {"error": str(e)})
                time.sleep(CHECK_INTERVAL)

        self.log("Watchdog stopped", "WARN")
        self.update_health("watchdog_stopped")
        WATCHDOG_PID_FILE.unlink(missing_ok=True)


def main():
    load_env()
    watchdog = HermesWatchdog()
    watchdog.run()


if __name__ == "__main__":
    main()
