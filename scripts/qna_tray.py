"""QNA System Tray — online/offline indicator + quick actions (GATE-5).

Shows a green/red/amber tray icon reflecting backend /health, with menu:
Open Dashboard, Open API Docs, Show Logs, Restart Backend, Exit.

Run:  C:\\Python314\\python.exe scripts\\qna_tray.py
Deps: pystray (pip install pystray) — Pillow already present.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_URL = os.environ.get("QNA_API_URL", "http://127.0.0.1:8000")
DASHBOARD_URL = os.environ.get("QNA_UI_URL", "http://localhost:3000")
LOG_FILE = ROOT / "logs" / "live-engine.log"
BACKEND_CMD = [sys.executable, str(ROOT / "qna.py"), "api"]

try:
    import pystray
except ImportError:
    print("pystray missing — pip install pystray")
    sys.exit(1)

import requests  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def _icon_image(color: str) -> Image.Image:
    img = Image.new("RGB", (64, 64), (10, 10, 14))
    d = ImageDraw.Draw(img)
    d.ellipse([12, 12, 52, 52], fill=color)
    d.text((22, 26), "Q", fill=(255, 255, 255))
    return img


COLORS = {
    "online": (0, 224, 158),
    "offline": (90, 90, 100),
    "error": (255, 59, 48),
}


class QNATray:
    def __init__(self) -> None:
        self.state = "offline"
        self._backend_proc: subprocess.Popen | None = None
        self.icon = pystray.Icon(
            "QNA",
            icon=_icon_image(COLORS["offline"]),
            title="QNA: checking…",
            menu=pystray.Menu(
                pystray.MenuItem("Open Dashboard",
                                 lambda *_: webbrowser.open(DASHBOARD_URL), default=True),
                pystray.MenuItem("Open API Docs",
                                 lambda *_: webbrowser.open(f"{API_URL}/docs")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Start Backend", self._start_backend),
                pystray.MenuItem("Restart Backend", self._restart_backend),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Show Logs", self._show_logs),
                pystray.MenuItem(lambda item: f"Status: {self.state}", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._exit),
            ),
        )

    # ── actions ──────────────────────────────────────────────────────
    def _start_backend(self, *_):
        if self._backend_proc and self._backend_proc.poll() is None:
            return
        env = dict(os.environ)
        env["PYTHONPATH"] = ""
        self._backend_proc = subprocess.Popen(
            BACKEND_CMD, cwd=str(ROOT), env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    def _restart_backend(self, *_):
        if self._backend_proc and self._backend_proc.poll() is None:
            self._backend_proc.terminate()
            time.sleep(2)
        self._start_backend()

    def _show_logs(self, *_):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_FILE.exists():
            LOG_FILE.touch()
        os.startfile(str(LOG_FILE))  # noqa: S606

    def _exit(self, *_):
        if self._backend_proc and self._backend_proc.poll() is None:
            self._backend_proc.terminate()
        self.icon.stop()

    # ── health loop ──────────────────────────────────────────────────
    def _poll_health(self) -> str:
        try:
            r = requests.get(f"{API_URL}/health", timeout=4)
            data = r.json() if r.status_code == 200 else {}
            ks = data.get("kill_switch_active")
            return "online" if not ks else "error"
        except Exception:
            proc_alive = self._backend_proc and self._backend_proc.poll() is None
            return "error" if proc_alive else "offline"

    def _health_loop(self) -> None:
        while self.icon.visible or True:
            new = self._poll_health()
            if new != self.state:
                self.state = new
                self.icon.icon = _icon_image(COLORS[new])
            label = {
                "online": "QNA: ONLINE — trading live",
                "error": "QNA: ERROR — kill switch active / degraded",
                "offline": "QNA: OFFLINE — backend down",
            }[new]
            self.icon.title = label
            time.sleep(5)

    def run(self) -> None:
        threading.Thread(target=self._health_loop, daemon=True).start()
        self.icon.run()


if __name__ == "__main__":
    QNATray().run()
