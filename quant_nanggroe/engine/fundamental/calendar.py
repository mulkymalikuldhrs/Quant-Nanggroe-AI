"""Economic Calendar — thin wrapper around engine/data/economic_calendar.

Provides economic event data, impact scoring, and pre-event analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class EconomicCalendar:
    """Economic calendar for fundamental event awareness."""

    def __init__(self):
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            try:
                # FINDING #12 fix: real provider lives in engine/macro/ — the
                # old import targeted engine/data/economic_calendar.py which
                # does not exist, so this wrapper silently returned [] forever.
                from quant_nanggroe.engine.macro.economic_calendar import (
                    EconomicCalendarProvider,
                )
                self._provider = EconomicCalendarProvider()
            except ImportError:
                return None
        return self._provider

    def get_today_events(self) -> List[Dict[str, Any]]:
        provider = self._get_provider()
        if provider is None:
            return []
        return provider.get_upcoming(days_ahead=1)

    def get_high_impact_events(
        self, days_ahead: int = 3
    ) -> List[Dict[str, Any]]:
        provider = self._get_provider()
        if provider is None:
            return []
        upcoming = provider.get_upcoming(days_ahead=days_ahead)
        return [e for e in upcoming if e.get("importance") == "high"]
