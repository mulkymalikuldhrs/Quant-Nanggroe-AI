"""Comprehensive tests for Trade Journal module.

Tests:
- Recording trade entries
- Recording trade exits with PnL calculation
- Adding reflections
- Trade history with filters
- Performance summary calculation
- Persistence (save/load)
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest

from quant_nanggroe.memory.journal import TradeJournal


@pytest.fixture
def journal():
    """Fresh TradeJournal instance."""
    return TradeJournal()


@pytest.fixture
def journal_with_trades(journal):
    """Journal with some pre-populated trades."""
    journal.record_entry(
        symbol="BTC/USDT", side="buy", price=50000.0, quantity=0.1,
        agent_name="trader", strategy="momentum",
    )
    journal.record_entry(
        symbol="ETH/USDT", side="buy", price=3000.0, quantity=1.0,
        agent_name="strategist", strategy="mean_reversion",
    )
    return journal


@pytest.fixture
def persist_dir():
    """Temporary directory for persistence tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestRecordEntry:
    def test_returns_trade_id(self, journal):
        trade_id = journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        assert trade_id.startswith("T")
        assert len(trade_id) > 1

    def test_sequential_trade_ids(self, journal):
        id1 = journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        id2 = journal.record_entry("ETH/USDT", "buy", 3000.0, 1.0)
        assert id1 != id2

    def test_trade_stored_as_open(self, journal):
        journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        trades = journal.get_trade_history()
        assert len(trades) == 1
        assert trades[0]["status"] == "open"

    def test_entry_fields(self, journal):
        journal.record_entry(
            symbol="BTC/USDT", side="buy", price=50000.0, quantity=0.1,
            agent_name="trader", strategy="momentum", reasoning="Strong uptrend",
        )
        trade = journal.get_trade_history()[0]
        assert trade["symbol"] == "BTC/USDT"
        assert trade["side"] == "buy"
        assert trade["entry_price"] == 50000.0
        assert trade["entry_quantity"] == 0.1
        assert trade["agent_name"] == "trader"
        assert trade["strategy"] == "momentum"
        assert trade["reasoning"] == "Strong uptrend"
        assert trade["exit_price"] is None
        assert trade["pnl"] is None

    def test_open_position_tracking(self, journal):
        journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        assert "BTC/USDT" in journal._open_positions

    def test_metadata_stored(self, journal):
        journal.record_entry(
            "BTC/USDT", "buy", 50000.0, 0.1,
            metadata={"market_regime": "bull"},
        )
        trade = journal.get_trade_history()[0]
        assert trade["metadata"]["market_regime"] == "bull"


class TestRecordExit:
    def test_exit_with_pnl(self, journal_with_trades):
        trade_id = journal_with_trades.record_exit("BTC/USDT", price=52000.0, pnl=200.0)
        assert trade_id is not None

    def test_exit_auto_calculates_buy_pnl(self, journal):
        journal.record_entry("BTC/USDT", "buy", price=50000.0, quantity=0.1)
        journal.record_exit("BTC/USDT", price=52000.0)
        trade = journal.get_trade_history()[0]
        expected_pnl = (52000.0 - 50000.0) * 0.1  # = 200
        assert trade["pnl"] == expected_pnl

    def test_exit_auto_calculates_sell_pnl(self, journal):
        journal.record_entry("BTC/USDT", "sell", price=50000.0, quantity=0.1)
        journal.record_exit("BTC/USDT", price=48000.0)
        trade = journal.get_trade_history()[0]
        expected_pnl = (50000.0 - 48000.0) * 0.1  # = 200
        assert trade["pnl"] == expected_pnl

    def test_exit_marks_closed(self, journal_with_trades):
        journal_with_trades.record_exit("BTC/USDT", price=52000.0, pnl=200.0)
        trade = journal_with_trades.get_trade_history()[0]
        assert trade["status"] == "closed"

    def test_exit_removes_from_open_positions(self, journal_with_trades):
        journal_with_trades.record_exit("BTC/USDT", price=52000.0, pnl=200.0)
        assert "BTC/USDT" not in journal_with_trades._open_positions

    def test_exit_nonexistent_position(self, journal):
        result = journal.record_exit("XRP/USDT", price=1.0)
        assert result is None

    def test_exit_explicit_pnl_overrides_calculation(self, journal):
        journal.record_entry("BTC/USDT", "buy", price=50000.0, quantity=0.1)
        journal.record_exit("BTC/USDT", price=52000.0, pnl=500.0)
        trade = journal.get_trade_history()[0]
        assert trade["pnl"] == 500.0

    def test_exit_with_notes(self, journal_with_trades):
        journal_with_trades.record_exit("BTC/USDT", price=52000.0, pnl=200.0, notes="Good trade")
        trade = journal_with_trades.get_trade_history()[0]
        assert trade["notes"] == "Good trade"

    def test_pnl_pct_calculated(self, journal):
        journal.record_entry("BTC/USDT", "buy", price=50000.0, quantity=0.1)
        journal.record_exit("BTC/USDT", price=52000.0)
        trade = journal.get_trade_history()[0]
        expected_pct = (200.0 / (50000.0 * 0.1)) * 100  # 4%
        assert abs(trade["pnl_pct"] - expected_pct) < 0.01


