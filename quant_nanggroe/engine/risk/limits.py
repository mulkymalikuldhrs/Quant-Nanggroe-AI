"""Persistent weekly loss tracking and trade gating.

Stores weekly P&L to ``risk_state.json`` on each trade close.
Loads from file on startup. Resets on Monday 00:00 UTC.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_STATE_DIR = Path(__file__).resolve().parents[3] / "data"
_DEFAULT_STATE_FILE = "risk_state.json"


class RiskLimits:
    """Persistent weekly loss tracker with JSON-backed state.

    ``can_trade()`` returns False when ``weekly_loss >= config.max_weekly_loss_pct``.
    """

    def __init__(
        self,
        max_weekly_loss_pct: float = 0.03,
        state_dir: Optional[Path] = None,
        state_file: str = _DEFAULT_STATE_FILE,
    ) -> None:
        self.max_weekly_loss_pct = max_weekly_loss_pct
        # Accept str or Path for state_dir — normalize defensively
        self._state_dir = Path(state_dir) if state_dir is not None else _DEFAULT_STATE_DIR
        self._state_file = self._state_dir / state_file
        self._weekly_pnl: float = 0.0
        self._week_start_iso: Optional[str] = None
        self._load()
        # Ensure week start is set even if _load() found no file
        if self._week_start_iso is None:
            self._week_start_iso = self._current_week_start(datetime.now(timezone.utc))

    # ── Public API ─────────────────────────────────────────────────────

    def record_trade(self, pnl: float) -> None:
        """Add trade P&L to the running weekly total and persist."""
        self._weekly_pnl += pnl
        self._save()

    def can_trade(self) -> bool:
        """Return False if weekly loss has reached or exceeded the limit."""
        return abs(min(0.0, self._weekly_pnl)) < self.max_weekly_loss_pct

    def current_weekly_loss_pct(self) -> float:
        """Return the current weekly loss as a fraction (0.03 = 3%)."""
        return abs(min(0.0, self._weekly_pnl))

    @property
    def weekly_pnl(self) -> float:
        return self._weekly_pnl

    # ── Persistence ────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load state from disk.  Reset if the stored week differs from
        the current ISO-week (i.e. Monday rollover happened while we
        were down)."""
        try:
            raw = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return

        stored_week = raw.get("week_start")
        now = datetime.now(timezone.utc)
        current_week = self._current_week_start(now)

        if stored_week != current_week:
            self._reset(now)
            return

        self._weekly_pnl = float(raw.get("weekly_pnl", 0.0))
        self._week_start_iso = stored_week
        logger.debug(
            "Weekly loss state loaded: pnl=%.4f, week=%s",
            self._weekly_pnl, self._week_start_iso,
        )

    def _save(self) -> None:
        """Persist state to disk, creating the directory if needed."""
        now = datetime.now(timezone.utc)
        current_week = self._current_week_start(now)
        if self._week_start_iso != current_week:
            self._reset(now)

        self._state_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._state_file.with_suffix(".json.tmp")
        payload = {
            "weekly_pnl": self._weekly_pnl,
            "week_start": self._week_start_iso,
            "updated_at": now.isoformat(),
        }
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self._state_file)

    def _reset(self, now: Optional[datetime] = None) -> None:
        """Zero counters for a fresh week."""
        now = now or datetime.now(timezone.utc)
        self._weekly_pnl = 0.0
        self._week_start_iso = self._current_week_start(now)
        logger.info("Weekly loss counters reset (week starting %s)", self._week_start_iso)

    @staticmethod
    def _current_week_start(dt: datetime) -> str:
        """Return ISO string for Monday 00:00 UTC of the week containing *dt*."""
        monday = dt - __import__("datetime").timedelta(days=dt.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
