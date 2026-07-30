#!/usr/bin/env python3
"""QNA Autonomous Guardian — CLI launcher.

Runs the self-healing watchtower that monitors the entire QNA hedge-fund
ecosystem (MT5, kill-switch, trading engine, strategy registry, canonical UI,
API wiring, logs, disk) and auto-dispatches a coding agent to fix anomalies.

Usage:
    python guardian_cli.py                 # loop forever (60s)
    python guardian_cli.py --once          # single pass, exit with code
    python guardian_cli.py --interval 30   # 30s loop
    python guardian_cli.py --no-dispatch   # log only, no agent spawn

Env:
    QNA_API_URL  (default http://localhost:8000)
    QNA_UI_URL   (default http://localhost:3000)
    QNA_API_KEY  (for kill-switch/registry/auth reads)
"""
import os
import sys

# Ensure the package root is importable when run as a script.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)  # worktree root = parent of quant_nanggroe/
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from quant_nanggroe.engine.guardian.core import _main  # noqa: E402

if __name__ == "__main__":
    _main()
