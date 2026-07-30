"""EvolutionScheduler — decides when to trigger evolution runs.

Checks thresholds: minimum trade count, calendar days since last run,
drawdown trigger, consecutive loss streak.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal


class EvolutionScheduler:
    """Check if it's time to run evolution."""

    def __init__(
        self,
        threshold_trades: int = 20,
        schedule_days: int = 7,
        drawdown_trigger: float = 5.0,
        consecutive_loss: int = 3,
    ) -> None:
        self.threshold_trades = threshold_trades
        self.schedule_days = schedule_days
        self.drawdown_trigger = drawdown_trigger
        self.consecutive_loss = consecutive_loss
        self._reason: str = ""

    def should_run(self, journal: EvolutionJournal) -> bool:
        """Return True if evolution should run.

        Gates:
        - Trade count must be >= threshold (no analysis without data)
        - 1h cooldown prevents rapid re-triggers

        Triggers (ANY):
        - Consecutive loss streak (emergency)
        - Schedule time reached (time-based fallback)
        """
        all_trades = journal.all_trades(limit=self.threshold_trades)
        now = datetime.now(timezone.utc)
        last_run = journal.get_last_run()
        last_ts = None
        if last_run is not None:
            try:
                last_ts = datetime.fromisoformat(last_run["timestamp"])
            except (ValueError, TypeError):
                last_ts = None
            if last_ts and last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)

        # ── GATE: minimum trade count ──────────────────────────────
        if len(all_trades) < self.threshold_trades:
            self._reason = f"Trade count {len(all_trades)} < threshold {self.threshold_trades}"
            return False

        # ── GATE: cooldown ─────────────────────────────────────────
        if last_ts and (now - last_ts) < timedelta(hours=1):
            self._reason = "Cooldown active — last run < 1 hour ago"
            return False

        # ── TRIGGER: consecutive loss streak ───────────────────────
        recent = all_trades[: self.consecutive_loss * 2]
        if len(recent) >= self.consecutive_loss:
            streak = 0
            for t in recent:
                if (t.get("pnl") or 0) <= 0:
                    streak += 1
                    if streak >= self.consecutive_loss:
                        self._reason = f"Consecutive loss streak >= {self.consecutive_loss}"
                        return True
                else:
                    streak = 0

        # ── TRIGGER: schedule time reached ─────────────────────────
        if last_ts and (now - last_ts) >= timedelta(days=self.schedule_days):
            self._reason = f"Schedule time reached ({self.schedule_days} days since last run)"
            return True

        # ── No trigger conditions met ─────────────────────────────
        self._reason = "Evolution conditions not met — no loss streak and schedule not due"
        return False

    def get_reason(self) -> str:
        """Return explanation string from last should_run() call."""
        return self._reason

    def should_run_scheduled(self, journal: EvolutionJournal) -> bool:
        """Quick check: has schedule_days elapsed since last run?"""
        last_run = journal.get_last_run()
        if last_run is None:
            return True
        try:
            last_ts = datetime.fromisoformat(last_run["timestamp"])
        except (ValueError, TypeError):
            return True
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        days_since = (datetime.now(timezone.utc) - last_ts).days
        return days_since >= self.schedule_days
