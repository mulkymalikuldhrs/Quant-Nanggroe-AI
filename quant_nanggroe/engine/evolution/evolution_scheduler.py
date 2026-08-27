"""EvolutionScheduler — decides when to trigger evolution runs.

Checks thresholds: minimum trade count, calendar days since last run,
drawdown trigger, consecutive loss streak.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
        """Return True if evolution should run."""
        # ── Check time since last run ────────────────────────────────
        last_run = journal.get_last_run()
        now = datetime.now(timezone.utc)

        if last_run is not None:
            try:
                last_ts = datetime.fromisoformat(last_run["timestamp"])
            except (ValueError, TypeError):
                last_ts = datetime.min.replace(tzinfo=timezone.utc)

            # Ensure timezone-aware comparison
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            if (now - last_ts) < timedelta(hours=1):
                # Minimum 1-hour cooldown
                self._reason = "Cooldown active — last run < 1 hour ago"
                return False

        # ── Check trade count ────────────────────────────────────────
        all_trades = journal.all_trades(limit=self.threshold_trades)
        if len(all_trades) < self.threshold_trades:
            self._reason = (
                f"Trade count {len(all_trades)} < threshold {self.threshold_trades}"
            )
            return False

        # ── Check consecutive losses across all strategies ───────────
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

        # ── Check schedule interval ──────────────────────────────────
        if last_run is not None:
            days_since = (now - last_ts).days
            if days_since >= self.schedule_days:
                self._reason = f"Scheduled — {days_since} days since last run"
                return True

        # ── Check drawdown ───────────────────────────────────────────
        # Only trigger if we have some history
        if len(all_trades) >= self.threshold_trades * 2:
            # ponytail: checks per-strategy max_drawdown from agg stats;
            # upgrade to rolling equity-curve drawdown when equity-curve is wired.
            self._reason = (
                f"Not enough trades ({len(all_trades)}) for drawdown check — skipping"
            )
            return False

        self._reason = "No trigger conditions met"
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
