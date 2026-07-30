"""Tests for EvolutionScheduler — trigger logic for evolution runs."""

from __future__ import annotations

import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest

from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal
from quant_nanggroe.engine.evolution.evolution_scheduler import EvolutionScheduler


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def journal() -> EvolutionJournal:
    """Temp-file journal, cleaned up after test."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = Path(tmp.name)
    tmp.close()
    j = EvolutionJournal(path)
    try:
        yield j
    finally:
        j.close()
        path.unlink(missing_ok=True)


def _seed_trades(
    journal: EvolutionJournal,
    count: int,
    strategy: str = "test_strat",
    pnl: float = 10.0,
) -> None:
    """Insert N winning trades for a strategy."""
    for _ in range(count):
        journal.record_trade({
            "strategy": strategy,
            "symbol": "BTCUSD",
            "direction": "long",
            "pnl": pnl,
            "pnl_pct": 0.5,
        })


def _seed_losses(
    journal: EvolutionJournal,
    count: int,
    strategy: str = "test_strat",
    pnl: float = -10.0,
) -> None:
    """Insert N losing trades."""
    for _ in range(count):
        journal.record_trade({
            "strategy": strategy,
            "symbol": "BTCUSD",
            "direction": "long",
            "pnl": pnl,
            "pnl_pct": -0.5,
        })


def _seed_run(journal: EvolutionJournal, days_ago: int) -> None:
    """Insert an evolution run with timestamp in the past."""
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(timespec="milliseconds")
    journal.record_run({"trigger": "scheduled", "timestamp": ts})


# ── Trade count trigger ───────────────────────────────────────────────────


class TestTradeCountTrigger:
    def test_insufficient_trades_returns_false(self, journal: EvolutionJournal) -> None:
        sched = EvolutionScheduler(threshold_trades=10)
        _seed_trades(journal, 5)
        assert sched.should_run(journal) is False
        assert "Trade count" in sched.get_reason()

    def test_sufficient_trades_but_no_other_trigger(self, journal: EvolutionJournal) -> None:
        """10 trades but no losses and first run — trade count alone is NOT a trigger.
        should_run checks trade count threshold first and returns False if below it,
        but having >= threshold trades alone does NOT trigger — it then checks
        consecutive losses and schedule interval.

        Since there's no last_run, schedule interval is skipped. No loss streak.
        The drawdown branch also gets hit and returns "not enough trades for drawdown".
        Result: should_run returns False.
        """
        sched = EvolutionScheduler(threshold_trades=5)
        _seed_trades(journal, 5)
        assert sched.should_run(journal) is False

    def test_trade_count_plus_loss_streak_triggers(self, journal: EvolutionJournal) -> None:
        """Enough trades + consecutive losses = True."""
        sched = EvolutionScheduler(threshold_trades=5, consecutive_loss=3)
        _seed_trades(journal, 5, pnl=10.0)           # wins
        _seed_losses(journal, 3, pnl=-10.0)            # 3 consecutive losses
        assert sched.should_run(journal) is True
        assert "loss" in sched.get_reason().lower()


# ── Time-based trigger ────────────────────────────────────────────────────


class TestTimeBasedTrigger:
    def test_schedule_days_elapsed_triggers(self, journal: EvolutionJournal) -> None:
        """Scheduled run after schedule_days elapsed."""
        sched = EvolutionScheduler(threshold_trades=5, schedule_days=7)
        _seed_run(journal, days_ago=10)
        _seed_trades(journal, 5)
        assert sched.should_run(journal) is True
        assert "Schedule" in sched.get_reason()

    def test_schedule_days_not_elapsed_still_checks_losses(self, journal: EvolutionJournal) -> None:
        """Within schedule window but loss streak triggers."""
        sched = EvolutionScheduler(threshold_trades=5, schedule_days=30, consecutive_loss=2)
        _seed_run(journal, days_ago=1)
        _seed_trades(journal, 5, pnl=10.0)
        _seed_losses(journal, 2, pnl=-10.0)
        assert sched.should_run(journal) is True

    def test_should_run_scheduled_no_prior_run(self, journal: EvolutionJournal) -> None:
        """No prior run means scheduled check returns True."""
        sched = EvolutionScheduler()
        assert sched.should_run_scheduled(journal) is True

    def test_should_run_scheduled_elapsed(self, journal: EvolutionJournal) -> None:
        """Prior run old enough returns True."""
        sched = EvolutionScheduler(schedule_days=7)
        _seed_run(journal, days_ago=14)
        assert sched.should_run_scheduled(journal) is True

    def test_should_run_scheduled_not_elapsed(self, journal: EvolutionJournal) -> None:
        """Prior run too recent returns False."""
        sched = EvolutionScheduler(schedule_days=7)
        _seed_run(journal, days_ago=2)
        assert sched.should_run_scheduled(journal) is False


# ── Consecutive loss trigger ──────────────────────────────────────────────


class TestConsecutiveLossTrigger:
    def test_loss_streak_triggers(self, journal: EvolutionJournal) -> None:
        sched = EvolutionScheduler(threshold_trades=5, consecutive_loss=3)
        _seed_trades(journal, 5)
        journal.record_trade({
            "strategy": "lossy", "symbol": "X", "direction": "long", "pnl": -5.0
        })
        journal.record_trade({
            "strategy": "lossy", "symbol": "X", "direction": "long", "pnl": -5.0
        })
        journal.record_trade({
            "strategy": "lossy", "symbol": "X", "direction": "long", "pnl": -5.0
        })
        assert sched.should_run(journal) is True

    def test_loss_below_streak_no_trigger(self, journal: EvolutionJournal) -> None:
        sched = EvolutionScheduler(threshold_trades=5, consecutive_loss=5)
        _seed_trades(journal, 5)
        _seed_losses(journal, 3)
        assert sched.should_run(journal) is False

    def test_loss_streak_reset_by_win(self, journal: EvolutionJournal) -> None:
        """Win breaks streak — should not trigger."""
        sched = EvolutionScheduler(threshold_trades=5, consecutive_loss=3)
        journal.record_trade({
            "strategy": "x", "symbol": "X", "direction": "long", "pnl": -5.0
        })
        journal.record_trade({
            "strategy": "x", "symbol": "X", "direction": "long", "pnl": -5.0
        })
        journal.record_trade({
            "strategy": "x", "symbol": "X", "direction": "long", "pnl": 10.0   # win
        })
        journal.record_trade({
            "strategy": "x", "symbol": "X", "direction": "long", "pnl": -5.0
        })
        # Need enough trades to pass threshold first
        _seed_trades(journal, 5)
        assert sched.should_run(journal) is False


# ── Cooldown ──────────────────────────────────────────────────────────────


class TestCooldown:
    def test_cooldown_blocks_immediate_run(self, journal: EvolutionJournal) -> None:
        """Last run less than 1 hour ago returns False."""
        sched = EvolutionScheduler(threshold_trades=5, consecutive_loss=2)
        # Recent run (now)
        journal.record_run({"trigger": "test"})
        # Add enough trade + losses to satisfy other triggers
        _seed_trades(journal, 5)
        _seed_losses(journal, 2)
        assert sched.should_run(journal) is False
        assert "Cooldown" in sched.get_reason()


# ── No trigger ────────────────────────────────────────────────────────────


class TestNoTrigger:
    def test_no_trigger_returns_false(self, journal: EvolutionJournal) -> None:
        sched = EvolutionScheduler(threshold_trades=5, schedule_days=30, consecutive_loss=10)
        _seed_trades(journal, 5)
        _seed_run(journal, days_ago=1)
        assert sched.should_run(journal) is False
        assert "not met" in sched.get_reason() or "No trigger" in sched.get_reason()


# ── Edge cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_malformed_timestamp_in_last_run(self, journal: EvolutionJournal) -> None:
        """Bad timestamp in last run should not crash — treated as ancient."""
        sched = EvolutionScheduler(threshold_trades=5, schedule_days=1)
        journal.record_run({"trigger": "bad_ts", "timestamp": "not-a-date"})
        _seed_trades(journal, 5)
        should = sched.should_run(journal)
        # Should not crash; returns whatever logic produces

    def test_empty_journal(self, journal: EvolutionJournal) -> None:
        """No trades, no runs — should_run returns False."""
        sched = EvolutionScheduler(threshold_trades=5)
        assert sched.should_run(journal) is False

    def test_custom_thresholds(self, journal: EvolutionJournal) -> None:
        """Custom thresholds work."""
        sched = EvolutionScheduler(
            threshold_trades=3, schedule_days=1, consecutive_loss=2
        )
        _seed_trades(journal, 3)
        _seed_losses(journal, 2)
        assert sched.should_run(journal) is True