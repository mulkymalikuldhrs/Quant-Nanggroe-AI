"""Economic Calendar — thin wrapper around engine/data/economic_calendar.

Provides economic event data, impact scoring, and pre-event analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EconomicCalendar:
    """Economic calendar for fundamental event awareness."""

    def __init__(self):
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            from quant_nanggroe.engine.data.economic_calendar import EconomicCalendarData
            self._provider = EconomicCalendarData()
        return self._provider

    def get_today_events(self) -> List[Dict[str, Any]]:
        provider = self._get_provider()
        return provider.get_today_events()

    def get_high_impact_events(
        self, days_ahead: int = 3
    ) -> List[Dict[str, Any]]:
        provider = self._get_provider()
        return provider.get_high_impact_events(days_ahead=days_ahead)
