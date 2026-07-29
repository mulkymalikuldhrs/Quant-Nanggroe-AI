"""Tests for PerformanceScanner — strategy metrics from trade data."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pytest

from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal
from quant_nanggroe.engine.evolution.performance_scanner import PerformanceScanner


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


@pytest.fixture
def scanner(journal: EvolutionJournal) -> PerformanceScanner:
    """Scanner backed by temp journal."""
    return PerformanceScanner(journal)


def _seed_trades(
    journal: EvolutionJournal,
    strategy: str,
    pnls: list[float],
    pnl_pcts: list[float] | None = None,
) -> None:
    """Insert trades with given pnls (and optionally pnl_pcts)."""
    pcts = pnl_pcts or [p * 0.01 for p in pnls]
    for pnl, pct in zip(pnls, pcts):
        journal.record_trade({
            "strategy": strategy,
            "symbol": "BTCUSD",
            "direction": "long" if pnl >= 0 else "short",
            "pnl": pnl,
            "pnl_pct": pct,
        })


# ── Empty strategy ────────────────────────────────────────────────────────


class TestEmptyStrategy:
    def test_empty_strategy_returns_defaults(self, scanner: PerformanceScanner) -> None:
        result = scanner.scan_strategy("nonexistent")
        assert result["strategy_name"] == "nonexistent"
        assert result["trade_count"] == 0
        assert result["sharpe"] == 0.0
        assert result["sortino"] == 0.0
        assert result["win_rate"] == 0.0
        assert result["profit_factor"] == 0.0
        assert result["max_drawdown"] == 0.0
        assert result["avg_return"] == 0.0
        assert result["total_pnl"] == 0.0


# ── Sharpe ratio ──────────────────────────────────────────────────────────


class TestSharpe:
    def test_sharpe_positive_returns(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "strat_a", pnls=[100.0, 200.0, 150.0], pnl_pcts=[1.0, 2.0, 1.5])
        result = scanner.scan_strategy("strat_a")
        assert result["trade_count"] == 3
        assert result["sharpe"] > 0

    def test_sharpe_zero_variance(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """Identical returns => std=0 => sharpe=0."""
        _seed_trades(journal, "flat", pnls=[10.0, 10.0, 10.0], pnl_pcts=[0.5, 0.5, 0.5])
        result = scanner.scan_strategy("flat")
        assert result["sharpe"] == 0.0

    def test_sharpe_negative_returns(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "loser", pnls=[-50.0, -30.0, -20.0], pnl_pcts=[-5.0, -3.0, -2.0])
        result = scanner.scan_strategy("loser")
        assert result["sharpe"] < 0

    def test_sharpe_one_trade(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """Single trade => std=0 => sharpe=0."""
        _seed_trades(journal, "loner", [42.0], [1.0])
        result = scanner.scan_strategy("loner")
        assert result["sharpe"] == 0.0

    def test_sharpe_formula(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """Manually verify sharpe calculation."""
        returns = [1.0, 2.0, 3.0]
        _seed_trades(journal, "calc", pnls=[100.0, 200.0, 300.0], pnl_pcts=returns)
        result = scanner.scan_strategy("calc")
        # avg=2.0, variance=((1)^2+(0)^2+(1)^2)/(3-1)=1.0, std=1.0, sharpe=2.0/1.0
        assert result["sharpe"] == pytest.approx(2.0, abs=1e-4)


# ── Sortino ratio ─────────────────────────────────────────────────────────


class TestSortino:
    def test_sortino_no_downside(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """All positive returns => downside_std=0 => sortino=0."""
        _seed_trades(journal, "all_win", [10.0, 20.0, 30.0], [1.0, 2.0, 3.0])
        result = scanner.scan_strategy("all_win")
        assert result["sortino"] == 0.0

    def test_sortino_formula(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """Mix of positive and negative returns."""
        returns = [2.0, -1.0, 3.0, -2.0]
        _seed_trades(journal, "mix", [200.0, -100.0, 300.0, -200.0], returns)
        result = scanner.scan_strategy("mix")
        # avg=0.5, downside=[-1, -2], n=2 → sample_std=sqrt(((0.5)^2+(-0.5)^2)/(2-1))=0.7071
        # sortino = 0.5 / 0.7071 = 0.7071
        assert result["sortino"] == pytest.approx(0.7071, abs=1e-4)

    def test_sortino_mixed_with_zeros(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """Returns including zeros — zeros counted as non-negative (excluded from downside).
        With only 1 downside value, _std returns 0.0 (n<2), so sortino = 0."""
        returns = [1.0, 0.0, -2.0, 3.0]
        _seed_trades(journal, "zeros", [10.0, 0.0, -20.0, 30.0], returns)
        result = scanner.scan_strategy("zeros")
        assert result["sortino"] == 0.0


# ── Win rate ──────────────────────────────────────────────────────────────


class TestWinRate:
    def test_all_wins(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "always_win", [10.0, 20.0, 30.0, 40.0], [1.0, 1.0, 1.0, 1.0])
        result = scanner.scan_strategy("always_win")
        assert result["win_rate"] == 1.0

    def test_all_losses(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "always_lose", [-10.0, -20.0], [-1.0, -2.0])
        result = scanner.scan_strategy("always_lose")
        assert result["win_rate"] == 0.0

    def test_mixed_wins_and_losses(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "mixed", [10.0, -5.0, 10.0, -5.0, 10.0], [1.0, -0.5, 1.0, -0.5, 1.0])
        result = scanner.scan_strategy("mixed")
        assert result["win_rate"] == pytest.approx(0.6)
        assert result["trade_count"] == 5

    def test_win_rate_zero_pnl_is_loss(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "zero_edge", [10.0, 0.0, 10.0], [1.0, 0.0, 1.0])
        result = scanner.scan_strategy("zero_edge")
        # 2 wins (10, 10), 1 loss (0.0) → 2/3 rounded to 4dp = 0.6667
        assert result["win_rate"] == pytest.approx(0.6667, abs=1e-4)


# ── Profit factor ─────────────────────────────────────────────────────────


class TestProfitFactor:
    def test_profit_factor_wins_only(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "no_loss", [10.0, 20.0], [1.0, 2.0])
        result = scanner.scan_strategy("no_loss")
        assert result["profit_factor"] == float("inf")

    def test_profit_factor_losses_only(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "no_win", [-10.0, -20.0], [-1.0, -2.0])
        result = scanner.scan_strategy("no_win")
        assert result["profit_factor"] == 0.0

    def test_profit_factor_mixed(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "balanced", [100.0, -50.0, 100.0, -50.0], [5.0, -2.0, 5.0, -2.0])
        result = scanner.scan_strategy("balanced")
        # wins sum=10.0, losses sum=-4.0 => 10/4 = 2.5
        assert result["profit_factor"] == pytest.approx(2.5)


# ── Max drawdown ──────────────────────────────────────────────────────────


class TestMaxDrawdown:
    def test_always_up_no_drawdown(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "uptrend", [10.0, 20.0, 30.0], [1.0, 2.0, 3.0])
        result = scanner.scan_strategy("uptrend")
        assert result["max_drawdown"] == 0.0

    def test_drawdown_positive(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """Returns that dip then recover — non-zero drawdown."""
        returns = [5.0, -3.0, 2.0]
        _seed_trades(journal, "dip", [500.0, -300.0, 200.0], returns)
        result = scanner.scan_strategy("dip")
        # cum: 5, 2, 4. peak=5. max_dd=5-2=3
        assert result["max_drawdown"] == pytest.approx(3.0)

    def test_drawdown_large_correction(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        returns = [10.0, -8.0, 5.0, -2.0, -3.0]
        _seed_trades(journal, "corr", [1000.0, -800.0, 500.0, -200.0, -300.0], returns)
        result = scanner.scan_strategy("corr")
        # cum: 10, 2, 7, 5, 2. peak=10. max_dd=10-2=8
        assert result["max_drawdown"] == pytest.approx(8.0)

    def test_drawdown_single_trade_no_dd(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "single", [42.0], [1.0])
        result = scanner.scan_strategy("single")
        assert result["max_drawdown"] == 0.0


# ── scan_all ──────────────────────────────────────────────────────────────


class TestScanAll:
    def test_scan_all_with_names(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "alpha", [10.0, 10.0, 10.0], [1.0, 1.0, 1.0])
        _seed_trades(journal, "beta", [5.0, 5.0], [0.5, 0.5])
        results = scanner.scan_all(strategy_names=["alpha", "beta"])
        # Sorted by sharpe desc
        assert len(results) == 2
        assert results[0]["strategy_name"] == "alpha"
        assert results[1]["strategy_name"] == "beta"

    def test_scan_all_no_names(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "gamma", [10.0], [0.5])
        _seed_trades(journal, "delta", [20.0], [1.0])
        results = scanner.scan_all()
        assert len(results) == 2
        names = {r["strategy_name"] for r in results}
        assert names == {"gamma", "delta"}

    def test_scan_all_empty_journal(self, scanner: PerformanceScanner) -> None:
        results = scanner.scan_all()
        assert results == []


# ── Internal helpers ──────────────────────────────────────────────────────


class TestHelpers:
    def test_std_single_value(self) -> None:
        assert PerformanceScanner._std([5.0]) == 0.0

    def test_std_two_values(self) -> None:
        assert PerformanceScanner._std([0.0, 2.0]) == pytest.approx(math.sqrt(2.0))

    def test_std_all_same(self) -> None:
        assert PerformanceScanner._std([1.0, 1.0, 1.0]) == 0.0

    def test_std_empty(self) -> None:
        assert PerformanceScanner._std([]) == 0.0

    def test_max_drawdown_empty(self) -> None:
        assert PerformanceScanner._max_drawdown([]) == 0.0

    def test_max_drawdown_strictly_increasing(self) -> None:
        assert PerformanceScanner._max_drawdown([1.0, 2.0, 3.0]) == 0.0

    def test_max_drawdown_strictly_decreasing(self) -> None:
        """All-negative returns → cum keeps dropping, peak stays 0."""
        assert PerformanceScanner._max_drawdown([-3.0, -1.0, -2.0]) == 6.0


# ── Edge cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_all_zero_pnl(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        _seed_trades(journal, "flat", [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        result = scanner.scan_strategy("flat")
        assert result["sharpe"] == 0.0
        assert result["sortino"] == 0.0
        assert result["win_rate"] == 0.0
        assert result["max_drawdown"] == 0.0

    def test_mixed_pnl_types(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """None pnl handled safely — avg_return from pnl_pct which is None -> 0.0."""
        journal.record_trade({
            "strategy": "messy", "symbol": "X", "direction": "long", "pnl": None
        })
        journal.record_trade({
            "strategy": "messy", "symbol": "X", "direction": "long", "pnl": 100.0
        })
        result = scanner.scan_strategy("messy")
        assert result["trade_count"] == 2

    def test_alternating_wins_losses_payoff_ratio(self, scanner: PerformanceScanner, journal: EvolutionJournal) -> None:
        """Payoff ratio = abs(avg_win / avg_loss)."""
        _seed_trades(journal, "po", [100.0, -25.0, 100.0, -25.0], [2.0, -1.0, 2.0, -1.0])
        result = scanner.scan_strategy("po")
        # avg_win=2.0, avg_loss=-1.0
        assert result["payoff_ratio"] == pytest.approx(2.0)