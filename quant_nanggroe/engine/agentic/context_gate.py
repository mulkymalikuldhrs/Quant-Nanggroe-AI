"""Macro/News Context Gate — pre-trade event-risk veto.

Wires the (previously phantom) economic calendar into the LIVE decision path:
a high-importance release inside the blackout window vetoes NEW entries.
Classic institutional rule: no fresh risk minutes around red-folder events.

Design notes:
- Calendar unavailability → NEUTRAL (allow). This is a CONTEXT filter, not a
  constitutional guard — a broken calendar feed must not halt all trading.
- Once real calendar data shows an imminent high-impact event → VETO.
- Result cached for EVENT_RISK_CACHE_SECONDS to avoid per-symbol refetches.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("QNA.ContextGate")

# No new entries within ± this many minutes of a high-impact release.
EVENT_BLACKOUT_MINUTES = 30
EVENT_RISK_CACHE_SECONDS = 300.0

# R-F4 circuit breaker: NEUTRAL-on-outage is bounded. After this many
# consecutive provider failures the gate flips to VETO (fail-closed) until
# one successful read proves the calendar alive again.
MAX_CONSECUTIVE_FAILURES = 3

_cache_lock = threading.Lock()
_cached_result: Optional[Dict[str, Any]] = None
_cached_at: float = 0.0
_consecutive_failures: int = 0


def _parse_event_time(raw: Any) -> Optional[datetime]:
    """Best-effort parse of an event timestamp from calendar payloads."""
    if raw is None:
        return None
    try:
        if isinstance(raw, datetime):
            return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        text = str(raw)
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def check_event_risk(now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return {vetoed, reason, events} for the current blackout window.

    Fail-open on provider errors (context filter), fail-closed on DATA.
    """
    global _cached_result, _cached_at
    now = now or datetime.now(timezone.utc)

    with _cache_lock:
        if _cached_result is not None and (time.monotonic() - _cached_at) < EVENT_RISK_CACHE_SECONDS:
            return _cached_result

    events: List[Dict[str, Any]] = []
    vetoed = False
    reason = ""
    global _consecutive_failures
    try:
        from quant_nanggroe.engine.fundamental.calendar import EconomicCalendar
        cal = EconomicCalendar()
        events = cal.get_high_impact_events(days_ahead=1) or []
        _consecutive_failures = 0  # healthy read resets the breaker
    except Exception as exc:
        _consecutive_failures += 1
        logger.warning(
            "Context gate: calendar unavailable (%s) — failure %d/%d",
            exc, _consecutive_failures, MAX_CONSECUTIVE_FAILURES,
        )
        events = []
        if _consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            return {
                "vetoed": True,
                "reason": (
                    f"CALENDAR_UNREACHABLE: {_consecutive_failures} consecutive "
                    f"provider failures — event risk unverifiable (fail-closed)"
                ),
                "events": 0,
            }

    for ev in events:
        ev_time = _parse_event_time(
            ev.get("time") or ev.get("datetime") or ev.get("estimated_window")
        )
        if ev_time is None:
            continue
        delta_min = abs((ev_time - now).total_seconds()) / 60.0
        if delta_min <= EVENT_BLACKOUT_MINUTES:
            vetoed = True
            reason = (
                f"HIGH_IMPACT_EVENT: '{ev.get('indicator', 'unknown')}' "
                f"in {delta_min:.0f} min (blackout ±{EVENT_BLACKOUT_MINUTES}m)"
            )
            break

    result = {"vetoed": vetoed, "reason": reason, "events": len(events)}
    with _cache_lock:
        _cached_result = result
        _cached_at = time.monotonic()
    if vetoed:
        logger.warning("Context gate VETO: %s", reason)
    return result


def reset_cache() -> None:
    """Test hook / periodic refresh."""
    global _cached_result, _cached_at, _consecutive_failures
    with _cache_lock:
        _cached_result = None
        _cached_at = 0.0
        _consecutive_failures = 0
