"""Tests: macro/news context gate — high-impact event vetoes new entries.

Calendar unavailability = NEUTRAL (context filter, not constitutional).
Imminent high-impact event = VETO.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from quant_nanggroe.engine.agentic import context_gate


class TestContextGate(unittest.TestCase):
    def setUp(self):
        context_gate.reset_cache()

    def tearDown(self):
        context_gate.reset_cache()

    def test_no_events_allows_trading(self):
        with patch(
            "quant_nanggroe.engine.fundamental.calendar.EconomicCalendar.get_high_impact_events",
            return_value=[],
        ):
            r = context_gate.check_event_risk()
        self.assertFalse(r["vetoed"])

    def _ev(self, when: datetime) -> dict:
        return {"indicator": "NFP", "importance": "high",
                "time": when.isoformat()}

    def test_imminent_high_impact_event_vetoes(self):
        now = datetime.now(timezone.utc)
        soon = now + timedelta(minutes=10)
        with patch(
            "quant_nanggroe.engine.fundamental.calendar.EconomicCalendar.get_high_impact_events",
            return_value=[self._ev(soon)],
        ):
            r = context_gate.check_event_risk()
        self.assertTrue(r["vetoed"])
        self.assertIn("NFP", r["reason"])

    def test_recent_high_impact_event_vetoes(self):
        now = datetime.now(timezone.utc)
        just_passed = now - timedelta(minutes=15)
        with patch(
            "quant_nanggroe.engine.fundamental.calendar.EconomicCalendar.get_high_impact_events",
            return_value=[self._ev(just_passed)],
        ):
            r = context_gate.check_event_risk()
        self.assertTrue(r["vetoed"])

    def test_distant_event_allows(self):
        now = datetime.now(timezone.utc)
        far = now + timedelta(hours=6)
        with patch(
            "quant_nanggroe.engine.fundamental.calendar.EconomicCalendar.get_high_impact_events",
            return_value=[self._ev(far)],
        ):
            r = context_gate.check_event_risk()
        self.assertFalse(r["vetoed"])

    def test_calendar_failure_is_neutral_not_veto(self):
        with patch(
            "quant_nanggroe.engine.fundamental.calendar.EconomicCalendar.get_high_impact_events",
            side_effect=RuntimeError("feed down"),
        ):
            r = context_gate.check_event_risk()
        self.assertFalse(r["vetoed"], "broken calendar feed must NOT veto")

    def test_unparsable_time_ignored(self):
        with patch(
            "quant_nanggroe.engine.fundamental.calendar.EconomicCalendar.get_high_impact_events",
            return_value=[{"indicator": "CPI", "importance": "high", "time": "garbage"}],
        ):
            r = context_gate.check_event_risk()
        self.assertFalse(r["vetoed"])


class TestCalendarWrapperRealProvider(unittest.TestCase):
    """FINDING #12: wrapper must reach the REAL provider (engine/macro)."""

    def test_wrapper_gets_real_provider(self):
        from quant_nanggroe.engine.fundamental.calendar import EconomicCalendar
        cal = EconomicCalendar()
        provider = cal._get_provider()
        self.assertIsNotNone(provider)
        events = cal.get_high_impact_events(days_ahead=3)
        self.assertIsInstance(events, list)


if __name__ == "__main__":
    unittest.main()
