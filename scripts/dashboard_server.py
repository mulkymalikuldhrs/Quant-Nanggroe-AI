#!/usr/bin/env python3
"""dashboard_server.py — serves Quant Nanggroe AI dashboard + paper_state JSON files.

Usage:
    python3 scripts/dashboard_server.py
    # Serves on http://localhost:8080

No dependencies beyond Python stdlib (http.server).
"""

import http.server
import mimetypes
import os
from pathlib import Path

# Auto-detect repo root (this file lives in scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_HTML = REPO_ROOT / "dashboard" / "qnai_dashboard.html"
PAPER_STATE_DIR = REPO_ROOT / "paper_state"
DOCS_DIR = REPO_ROOT / "docs"
PORT = int(os.environ.get("QNAI_DASHBOARD_PORT", 8080))

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def end_headers(self):
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = self.path

        # Root → dashboard HTML
        if path == "/" or path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if DASHBOARD_HTML.exists():
                self.wfile.write(DASHBOARD_HTML.read_bytes())
            else:
                self.wfile.write(b"<h1>Dashboard HTML not found</h1>")
            return

        # paper_state/ files → serve with correct content type
        if path.startswith("/paper_state/"):
            filename = path[len("/paper_state/"):]
            filepath = PAPER_STATE_DIR / filename
            if not filepath.exists():
                self.send_error(404, f"State file not found: {filename}")
                return
            self._serve_file(filepath)
            return

        # docs/ files
        if path.startswith("/docs/"):
            filename = path[len("/docs/"):]
            filepath = DOCS_DIR / filename
            if not filepath.exists():
                self.send_error(404, f"Doc file not found: {filename}")
                return
            self._serve_file(filepath)
            return

        # Everything else → try static files from repo root
        super().do_GET()

    def _serve_file(self, filepath: Path):
        ext = filepath.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(filepath))

        if ext == ".json":
            mime_type = "application/json"
        elif ext == ".csv":
            mime_type = "text/csv"
        elif ext == ".pid":
            mime_type = "text/plain"

        content = filepath.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(content)


def main():
    server = http.server.HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print("Quant Nanggroe AI Dashboard Server")
    print(f"  URL:      http://localhost:{PORT}")
    print(f"  Repo:     {REPO_ROOT}")
    print("  Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
