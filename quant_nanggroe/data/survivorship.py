"""Survivorship bias detection for backtest data.

Detects whether a symbol universe exhibits survivorship bias by comparing
the current constituent list against historical records. When backtesting,
using today's index constituents biases results upward (only survivors remain).

Usage::

    detector = SurvivorshipBiasDetector()
    detector.record_universe("SP500", {"AAPL", "MSFT", "GOOGL"}, date="2024-01-01")
    report = detector.analyze("SP500")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class UniverseSnapshot:
    date: date
    symbols: Set[str]
    source: str = ""


@dataclass
class BiasReport:
    universe: str
    current_symbols: int
    historical_symbols: int
    survivors: int
    delisted: int
    survivorship_bias_pct: float
    is_biased: bool
    snapshots: List[dict] = field(default_factory=list)


class SurvivorshipBiasDetector:
    """Detects survivorship bias by tracking universe composition over time.

    A universe is biased if a significant portion of historically tracked
    symbols no longer exist in the current snapshot. The default threshold
    is 10% missing symbols.
    """

    def __init__(self, bias_threshold: float = 0.10) -> None:
        self._snapshots: Dict[str, List[UniverseSnapshot]] = {}
        self._bias_threshold = bias_threshold

    def record_universe(
        self,
        name: str,
        symbols: Set[str],
        snapshot_date: Optional[date] = None,
        source: str = "",
    ) -> None:
        """Record a universe composition at a point in time.

        Args:
            name: Universe identifier (e.g., "SP500", "NASDAQ100").
            symbols: Set of constituent symbols at this point in time.
            snapshot_date: Date of this snapshot. Defaults to today.
            source: Optional description of where this snapshot came from.
        """
        snap = UniverseSnapshot(
            date=snapshot_date or date.today(),
            symbols=frozenset(symbols),  # type: ignore[assignment]
            source=source,
        )
        self._snapshots.setdefault(name, []).append(snap)
        logger.info(
            "Recorded %s universe: %d symbols on %s",
            name, len(symbols), snap.date,
        )

    def get_universe(self, name: str) -> Optional[List[UniverseSnapshot]]:
        """Get all recorded snapshots for a universe."""
        return self._snapshots.get(name)

    def analyze(self, name: str) -> Optional[BiasReport]:
        """Analyze a universe for survivorship bias.

        Compares the earliest (historical) snapshot against the latest
        (current) snapshot. The proportion of symbols present historically
        but missing today indicates the survivorship bias risk.

        Returns ``None`` if fewer than 2 snapshots exist.
        """
        snaps = self._snapshots.get(name)
        if not snaps or len(snaps) < 2:
            return None

        snaps_sorted = sorted(snaps, key=lambda s: s.date)
        historical = snaps_sorted[0]
        current = snaps_sorted[-1]

        survivors = historical.symbols & current.symbols
        delisted = historical.symbols - current.symbols

        total_historical = len(historical.symbols)
        bias_pct = (len(delisted) / total_historical * 100) if total_historical else 0.0

        report = BiasReport(
            universe=name,
            current_symbols=len(current.symbols),
            historical_symbols=total_historical,
            survivors=len(survivors),
            delisted=len(delisted),
            survivorship_bias_pct=round(bias_pct, 2),
            is_biased=bias_pct > (self._bias_threshold * 100),
            snapshots=[
                {"date": s.date.isoformat(), "count": len(s.symbols), "source": s.source}
                for s in snaps_sorted
            ],
        )

        if report.is_biased:
            logger.warning(
                "Survivorship bias detected in %s: %.1f%% symbols delisted",
                name, bias_pct,
            )

        return report

    def clear(self) -> None:
        """Clear all recorded snapshots."""
        self._snapshots.clear()
