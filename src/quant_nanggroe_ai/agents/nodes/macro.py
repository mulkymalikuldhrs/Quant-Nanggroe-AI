"""
Macro Analyst Agent — Economic indicators, calendar, and regime shifts.
========================================================================
Analyzes FRED economic indicators, checks the economic calendar for
scheduled events, detects macro regime shifts, and provides a macro
risk assessment that feeds into the trading graph.

Responsibilities:
  - Analyze FRED economic indicators (GDP, CPI, unemployment, rates)
  - Check economic calendar for scheduled high-impact events
  - Detect macro regime shifts (tightening/easing/neutral)
  - Return macro_context, macro_risk_level
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Macro Risk Level Enum
# ══════════════════════════════════════════════════════════════════════

MACRO_RISK_LOW = "LOW"
MACRO_RISK_MEDIUM = "MEDIUM"
MACRO_RISK_HIGH = "HIGH"
MACRO_RISK_EXTREME = "EXTREME"


# ══════════════════════════════════════════════════════════════════════
# FRED Economic Indicator Series
# ══════════════════════════════════════════════════════════════════════

FRED_INDICATORS = {
    "DFF": "Federal Funds Effective Rate",
    "DGS10": "10-Year Treasury Rate",
    "DGS2": "2-Year Treasury Rate",
    "T10Y2Y": "10Y-2Y Treasury Spread (Yield Curve)",
    "CPIAUCSL": "Consumer Price Index (CPI)",
    "UNRATE": "Unemployment Rate",
    "GDP": "Gross Domestic Product",
    "PAYEMS": "Nonfarm Payrolls",
    "PCE": "Personal Consumption Expenditures",
    "PPIFGS": "Producer Price Index",
    "VIXCLS": "CBOE Volatility Index (VIX)",
    "DEXUSEU": "USD/EUR Exchange Rate",
    "DEXCHUS": "CNY/USD Exchange Rate",
}


# ══════════════════════════════════════════════════════════════════════
# Economic Calendar — High-Impact Events
# ══════════════════════════════════════════════════════════════════════

HIGH_IMPACT_EVENTS = [
    "FOMC Meeting",
    "FOMC Rate Decision",
    "Nonfarm Payrolls (NFP)",
    "CPI (Consumer Price Index)",
    "GDP (Advance/Final)",
    "Unemployment Rate",
    "Retail Sales",
    "PMI Manufacturing",
    "PMI Services",
    "ECB Rate Decision",
    "BoE Rate Decision",
    "BoJ Rate Decision",
]


def _classify_symbol_zone(symbol: str) -> list[str]:
    """Return relevant economic zones based on the symbol."""
    upper = symbol.upper()
    zones = []

    # Crypto is global — watch USD and risk sentiment
    crypto_bases = {"BTC", "ETH", "SOL", "BNB", "XRP"}
    if any(upper.startswith(c) for c in crypto_bases) or "USDT" in upper:
        return ["USD", "GLOBAL"]

    # Commodities — USD driven
    if upper in {"XAUUSD", "XAGUSD"} or upper.startswith("XAU") or upper.startswith("XAG"):
        return ["USD", "COMMODITY"]

    # Forex pairs — extract both currencies
    forex_currencies = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"}
    if len(upper) == 6:
        base, quote = upper[:3], upper[3:6]
        if base in forex_currencies:
            zones.append(base)
        if quote in forex_currencies:
            zones.append(quote)

    # Equities — USD zone
    if not zones:
        zones.append("USD")

    return zones


async def _fetch_fred_indicators(series_ids: list[str]) -> dict[str, Any]:
    """
    Fetch latest values for FRED economic indicators.

    Uses the FRED API if the key is configured, otherwise returns
    a structured placeholder that degrades gracefully.
    """
    results: dict[str, Any] = {}

    try:
        from quant_nanggroe_ai.config import get_settings
        settings = get_settings()
        fred_api_key = settings.data_sources.fred_api_key

        if fred_api_key:
            import json as json_module
            import urllib.request

            for series_id in series_ids:
                try:
                    url = (
                        f"https://api.stlouisfed.org/fred/series/observations"
                        f"?series_id={series_id}"
                        f"&api_key={fred_api_key}"
                        f"&file_type=json"
                        f"&sort_order=desc"
                        f"&limit=5"
                    )
                    req = urllib.request.Request(url, headers={"User-Agent": "Quant-Nanggroe-AI"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json_module.loads(resp.read().decode())

                    observations = data.get("observations", [])
                    if observations:
                        latest = next(
                            (o for o in observations if o.get("value", ".") != "."),
                            None,
                        )
                        if latest:
                            results[series_id] = {
                                "value": float(latest["value"]),
                                "date": latest["date"],
                                "name": FRED_INDICATORS.get(series_id, series_id),
                            }
                except Exception as exc:
                    logger.debug("FRED fetch failed for %s: %s", series_id, exc)
                    results[series_id] = {
                        "value": None,
                        "error": str(exc),
                        "name": FRED_INDICATORS.get(series_id, series_id),
                    }
        else:
            # No API key — return structured placeholder
            for sid in series_ids:
                results[sid] = {
                    "value": None,
                    "name": FRED_INDICATORS.get(sid, sid),
                    "note": "FRED_API_KEY not configured",
                }

    except Exception as exc:
        logger.warning("FRED indicator fetch failed: %s", exc)
        for sid in series_ids:
            results[sid] = {
                "value": None,
                "error": str(exc),
                "name": FRED_INDICATORS.get(sid, sid),
            }

    return results


def _get_upcoming_events(days_ahead: int = 7) -> list[dict[str, Any]]:
    """
    Check for upcoming high-impact economic events.

    In production, this would query an economic calendar API.
    For now, it generates a realistic assessment based on the
    current day of the week and typical event schedules.
    """
    upcoming: list[dict[str, Any]] = []
    today = datetime.now()

    # Typical FOMC schedule: meetings roughly every 6 weeks
    # NFP: first Friday of each month
    # CPI: usually around the 10th-13th of each month

    for i in range(days_ahead):
        future_date = today + timedelta(days=i)
        day_of_week = future_date.weekday()  # 0=Mon, 4=Fri
        day_of_month = future_date.day

        # NFP — first Friday of the month
        if day_of_week == 4 and day_of_month <= 7:
            upcoming.append({
                "event": "Nonfarm Payrolls (NFP)",
                "date": future_date.strftime("%Y-%m-%d"),
                "impact": "HIGH",
                "currency": "USD",
                "days_until": i,
            })

        # CPI — around 10th-13th of the month
        if 10 <= day_of_month <= 13:
            upcoming.append({
                "event": "CPI (Consumer Price Index)",
                "date": future_date.strftime("%Y-%m-%d"),
                "impact": "HIGH",
                "currency": "USD",
                "days_until": i,
            })

        # FOMC — approximate dates (Wednesdays, ~6 weeks apart)
        if day_of_week == 2 and i <= 2:
            upcoming.append({
                "event": "FOMC Meeting (possible)",
                "date": future_date.strftime("%Y-%m-%d"),
                "impact": "HIGH",
                "currency": "USD",
                "days_until": i,
            })

    return upcoming


def _detect_monetary_policy_stance(indicators: dict[str, Any]) -> str:
    """
    Detect the current monetary policy stance from FRED indicators.

    Returns: "tightening", "easing", or "neutral"
    """
    # Use yield curve and fed funds rate as primary signals
    yield_curve = indicators.get("T10Y2Y", {})
    fed_funds = indicators.get("DFF", {})

    yc_val = yield_curve.get("value")
    ff_val = fed_funds.get("value")

    if yc_val is not None and ff_val is not None:
        # Inverted yield curve = tightening
        if yc_val < 0:
            return "tightening"
        # Very low rates + positive curve = easing
        if ff_val < 1.0 and yc_val > 0.5:
            return "easing"
        # Steep curve = potential easing
        if yc_val > 1.5:
            return "easing"

    return "neutral"


def _assess_macro_risk(
    policy_stance: str,
    upcoming_events: list[dict[str, Any]],
    indicators: dict[str, Any],
) -> tuple[str, str]:
    """
    Assess overall macro risk level.

    Returns (risk_level, risk_reason) tuple.
    """
    high_impact_soon = any(
        e["impact"] == "HIGH" and e["days_until"] <= 1
        for e in upcoming_events
    )

    yield_curve = indicators.get("T10Y2Y", {})
    yc_val = yield_curve.get("value")

    # Extreme risk: inverted yield curve + high-impact event imminent
    if yc_val is not None and yc_val < -0.5 and high_impact_soon:
        return MACRO_RISK_EXTREME, (
            f"Deeply inverted yield curve ({yc_val:.2f}%) + "
            f"high-impact event within 24h — extreme macro risk"
        )

    # High risk: tightening + upcoming events
    if policy_stance == "tightening" and high_impact_soon:
        return MACRO_RISK_HIGH, (
            "Monetary tightening + high-impact event imminent — "
            "elevated macro risk"
        )

    # High risk: inverted yield curve alone
    if yc_val is not None and yc_val < 0:
        return MACRO_RISK_HIGH, (
            f"Inverted yield curve ({yc_val:.2f}%) — recession signal, "
            f"high macro risk"
        )

    # Medium risk: any high-impact event within 3 days
    medium_impact = any(
        e["impact"] == "HIGH" and e["days_until"] <= 3
        for e in upcoming_events
    )
    if medium_impact:
        return MACRO_RISK_MEDIUM, (
            "High-impact economic event within 3 days — "
            "moderate macro risk, expect increased volatility"
        )

    # Low risk: easing + no imminent events
    if policy_stance == "easing" and not high_impact_soon:
        return MACRO_RISK_LOW, (
            "Accommodative monetary policy + no imminent high-impact events — "
            "low macro risk"
        )

    # Default: medium
    return MACRO_RISK_MEDIUM, (
        f"Monetary policy stance: {policy_stance}. "
        "Standard macro risk environment — maintain normal risk parameters."
    )


async def macro_node(state: AgentState) -> dict[str, Any]:
    """
    Macro Specialist Agent node.

    Analyzes FRED economic indicators, checks the economic calendar,
    detects macro regime shifts, and returns a macro risk assessment.
    """
    symbol = state.symbol or "SPY"
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Determine relevant economic zones ────────────────────────────
    zones = _classify_symbol_zone(symbol)

    # ── 2. Fetch relevant FRED indicators ───────────────────────────────
    # Select key indicators based on zones
    relevant_series = ["DFF", "DGS10", "DGS2", "T10Y2Y", "CPIAUCSL", "UNRATE", "VIXCLS"]
    if "EUR" in zones:
        relevant_series.append("DEXUSEU")

    indicators = await _fetch_fred_indicators(relevant_series)

    # ── 3. Check economic calendar ──────────────────────────────────────
    try:
        upcoming_events = _get_upcoming_events(days_ahead=7)
    except Exception as exc:
        logger.warning("Economic calendar check failed: %s", exc)
        upcoming_events = []
        errors.append(f"Economic calendar: {exc}")

    # ── 4. Detect monetary policy stance ───────────────────────────────
    policy_stance = _detect_monetary_policy_stance(indicators)

    # ── 5. Assess macro risk ───────────────────────────────────────────
    macro_risk_level, macro_risk_reason = _assess_macro_risk(
        policy_stance, upcoming_events, indicators,
    )

    # ── 6. Build macro context string ──────────────────────────────────
    zones_str = "/".join(zones)
    event_summary = ""
    if upcoming_events:
        next_event = min(upcoming_events, key=lambda e: e["days_until"])
        event_summary = (
            f"Next high-impact event: {next_event['event']} "
            f"({next_event['date']}, {next_event['days_until']}d away). "
        )

    # Format key indicator values
    indicator_parts = []
    for sid in ["DFF", "T10Y2Y", "VIXCLS", "UNRATE", "CPIAUCSL"]:
        ind = indicators.get(sid, {})
        val = ind.get("value")
        name = ind.get("name", sid)
        if val is not None:
            indicator_parts.append(f"{name}: {val}")

    indicators_str = "; ".join(indicator_parts) if indicator_parts else "FRED data unavailable (API key not configured)"

    macro_context = (
        f"Macro analysis for {symbol} (zone: {zones_str}): "
        f"Policy stance: {policy_stance}. "
        f"{event_summary}"
        f"Risk level: {macro_risk_level} — {macro_risk_reason}. "
        f"Key indicators: {indicators_str}"
    )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "macro_context": macro_context,
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "macro",
                "status": "completed",
                "action": "macro_analysis",
                "symbol": symbol,
                "zones": zones,
                "policy_stance": policy_stance,
                "macro_risk_level": macro_risk_level,
                "upcoming_events": len(upcoming_events),
                "timestamp": now,
            }
        ],
    }
