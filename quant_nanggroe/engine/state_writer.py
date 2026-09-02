"""Paper state writer — atomic, thread-safe persistence for paper_state/.

Writes JSON/CSV state files that the legacy HTML dashboard reads live.
Follows the same atomic-write pattern as kill_switch.py (write .tmp, rename)
to prevent partial reads.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()
_DEFAULT_WRITER: Optional["PaperStateWriter"] = None

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PaperStateWriter:
    """Atomic, thread-safe writer for all paper_state/ files.

    Parameters
    ----------
    state_dir:
        Directory path for state files. Defaults to ``<project_root>/paper_state/``.
    """

    def __init__(self, state_dir: Optional[os.PathLike[str]] = None) -> None:
        self._dir = Path(state_dir) if state_dir else (_PROJECT_ROOT / "paper_state")
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Internal helpers ──────────────────────────────────────────────

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _write_json(self, name: str, data: Any) -> None:
        path = self._dir / name
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, path)

    def _write_text(self, name: str, text: str) -> None:
        path = self._dir / name
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    # ── Per-file writers ──────────────────────────────────────────────

    def write_state(self, state: dict) -> None:
        """Write ``state.json`` — top-level engine snapshot."""
        payload = {
            "timestamp": self._now(),
            "total_value": state.get("total_value", 0),
            "cash_balance": state.get("cash_balance", 0),
            "positions_count": state.get("positions_count", 0),
            "daily_pnl": state.get("daily_pnl", 0),
            "weekly_pnl": state.get("weekly_pnl", 0),
            "drawdown": state.get("drawdown", 0),
            "regime": state.get("regime", "unknown"),
        }
        with _LOCK:
            self._write_json("state.json", payload)

    def write_pnl(self, pnl_data: List[Dict[str, Any]]) -> None:
        """Write ``pnl.csv`` — P&L records with columns timestamp,symbol,pnl,reason."""
        with _LOCK:
            path = self._dir / "pnl.csv"
            tmp = path.with_name(path.name + ".tmp")
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "pnl", "reason"])
                writer.writeheader()
                writer.writerows(pnl_data)
            os.replace(tmp, path)

    def write_kill_switch(self, state: dict) -> None:
        """Write ``kill_switch_state.json``."""
        payload = {
            "active": state.get("active", False),
            "is_active": state.get("is_active", state.get("active", False)),
            "level": state.get("level"),
            "triggered_at": state.get("triggered_at"),
            "reason": state.get("reason"),
        }
        with _LOCK:
            self._write_json("kill_switch_state.json", payload)

    def write_positions(self, positions: list) -> None:
        """Write ``positions.json`` — current open positions."""
        with _LOCK:
            self._write_json("positions.json", positions)

    def write_daemon_pid(self, pid: int) -> None:
        """Write ``daemon.pid`` — just the PID as text."""
        with _LOCK:
            self._write_text("daemon.pid", str(pid))

    def write_auto_disable(self, state: dict) -> None:
        """Write ``auto_disable_state.json``."""
        with _LOCK:
            self._write_json("auto_disable_state.json", state)

    def write_tuned_params(self, params: dict) -> None:
        """Write ``tuned_params.json``."""
        with _LOCK:
            self._write_json("tuned_params.json", params)

    def write_correlation_state(self, state: dict) -> None:
        """Write ``correlation_state.json``."""
        with _LOCK:
            self._write_json("correlation_state.json", state)

    def write_anomaly_state(self, state: dict) -> None:
        """Write ``anomaly_state.json``."""
        with _LOCK:
            self._write_json("anomaly_state.json", state)

    def write_regime_adapted_params(self, params: dict) -> None:
        """Write ``regime_adapted_params.json``."""
        with _LOCK:
            self._write_json("regime_adapted_params.json", params)

    def write_budget_state(self, state: dict) -> None:
        """Write ``budget_state.json``."""
        with _LOCK:
            self._write_json("budget_state.json", state)

    def write_all(
        self,
        engine_state: Optional[dict] = None,
        risk_state: Optional[dict] = None,
        positions: Optional[list] = None,
    ) -> None:
        """Convenience: write state.json, kill_switch_state.json, and positions.json in one call."""
        if engine_state:
            self.write_state(engine_state)
        if risk_state:
            self.write_kill_switch(risk_state)
        if positions is not None:
            self.write_positions(positions)

    def assert_reconciled(self, journal_path=None) -> None:
        """Verify state.json total_value matches journal sum(pnl) within $1."""
        import sqlite3
        journal = Path(journal_path) if journal_path else (_PROJECT_ROOT / "quant_nanggroe" / "data" / "qna_trade_journal.db")
        if not journal.exists():
            logger.warning("journal not found at %s", journal)
            return
        try:
            total = float(json.loads((self._dir / "state.json").read_text(encoding="utf-8")).get("total_value", 0))
            j_pnl = float(sqlite3.connect(str(journal)).execute("SELECT SUM(pnl) FROM trades").fetchone()[0] or 0)
            diff = abs(total - j_pnl)
            if diff >= 1.0:
                msg = f"DRIFT: state {total} vs journal {j_pnl} diff {diff:.2f}"
                logger.error(msg)
                raise AssertionError(msg)
            logger.info("reconciled: state %.2f vs journal %.2f diff %.4f", total, j_pnl, diff)
        except FileNotFoundError:
            logger.warning("state.json not found — skip")


def get_state_writer(state_dir: Optional[os.PathLike[str]] = None) -> PaperStateWriter:
    """Return the module-level PaperStateWriter singleton.

    Creates it on first call.  Pass ``state_dir`` only on the first call;
    subsequent calls ignore it.
    """
    global _DEFAULT_WRITER
    if _DEFAULT_WRITER is None:
        _DEFAULT_WRITER = PaperStateWriter(state_dir)
    return _DEFAULT_WRITER


def write_engine_snapshot(
    engine_state: Optional[dict] = None,
    risk_state: Optional[dict] = None,
    positions: Optional[list] = None,
) -> None:
    """One-call convenience using the default singleton writer."""
    get_state_writer().write_all(engine_state, risk_state, positions)



class PaperStateReader:
    """Read state from paper_state/ directory."""

    def __init__(self, state_dir: Optional[os.PathLike[str]] = None) -> None:
        self._dir = Path(state_dir) if state_dir else (_PROJECT_ROOT / "paper_state")

    def read_json(self, filename: str) -> dict:
        path = self._dir / filename
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def read_csv(self, filename: str) -> list:
        path = self._dir / filename
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def read_text(self, filename: str) -> str:
        path = self._dir / filename
        if not path.exists():
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
