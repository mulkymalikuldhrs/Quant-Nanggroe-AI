"""Autonomous Guardian — self-healing watchtower for QNA Hedge Fund.

Single entry point: `from quant_nanggroe.engine.guardian import Guardian`.

The Guardian continuously monitors the ENTIRE QNA ecosystem:
  - MT5 connection (re-init / flag relaunch if it drops)
  - Kill-switch state (detects the silent AUTO_DAILY_LIMIT veto bug)
  - Trading engine liveness (process + cycle heartbeat)
  - Strategy registry liveness (all strategies loaded)
  - Canonical UI (localhost:3000) reachability
  - API wiring (critical endpoints return 200)
  - Trade journal vs live MT5 positions consistency
  - Disk / error-log anomaly detection

On ANY anomaly it:
  1. writes a structured issue .md to the project root,
  2. appends to logs/guardian.log,
  3. auto-dispatches a coding agent (opencode -> hermes chat -q) to fix it,
     after auto-detecting the OS (Windows / Linux / macOS).

No mock. Every check degrades gracefully (paper mode, API down) and reports
honestly instead of fabricating health.
"""

from .checks import CheckResult, Severity
from .core import Guardian, GuardianConfig

__all__ = ["Guardian", "GuardianConfig", "CheckResult", "Severity"]
