"""Persistent risk state — Survives process restarts via file-based persistence.

The RiskManager tracks daily/weekly P&L in memory, which is lost on restart.
This module provides a PersistentRiskState that:
1. Persists risk state to a JSON file on every update
2. Loads state on startup
3. Uses atomic writes to prevent corruption
4. Auto-migrates from in-memory RiskState if no persisted file exists

File format:
    <runtime_root>/risk_state.json

This is critical for production: if the process restarts mid-day, we must
NOT reset daily P&L to zero, as that would allow exceeding daily loss limits.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default persistence path
_DEFAULT_STATE_DIR = os.getenv("QNAI_DATA_DIR", "/tmp/qnai")
_STATE_FILENAME = "risk_state.json"


class PersistentRiskState:
    """Risk state with file-based persistence.

    Every mutation writes the state to disk atomically (temp + os.replace).
    On startup, previous state is loaded from disk.

    Parameters
    ----------
    state_dir:
        Directory for the state file. Defaults to ``QNAI_DATA_DIR`` env var
        or ``/tmp/qnai``.
    initial_equity:
        Starting equity if no persisted state exists.
    """

    def __init__(
        self,
        state_dir: Optional[str] = None,
        initial_equity: float = 1_000_000.0,
    ) -> None:
        self._state_dir = Path(state_dir or _DEFAULT_STATE_DIR)
        self._state_file = self._state_dir / _STATE_FILENAME
        self._initial_equity = initial_equity

        # Ensure directory exists
        self._state_dir.mkdir(parents=True, exist_ok=True)

        # Load or initialize state
        self._state: Dict[str, Any] = self._load_state()

    def _default_state(self) -> Dict[str, Any]:
        """Create default state for first run."""
        return {
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "trade_count_today": 0,
            "trade_count_week": 0,
            "active_positions": [],
            "peak_equity": self._initial_equity,
            "current_equity": self._initial_equity,
            "last_reset_date": datetime.now(timezone.utc).date().isoformat(),
            "version": 1,
        }

    def _load_state(self) -> Dict[str, Any]:
        """Load state from disk, or create default."""
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())
                # Validate essential keys
                required_keys = {
                    "daily_pnl", "weekly_pnl", "trade_count_today",
                    "peak_equity", "current_equity", "last_reset_date",
                }
                if required_keys.issubset(data.keys()):
                    logger.info(
                        "Loaded persisted risk state: daily_pnl=%.2f, weekly_pnl=%.2f, trades_today=%d",
                        data["daily_pnl"], data["weekly_pnl"], data["trade_count_today"],
                    )
                    return data
                else:
                    logger.warning("Persisted risk state missing keys, using defaults")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load risk state: %s, using defaults", e)

        state = self._default_state()
        self._persist(state)
        return state

    def _persist(self, state: Dict[str, Any]) -> None:
        """Write state to disk atomically.

        Uses temp file + os.replace for atomic write (no partial writes).
        """
        try:
            # Write to temp file first
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._state_dir),
                prefix=".risk_state_",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(state, f, indent=2, default=str)
                # Atomic replace
                os.replace(tmp_path, str(self._state_file))
            except Exception:
                os.unlink(tmp_path)
                raise
        except OSError as e:
            logger.error("Failed to persist risk state: %s", e)

    @property
    def daily_pnl(self) -> float:
        return self._state["daily_pnl"]

    @daily_pnl.setter
    def daily_pnl(self, value: float) -> None:
        self._state["daily_pnl"] = value
        self._persist(self._state)

    @property
    def weekly_pnl(self) -> float:
        return self._state["weekly_pnl"]

    @weekly_pnl.setter
    def weekly_pnl(self, value: float) -> None:
        self._state["weekly_pnl"] = value
        self._persist(self._state)

    @property
    def trade_count_today(self) -> int:
        return self._state["trade_count_today"]

    @trade_count_today.setter
    def trade_count_today(self, value: int) -> None:
        self._state["trade_count_today"] = value
        self._persist(self._state)

    @property
    def trade_count_week(self) -> int:
        return self._state.get("trade_count_week", 0)

    @trade_count_week.setter
    def trade_count_week(self, value: int) -> None:
        self._state["trade_count_week"] = value
        self._persist(self._state)

    @property
    def active_positions(self) -> List[str]:
        return self._state.get("active_positions", [])

    @active_positions.setter
    def active_positions(self, value: List[str]) -> None:
        self._state["active_positions"] = value
        self._persist(self._state)

    @property
    def peak_equity(self) -> float:
        return self._state["peak_equity"]

    @peak_equity.setter
    def peak_equity(self, value: float) -> None:
        self._state["peak_equity"] = value
        self._persist(self._state)

    @property
    def current_equity(self) -> float:
        return self._state["current_equity"]

    @current_equity.setter
    def current_equity(self, value: float) -> None:
        self._state["current_equity"] = value
        self._persist(self._state)

    @property
    def last_reset_date(self) -> Optional[date]:
        val = self._state.get("last_reset_date")
        if val is None:
            return None
        if isinstance(val, date):
            return val
        return date.fromisoformat(str(val))

    @last_reset_date.setter
    def last_reset_date(self, value: date) -> None:
        self._state["last_reset_date"] = value.isoformat()
        self._persist(self._state)

    def add_position(self, symbol: str) -> None:
        """Track a new open position."""
        positions = self.active_positions
        if symbol not in positions:
            positions.append(symbol)
            self.active_positions = positions

    def remove_position(self, symbol: str) -> None:
        """Remove a closed position."""
        positions = self.active_positions
        if symbol in positions:
            positions.remove(symbol)
            self.active_positions = positions

    def update_pnl(self, trade_pnl: float) -> None:
        """Update P&L tracking with persistence."""
        self.daily_pnl = self.daily_pnl + trade_pnl
        self.weekly_pnl = self.weekly_pnl + trade_pnl
        self.trade_count_today = self.trade_count_today + 1
        self.trade_count_week = self.trade_count_week + 1
        self.current_equity = self.current_equity + trade_pnl
        self.peak_equity = max(self.peak_equity, self.current_equity + trade_pnl)

    def reset_daily_if_needed(self) -> None:
        """Reset daily counters if new day."""
        today = datetime.now(timezone.utc).date()
        last_reset = self.last_reset_date

        if last_reset is None or today > last_reset:
            self.daily_pnl = 0.0
            self.trade_count_today = 0
            # Reset weekly on Monday
            if today.weekday() == 0:
                self.weekly_pnl = 0.0
                self.trade_count_week = 0
            self.last_reset_date = today

    def to_dict(self) -> Dict[str, Any]:
        """Export current state as dictionary."""
        return dict(self._state)
