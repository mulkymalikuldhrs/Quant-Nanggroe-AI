"""Data freshness monitoring for Quant Nanggroe AI.

Tracks when each symbol/timeframe was last updated and reports stale data.
Integrates with the DataManager to provide per-symbol staleness checks.

Usage::

    monitor = DataFreshnessMonitor()
    monitor.record_fetch("BTC/USDT", TimeFrame.H1)
    report = monitor.get_stale_report(max_age_hours=2)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quant_nanggroe.types.market import TimeFrame

logger = logging.getLogger(__name__)

# Staleness thresholds for kill switch escalation (in minutes)
STALE_LEVEL_1_MINUTES = 5
STALE_LEVEL_2_MINUTES = 15
STALE_LEVEL_3_MINUTES = 60

# Expected max age per timeframe before a symbol is considered stale.
# These are generous to account for trading hours, weekends, etc.
DEFAULT_MAX_AGE_HOURS: Dict[TimeFrame, float] = {
    TimeFrame.M1: 0.05,   # ~3 minutes
    TimeFrame.M5: 0.15,   # ~9 minutes
    TimeFrame.M15: 0.4,   # ~24 minutes
    TimeFrame.M30: 0.75,  # ~45 minutes
    TimeFrame.H1: 1.5,
    TimeFrame.H4: 5,
    TimeFrame.D1: 28,
    TimeFrame.W1: 180,
    TimeFrame.MO1: 720,
}


@dataclass
class SymbolFreshness:
    symbol: str
    timeframe: TimeFrame
    last_updated: datetime
    age_hours: float
    is_stale: bool
    max_age_hours: float


@dataclass
class FreshnessReport:
    total_symbols: int = 0
    stale_count: int = 0
    fresh_count: int = 0
    unknown_count: int = 0
    per_symbol: List[SymbolFreshness] = field(default_factory=list)


class DataFreshnessMonitor:
    """Tracks data freshness across all symbols and timeframes.

    Thread-safe for concurrent access by multiple providers.
    """

    def __init__(self, kill_switch: Any = None) -> None:
        self._last_fetch: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        self._kill_switch = kill_switch

    def set_kill_switch(self, kill_switch: Any) -> None:
        """Bind a kill switch instance for auto-trigger on stale data."""
        self._kill_switch = kill_switch

    def _get_kill_switch(self) -> Any:
        """Lazy import and return the kill switch module types."""
        if self._kill_switch is None:
            return None
        return self._kill_switch

    def check_and_trigger_kill_switch(self, max_age_hours: Optional[float] = None) -> Optional[str]:
        """Check data freshness and trigger kill switch if data is stale.

        Thresholds (configurable via module constants):
        - > 5 min  stale -> LEVEL_1 (reduce position size)
        - > 15 min stale -> LEVEL_2 (close positions, stop new)
        - > 60 min stale -> LEVEL_3 (emergency halt)

        Returns the level triggered (as string), or None if no trigger.
        """
        from quant_nanggroe.engine.risk.kill_switch import KillSwitchLevel, KillSwitchTrigger

        ks = self._get_kill_switch()
        if ks is None:
            return None

        report = self.get_stale_report(max_age_hours=max_age_hours)
        if not report.per_symbol:
            return None

        now = datetime.now(timezone.utc)
        max_age_minutes = 0.0
        oldest_symbol = ""
        oldest_tf = ""

        for entry in report.per_symbol:
            age_min = (now - entry.last_updated).total_seconds() / 60.0
            if age_min > max_age_minutes:
                max_age_minutes = age_min
                oldest_symbol = entry.symbol
                oldest_tf = entry.timeframe.value if hasattr(entry.timeframe, 'value') else str(entry.timeframe)
                self._max_age_minutes = max_age_minutes

        if max_age_minutes > STALE_LEVEL_3_MINUTES:
            level = KillSwitchLevel.LEVEL_3
            age_str = f"{max_age_minutes:.0f}m"
        elif max_age_minutes > STALE_LEVEL_2_MINUTES:
            level = KillSwitchLevel.LEVEL_2
            age_str = f"{max_age_minutes:.0f}m"
        elif max_age_minutes > STALE_LEVEL_1_MINUTES:
            level = KillSwitchLevel.LEVEL_1
            age_str = f"{max_age_minutes:.0f}m"
        else:
            return None

        reason = (
            f"Data stale for {age_str} (oldest: {oldest_symbol} [{oldest_tf}]). "
            f"Max allowed: {STALE_LEVEL_1_MINUTES}m / {STALE_LEVEL_2_MINUTES}m / {STALE_LEVEL_3_MINUTES}m"
        )
        ks.activate(level=level, reason=reason, trigger=KillSwitchTrigger.DATA_STALE, auto_activated=True)
        logger.warning("Kill switch triggered at %s: %s", level.value, reason)
        return level.value

    def record_fetch(self, symbol: str, timeframe: TimeFrame) -> None:
        """Record that fresh data was fetched for a symbol at this timeframe."""
        key = timeframe.value
        self._last_fetch[symbol][key] = datetime.now(timezone.utc)
        logger.debug("Recorded fresh data for %s [%s]", symbol, key)

    def record_batch(self, symbols: List[str], timeframe: TimeFrame) -> None:
        """Record a batch fetch for multiple symbols at once."""
        now = datetime.now(timezone.utc)
        key = timeframe.value
        for symbol in symbols:
            self._last_fetch[symbol][key] = now

    def get_last_update(self, symbol: str, timeframe: TimeFrame) -> Optional[datetime]:
        """Get the last recorded update time for a symbol at a timeframe."""
        return self._last_fetch.get(symbol, {}).get(timeframe.value)

    def is_stale(self, symbol: str, timeframe: TimeFrame, max_age_hours: Optional[float] = None) -> Optional[bool]:
        """Check if a symbol is stale at a given timeframe.

        Returns ``None`` if no data has ever been fetched.
        """
        last = self.get_last_update(symbol, timeframe)
        if last is None:
            return None

        age = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        max_age = max_age_hours or DEFAULT_MAX_AGE_HOURS.get(timeframe, 24)
        return age > max_age

    def get_stale_report(self, max_age_hours: Optional[float] = None) -> FreshnessReport:
        """Generate a freshness report for all tracked symbols.

        If ``max_age_hours`` is set, it overrides all per-timeframe defaults.
        """
        report = FreshnessReport()
        now = datetime.now(timezone.utc)

        for symbol, tf_map in self._last_fetch.items():
            for tf_value, last_updated in tf_map.items():
                age = (now - last_updated).total_seconds() / 3600

                if max_age_hours is not None:
                    max_age = max_age_hours
                else:
                    tf = TimeFrame(tf_value)
                    max_age = DEFAULT_MAX_AGE_HOURS.get(tf, 24)

                is_stale = age > max_age
                if is_stale:
                    report.stale_count += 1
                else:
                    report.fresh_count += 1

                report.per_symbol.append(
                    SymbolFreshness(
                        symbol=symbol,
                        timeframe=TimeFrame(tf_value),
                        last_updated=last_updated,
                        age_hours=round(age, 3),
                        is_stale=is_stale,
                        max_age_hours=max_age,
                    )
                )
                report.total_symbols += 1

        return report

    def clear(self) -> None:
        """Clear all tracked freshness data."""
        self._last_fetch.clear()

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from tracking."""
        self._last_fetch.pop(symbol, None)
