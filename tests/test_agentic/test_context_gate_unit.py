"""Unit tests for the macro/news context gate (no network, no MT5).

Tests the blackout-window math in
quant_nanggroe/engine/agentic/context_gate.py by stubbing
EconomicCalendar.get_high_impact_events with fake calendar data:
  - event within ±EVENT_BLACKOUT_MINUTES (30m) → vetoed
  - distant event → allowed
  - boundary ±30m vetoes, ±31m allows
  - provider outage → neutral until MAX_CONSECUTIVE_FAILURES, then fail-closed
  - result caching avoids provider refetch within TTL
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from quant_nanggroe.engine.agentic import context_gate
from quant_nanggroe.engine.agentic.context_gate import (
    EVENT_BLACKOUT_MINUTES,
    MAX_CONSECUTIVE_FAILURES,
    _parse_event_time,
    check_event_risk,
    reset_cache,
)


@pytest.fixture(autouse=True)
def _fresh_gate():
    reset_cache()
    yield
    reset_cache()


@pytest.fixture
def fake_calendar(monkeypatch):
    """Patch EconomicCalendar in the fundamental.calendar module."""
    import quant_nanggroe.engine.fundamental.calendar as cal_mod

    calls = {"n": 0, "failures_left": 0, "events": []}

    class FakeCalendar:
        def get_high_impact_events(self, days_ahead=1):
            calls["n"] += 1
            if calls["failures_left"] > 0:
                calls["failures_left"] -= 1
                raise ConnectionError("calendar provider down")
            return list(calls["events"])

    monkeypatch.setattr(cal_mod, "EconomicCalendar", FakeCalendar)
    return calls


def _ev(at: datetime, indicator: str = "NFP") -> dict:
    return {"indicator": indicator, "time": at.isoformat()}


def test_parse_event_time_variants():
    assert _parse_event_time(None) is None
    assert _parse_event_time("not-a-date") is None
    naive = datetime(2026, 1, 2, 12, 0, 0)
    parsed = _parse_event_time(naive)
    assert parsed is not None and parsed.tzinfo is not None
    aware = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    assert _parse_event_time(aware) == aware
    assert _parse_event_time("2026-01-02T12:00:00Z") == aware
    assert _parse_event_time(aware) is not None


def test_imminent_event_vetoes(fake_calendar):
    now = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    fake_calendar["events"] = [_ev(now + timedelta(minutes=10))]
    out = check_event_risk(now=now)
    assert out["vetoed"] is True
    assert "HIGH_IMPACT_EVENT" in out["reason"]
    assert "NFP" in out["reason"]
    assert out["events"] == 1


def test_distant_event_allows(fake_calendar):
    now = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    fake_calendar["events"] = [_ev(now + timedelta(hours=5))]
    out = check_event_risk(now=now)
    assert out["vetoed"] is False
    assert out["reason"] == ""


def test_blackout_boundary(fake_calendar):
    now = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    assert EVENT_BLACKOUT_MINUTES == 30
    for minutes in (30, -30, 0):
        reset_cache()
        fake_calendar["events"] = [_ev(now + timedelta(minutes=minutes))]
        assert check_event_risk(now=now)["vetoed"] is True
    for minutes in (31, -31, 120):
        reset_cache()
        fake_calendar["events"] = [_ev(now + timedelta(minutes=minutes))]
        assert check_event_risk(now=now)["vetoed"] is False


def test_outage_neutral_then_fail_closed(fake_calendar):
    now = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    fake_calendar["failures_left"] = 99  # provider stays down
    for _ in range(MAX_CONSECUTIVE_FAILURES - 1):
        out = check_event_risk(now=now)
        assert out["vetoed"] is False  # context filter: fail-open below threshold
    out = check_event_risk(now=now)
    assert out["vetoed"] is True  # breaker trips: fail-closed
    assert "CALENDAR_UNREACHABLE" in out["reason"]
    # recovery: one healthy read resets the breaker
    reset_cache()
    fake_calendar["failures_left"] = 0
    fake_calendar["events"] = []
    out = check_event_risk(now=now)
    assert out["vetoed"] is False


def test_result_cached_within_ttl(fake_calendar):
    now = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    fake_calendar["events"] = [_ev(now + timedelta(hours=6))]
    first = check_event_risk(now=now)
    second = check_event_risk(now=now)
    assert first == second
    assert fake_calendar["n"] == 1
