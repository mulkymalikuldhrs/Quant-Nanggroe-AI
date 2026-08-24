"""QNA System Tray — Windows tray control for the Quant-Nanggroe-AI daemon.

Menu: Start/Stop daemon · Status · Open Dashboard/API · Quit.
Daemon lifecycle is managed via qna.py CLI in a child process; status comes
from the PID file written by the daemon itself.

Run:  python qna_tray.py
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
PID_FILE = PROJECT_ROOT / "data" / "daemons" / "qna-daemon.pid"
DASHBOARD_URL = os.environ.get("QNA_DASHBOARD_URL", "http://localhost:3000")
API_URL = os.environ.get("QNA_API_URL", "http://localhost:8000")

_daemon_proc: subprocess.Popen | None = None


def _daemon_running() -> bool:
    """Broker-truth check: PID file exists AND process alive."""
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)  # raises if dead (Windows: validates handle)
        return True
    except FileNotFoundError:
        pass
    except (ProcessLookupError, PermissionError, ValueError):
        pass
    # fall back to our own child process handle
    return _daemon_proc is not None and _daemon_proc.poll() is None


def _start_daemon() -> str:
    global _daemon_proc
    if _daemon_running():
        return "Daemon already running"
    env = dict(os.environ)
    env["PYTHONPATH"] = ""  # mandatory: Hermes venv leak guard
    _daemon_proc = subprocess.Popen(
        [PYTHON, str(PROJECT_ROOT / "qna.py"), "daemon"],
        cwd=str(PROJECT_ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return f"Daemon started (pid {_daemon_proc.pid})"


def _stop_daemon() -> str:
    global _daemon_proc
    stopped = False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        stopped = True
    except Exception:
        pass
    if not stopped and _daemon_proc is not None and _daemon_proc.poll() is None:
        _daemon_proc.terminate()
        stopped = True
    if not stopped:
        return "Daemon not running"
    # wait briefly for clean exit
    deadline = time.time() + 8
    while time.time() < deadline:
        if not _daemon_running():
            break
        time.sleep(0.5)
    else:
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
    _daemon_proc = None
    return "Daemon stopped"


# ── Tray UI ──────────────────────────────────────────────────────────────

def _make_image(running: bool):
    from PIL import Image, ImageDraw

    color = (16, 185, 129) if running else (239, 68, 68)  # emerald / red
    img = Image.new("RGB", (64, 64), (12, 17, 29))
    d = ImageDraw.Draw(img)
    d.ellipse([10, 10, 54, 54], fill=color)
    d.ellipse([24, 24, 40, 40], fill=(12, 17, 29))
    return img


def _menu_items(icon, item=None):
    import pystray

    running = _daemon_running()

    def _run(fn):
        def wrapper(icon_, item_):
            def job():
                fn()
                icon.update_menu()
            threading.Thread(target=job, daemon=True).start()
        return wrapper

    def _status(icon_, item_):
        pass  # dynamic text item

    def _open(url):
        def wrapper(icon_, item_):
            webbrowser.open(url)
        return wrapper

    def _quit(icon_, item_):
        icon.stop()

    yield pystray.MenuItem(
        lambda item: f"QNA v8.0.6 — {'RUNNING' if running else 'STOPPED'}",
        None, enabled=False)
    yield pystray.Menu.SEPARATOR
    if running:
        yield pystray.MenuItem("Stop Daemon", _run(_stop_daemon))
    else:
        yield pystray.MenuItem("Start Daemon", _run(_start_daemon))
    yield pystray.Menu.SEPARATOR
    yield pystray.MenuItem("Open Dashboard", _open(DASHBOARD_URL))
    yield pystray.MenuItem("Open API Docs", _open(f"{API_URL}/docs"))
    yield pystray.Menu.SEPARATOR
    yield pystray.MenuItem("Quit", _quit)


def main() -> int:
    import pystray

    icon = pystray.Icon(
        name="QuantNanggroeAI",
        icon=_make_image(False),
        title="Quant Nanggroe AI",
        menu=pystray.Menu(lambda icon, item: list(_menu_items(icon, item))),
    )

    def _icon_refresher():
        last = None
        while True:
            try:
                running = _daemon_running()
                if running != last:
                    last = running
                    icon.icon = _make_image(running)
                    icon.title = f"Quant Nanggroe AI — {'RUNNING' if running else 'STOPPED'}"
                    icon.update_menu()
            except Exception:
                pass
            time.sleep(3)

    threading.Thread(target=_icon_refresher, daemon=True).start()
    icon.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
