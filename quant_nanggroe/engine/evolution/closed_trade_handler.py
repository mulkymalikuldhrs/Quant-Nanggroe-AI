"""ClosedTradeHandler — record and query closed trades in evolution journal.

Thin wrapper over EvolutionJournal with strategy-level stats queries.
"""

from __future__ import annotations

from typing import Any, Optional

from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal


class ClosedTradeHandler:
    """Record and query closed trades from the evolution journal."""

    def __init__(self, journal: Optional[EvolutionJournal] = None) -> None:
        self._journal = journal or EvolutionJournal()

    # ── Write ─────────────────────────────────────────────────────────

    def record_trade(self, trade: dict[str, Any]) -> int:
        """Store a closed trade in the journal.

        Expected keys (all optional except strategy/direction/symbol):
            strategy, symbol, direction, entry_price, exit_price, pnl,
            pnl_pct, hold_hours, spread, entry_reason, sl_type, tags, timestamp
        """
        return self._journal.record_trade(trade)

    # ── Read ──────────────────────────────────────────────────────────

    def get_recent_trades(
        self, strategy_name: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Return most recent closed trades for a strategy."""
        return self._journal.get_recent_trades(strategy_name, limit)

    def get_strategy_stats(self, strategy_name: str) -> dict[str, Any]:
        """Return aggregate stats for a strategy.

        Returns dict with trade_count, wins, losses, win_rate, avg_pnl,
        avg_pnl_pct. Falls back to journal's basic stats.
        """
        return self._journal.get_strategy_stats(strategy_name)

    def get_all_trades(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Return recent trades across all strategies."""
        return self._journal.all_trades(limit)