class TestAddReflection:
    def test_add_reflection_to_open_position(self, journal_with_trades):
        journal_with_trades.add_reflection("BTC/USDT", "Good entry timing", rating=4)
        trade = journal_with_trades.get_trade_history()[0]
        assert trade["reflection"]["notes"] == "Good entry timing"
        assert trade["reflection"]["rating"] == 4

    def test_add_reflection_to_closed_trade(self, journal):
        journal.record_entry("BTC/USDT", "buy", price=50000.0, quantity=0.1)
        journal.record_exit("BTC/USDT", price=52000.0, pnl=200.0)
        journal.add_reflection("BTC/USDT", "Should have held longer", rating=3)
        trade = journal.get_trade_history()[0]
        assert trade["reflection"]["notes"] == "Should have held longer"

    def test_add_reflection_without_rating(self, journal_with_trades):
        journal_with_trades.add_reflection("BTC/USDT", "Observation only")
        trade = journal_with_trades.get_trade_history()[0]
        assert trade["reflection"]["rating"] is None


class TestGetTradeHistory:
    def test_get_all_trades(self, journal_with_trades):
        trades = journal_with_trades.get_trade_history()
        assert len(trades) == 2

    def test_filter_by_symbol(self, journal_with_trades):
        trades = journal_with_trades.get_trade_history(symbol="BTC/USDT")
        assert len(trades) == 1
        assert trades[0]["symbol"] == "BTC/USDT"

    def test_filter_by_status(self, journal_with_trades):
        journal_with_trades.record_exit("BTC/USDT", price=52000.0, pnl=200.0)
        open_trades = journal_with_trades.get_trade_history(status="open")
        assert len(open_trades) == 1
        assert open_trades[0]["symbol"] == "ETH/USDT"

    def test_limit(self, journal):
        for i in range(10):
            journal.record_entry(f"SYM{i}", "buy", 100.0, 1.0)
        trades = journal.get_trade_history(limit=5)
        assert len(trades) == 5

    def test_returns_most_recent(self, journal):
        for i in range(10):
            journal.record_entry(f"SYM{i}", "buy", 100.0, 1.0)
        trades = journal.get_trade_history(limit=3)
        symbols = [t["symbol"] for t in trades]
        assert "SYM9" in symbols
        assert "SYM8" in symbols
        assert "SYM7" in symbols

    def test_empty_journal(self, journal):
        trades = journal.get_trade_history()
        assert len(trades) == 0


