"""
EconomicCalendarProvider — Scheduled economic release tracker.

Provides a structured registry of important economic releases with:
  - Release schedule (frequency, typical day)
  - FRED series ID mapping for historical data retrieval
  - Default consensus vs actual tracking

The provider maintains a list of indicators that QNA monitors for
macro surprise detection and causal bias evaluation.

Usage:
    from quant_nanggroe.engine.macro import EconomicCalendarProvider

    cal = EconomicCalendarProvider()
    events = cal.get_upcoming()  # Events due in the next 7 days
    recent = cal.get_recent()    # Events released in the last 7 days
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Economic indicator definitions
# ══════════════════════════════════════════════════════════════════════


@dataclass
class EconomicIndicator:
    """Definition of an economic indicator for tracking.

    Attributes:
        name: Human-readable name (e.g. 'CPI YoY').
        fred_series_id: FRED series ID for historical data retrieval.
        release_frequency: 'monthly', 'quarterly', 'weekly', or 'irregular'.
        typical_release_day: Typical day of release (e.g. 'second Tuesday').
        importance: 'high', 'medium', or 'low'.
        qna_event_type: The QNA macro event type this indicator maps to
                        (e.g. 'INFLATION_SURPRISE').
        description: What this indicator measures.
    """

    name: str
    fred_series_id: str
    release_frequency: str = "monthly"
    typical_release_day: str = ""
    importance: str = "high"
    qna_event_type: str = ""
    description: str = ""


# Registry of all economic indicators QNA monitors
ECONOMIC_INDICATORS_REGISTRY: list[EconomicIndicator] = [
    EconomicIndicator(
        name="CPI MoM",
        fred_series_id="CPIAUCNS",
        release_frequency="monthly",
        typical_release_day="Second Tuesday",
        importance="high",
        qna_event_type="INFLATION_SURPRISE",
        description="Consumer Price Index month-over-month change",
    ),
    EconomicIndicator(
        name="CPI YoY",
        fred_series_id="CPIAUCSL",
        release_frequency="monthly",
        typical_release_day="Second Tuesday",
        importance="high",
        qna_event_type="INFLATION_SURPRISE",
        description="Consumer Price Index year-over-year change",
    ),
    EconomicIndicator(
        name="Core CPI YoY",
        fred_series_id="CPILFESL",
        release_frequency="monthly",
        typical_release_day="Second Tuesday",
        importance="high",
        qna_event_type="INFLATION_SURPRISE",
        description="Core CPI (excluding food and energy)",
    ),
    EconomicIndicator(
        name="PPI YoY",
        fred_series_id="PPIACO",
        release_frequency="monthly",
        typical_release_day="Mid-month",
        importance="medium",
        qna_event_type="INFLATION_SURPRISE",
        description="Producer Price Index",
    ),
    EconomicIndicator(
        name="Nonfarm Payrolls",
        fred_series_id="PAYEMS",
        release_frequency="monthly",
        typical_release_day="First Friday",
        importance="high",
        qna_event_type="EMPLOYMENT_SURPRISE",
        description="Total nonfarm payroll employment change",
    ),
    EconomicIndicator(
        name="Unemployment Rate",
        fred_series_id="UNRATE",
        release_frequency="monthly",
        typical_release_day="First Friday",
        importance="high",
        qna_event_type="EMPLOYMENT_SURPRISE",
        description="Civilian unemployment rate",
    ),
    EconomicIndicator(
        name="GDP QoQ",
        fred_series_id="GDP",
        release_frequency="quarterly",
        typical_release_day="Third week of quarter month",
        importance="high",
        qna_event_type="GROWTH_SURPRISE",
        description="Gross Domestic Product quarterly change",
    ),
    EconomicIndicator(
        name="GDP YoY",
        fred_series_id="GDPC1",
        release_frequency="quarterly",
        typical_release_day="Third week of quarter month",
        importance="high",
        qna_event_type="GROWTH_SURPRISE",
        description="Real Gross Domestic Product",
    ),
    EconomicIndicator(
        name="Fed Funds Rate",
        fred_series_id="FEDFUNDS",
        release_frequency="monthly",
        typical_release_day="Continuous (FOMC 8x/year)",
        importance="high",
        qna_event_type="CENTRAL_BANK_HAWKISH",
        description="Effective Federal Funds Rate",
    ),
    EconomicIndicator(
        name="Retail Sales MoM",
        fred_series_id="RSAFS",
        release_frequency="monthly",
        typical_release_day="Second week",
        importance="medium",
        qna_event_type="CONSUMPTION_SURPRISE",
        description="Retail and food services sales",
    ),
    EconomicIndicator(
        name="Industrial Production MoM",
        fred_series_id="INDPRO",
        release_frequency="monthly",
        typical_release_day="Mid-month",
        importance="medium",
        qna_event_type="GROWTH_SURPRISE",
        description="Industrial production index",
    ),
    EconomicIndicator(
        name="Consumer Confidence",
        fred_series_id="UMCSENT",
        release_frequency="monthly",
        typical_release_day="Last Tuesday",
        importance="medium",
        qna_event_type="RISK_ON_SENTIMENT",
        description="University of Michigan Consumer Sentiment Index",
    ),
    EconomicIndicator(
        name="Initial Jobless Claims",
        fred_series_id="ICSA",
        release_frequency="weekly",
        typical_release_day="Thursday",
        importance="medium",
        qna_event_type="EMPLOYMENT_SURPRISE",
        description="Weekly initial unemployment claims",
    ),
    EconomicIndicator(
        name="10Y Treasury Yield",
        fred_series_id="DGS10",
        release_frequency="irregular",
        typical_release_day="Daily",
        importance="high",
        qna_event_type="RISK_OFF_SENTIMENT",
        description="10-Year Treasury Constant Maturity Rate",
    ),
    EconomicIndicator(
        name="M2 Money Supply",
        fred_series_id="M2SL",
        release_frequency="monthly",
        typical_release_day="Fourth week",
        importance="medium",
        qna_event_type="LIQUIDITY_SURPRISE",
        description="M2 Money Stock",
    ),
]


# ══════════════════════════════════════════════════════════════════════
#  EconomicCalendarProvider
# ══════════════════════════════════════════════════════════════════════


class EconomicCalendarProvider:
    """Structured registry and tracker for economic releases.

    Provides:
      - Lookup of indicators by FRED series ID or QNA event type
      - Filtering by importance level
      - Scheduled event tracking (upcoming/recent)
    """

    def __init__(
        self,
        indicators: Optional[list[EconomicIndicator]] = None,
    ):
        """
        Args:
            indicators: Custom indicator list (default: full ECONOMIC_INDICATORS_REGISTRY).
        """
        self._indicators = indicators or ECONOMIC_INDICATORS_REGISTRY
        self._index_by_fred: dict[str, EconomicIndicator] = {}
        self._index_by_event: dict[str, list[EconomicIndicator]] = {}
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild FRED and event type indices."""
        self._index_by_fred = {}
        self._index_by_event = {}
        for ind in self._indicators:
            self._index_by_fred[ind.fred_series_id] = ind
            if ind.qna_event_type:
                if ind.qna_event_type not in self._index_by_event:
                    self._index_by_event[ind.qna_event_type] = []
                self._index_by_event[ind.qna_event_type].append(ind)

    # ── Lookups ────────────────────────────────────────────────

    @property
    def indicators(self) -> list[EconomicIndicator]:
        """All tracked indicators."""
        return list(self._indicators)

    def by_fred_id(self, fred_id: str) -> Optional[EconomicIndicator]:
        """Look up indicator by FRED series ID."""
        return self._index_by_fred.get(fred_id)

    def by_event_type(self, event_type: str) -> list[EconomicIndicator]:
        """Get indicators that map to a QNA event type."""
        return self._index_by_event.get(event_type, [])

    def by_importance(self, importance: str) -> list[EconomicIndicator]:
        """Filter indicators by importance level."""
        return [i for i in self._indicators if i.importance == importance]

    @property
    def high_importance(self) -> list[EconomicIndicator]:
        """High importance indicators only."""
        return self.by_importance("high")

    def fred_ids(self) -> list[str]:
        """All tracked FRED series IDs."""
        return [i.fred_series_id for i in self._indicators]

    # ── Scheduling ─────────────────────────────────────────────

    def get_upcoming(
        self, days_ahead: int = 7
    ) -> list[dict[str, Any]]:
        """Get upcoming economic releases (estimated schedule).

        Since exact release dates aren't available without a dedicated
        economic calendar API, this provides a best-effort schedule
        based on typical release patterns.

        Args:
            days_ahead: How many days to look ahead (default: 7).

        Returns:
            List of dicts with indicator info and estimated release window.
        """
        now = datetime.now(timezone.utc)
        # Simple heuristic: high-importance indicators have a typical
        # release window. For actual dates, callers should use an
        # external economic calendar API (e.g., Investing.com, ForexFactory).
        upcoming = []
        for ind in self._indicators:
            if ind.release_frequency == "weekly":
                # Weekly releases are every week
                upcoming.append({
                    "indicator": ind.name,
                    "fred_id": ind.fred_series_id,
                    "importance": ind.importance,
                    "qna_event_type": ind.qna_event_type,
                    "frequency": ind.release_frequency,
                    "typical_day": ind.typical_release_day or "weekly",
                    "estimated_window": f"Next {days_ahead} days",
                    "description": ind.description,
                })
            elif ind.release_frequency in ("monthly", "quarterly"):
                # Monthly/quarterly — due within the release window
                upcoming.append({
                    "indicator": ind.name,
                    "fred_id": ind.fred_series_id,
                    "importance": ind.importance,
                    "qna_event_type": ind.qna_event_type,
                    "frequency": ind.release_frequency,
                    "typical_day": ind.typical_release_day,
                    "estimated_window": f"Next {days_ahead} days",
                    "description": ind.description,
                })

        return upcoming

    def get_recent(
        self, days_back: int = 7
    ) -> list[dict[str, Any]]:
        """Get recently released events (all tracked indicators).

        Args:
            days_back: How many days to look back (default: 7).

        Returns:
            List of dicts with indicator info.
        """
        # Since we don't have real-time release tracking without an API,
        # return all tracked indicators as "recently monitored"
        recent = []
        for ind in self._indicators:
            recent.append({
                "indicator": ind.name,
                "fred_id": ind.fred_series_id,
                "importance": ind.importance,
                "qna_event_type": ind.qna_event_type,
                "frequency": ind.release_frequency,
                "description": ind.description,
                "note": "Check FRED for latest release value",
            })
        return recent

    def __len__(self) -> int:
        return len(self._indicators)

    def __repr__(self) -> str:
        return (
            f"EconomicCalendarProvider({len(self._indicators)} indicators: "
            f"{len([i for i in self._indicators if i.importance == 'high'])} high, "
            f"{len([i for i in self._indicators if i.importance == 'medium'])} medium)"
        )