class TestGetPerformanceSummary:
    def test_empty_summary(self, journal):
        summary = journal.get_performance_summary()
        assert summary["total_trades"] == 0

    def test_with_winning_trades(self, journal):
        journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        journal.record_exit("BTC/USDT", price=52000.0)
        summary = journal.get_performance_summary()
        assert summary["total_trades"] == 1
        assert summary["winning_trades"] == 1
        assert summary["losing_trades"] == 0
        assert summary["win_rate"] == 1.0
        assert summary["total_pnl"] > 0

    def test_with_losing_trades(self, journal):
        journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        journal.record_exit("BTC/USDT", price=48000.0)
        summary = journal.get_performance_summary()
        assert summary["losing_trades"] == 1
        assert summary["total_pnl"] < 0

    def test_mixed_trades(self, journal):
        # Win
        journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        journal.record_exit("BTC/USDT", price=52000.0)
        # Loss
        journal.record_entry("ETH/USDT", "buy", 3000.0, 1.0)
        journal.record_exit("ETH/USDT", price=2800.0)
        summary = journal.get_performance_summary()
        assert summary["total_trades"] == 2
        assert summary["winning_trades"] == 1
        assert summary["losing_trades"] == 1
        assert abs(summary["win_rate"] - 0.5) < 0.01

    def test_profit_factor(self, journal):
        journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        journal.record_exit("BTC/USDT", price=52000.0)  # +200
        journal.record_entry("ETH/USDT", "buy", 3000.0, 1.0)
        journal.record_exit("ETH/USDT", price=2800.0)  # -200
        summary = journal.get_performance_summary()
        assert summary["profit_factor"] == 1.0

    def test_best_and_worst_trade(self, journal):
        journal.record_entry("A", "buy", 100.0, 1.0)
        journal.record_exit("A", price=120.0)  # +20
        journal.record_entry("B", "buy", 100.0, 1.0)
        journal.record_exit("B", price=80.0)  # -20
        summary = journal.get_performance_summary()
        assert summary["best_trade"] == 20.0
        assert summary["worst_trade"] == -20.0

    def test_open_trades_excluded(self, journal):
        journal.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        # Not exited — should not appear in summary
        summary = journal.get_performance_summary()
        assert summary["total_trades"] == 0


class TestJournalPersistence:
    def test_save_and_load(self, persist_dir):
        path = os.path.join(persist_dir, "journal.json")
        j1 = TradeJournal(persist_path=path)
        j1.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        j1.record_exit("BTC/USDT", price=52000.0, pnl=200.0)
        j1.save()

        j2 = TradeJournal(persist_path=path)
        loaded = j2.load()
        assert loaded is True
        assert len(j2.get_trade_history()) == 1
        assert j2.get_trade_history()[0]["pnl"] == 200.0

    def test_save_creates_directory(self, persist_dir):
        path = os.path.join(persist_dir, "subdir", "journal.json")
        j = TradeJournal(persist_path=path)
        j.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        j.save()
        assert os.path.exists(path)

    def test_load_nonexistent_file(self):
        j = TradeJournal(persist_path="/tmp/nonexistent_journal.json")
        assert j.load() is False

    def test_load_without_path(self):
        j = TradeJournal()
        assert j.load() is False

    def test_save_without_path(self):
        j = TradeJournal()
        j.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        j.save()  # Should not raise

    def test_load_rebuilds_open_positions(self, persist_dir):
        path = os.path.join(persist_dir, "journal.json")
        j1 = TradeJournal(persist_path=path)
        j1.record_entry("BTC/USDT", "buy", 50000.0, 0.1)
        j1.save()

        j2 = TradeJournal(persist_path=path)
        j2.load()
        assert "BTC/USDT" in j2._open_positions

    def test_persistence_round_trip_preserves_data(self, persist_dir):
        path = os.path.join(persist_dir, "journal.json")
        j1 = TradeJournal(persist_path=path)
        j1.record_entry("BTC/USDT", "buy", 50000.0, 0.1,
                         agent_name="trader", strategy="momentum",
                         reasoning="Strong trend")
        j1.record_exit("BTC/USDT", price=52000.0, pnl=200.0)
        j1.add_reflection("BTC/USDT", "Good trade", rating=5)
        j1.save()

        j2 = TradeJournal(persist_path=path)
        j2.load()
        trade = j2.get_trade_history()[0]
        assert trade["agent_name"] == "trader"
        assert trade["strategy"] == "momentum"
        assert trade["pnl"] == 200.0
