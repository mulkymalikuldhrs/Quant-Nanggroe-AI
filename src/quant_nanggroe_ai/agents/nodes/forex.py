"""
Forex Agent — Currency Pair Analysis, Carry Trade & Central Bank Tracking
=========================================================================
Analyzes currency pairs with focus on central bank policy divergence,
carry trade opportunities, and economic calendar integration. Provides
forex-specific technical and fundamental analysis that supplements the
general analyst and macro agents.

Responsibilities:
  - Currency pair analysis (major, minor, exotic)
  - Central bank event tracking (FOMC, ECB, BoE, BoJ, RBA, RBNZ, BoC, SNB)
  - Carry trade identification (interest rate differentials)
  - Economic calendar integration for forex-specific events
  - Return forex_context, carry_trade_opportunities, cb_risk_level
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Central Bank Reference Data
# ══════════════════════════════════════════════════════════════════════

CENTRAL_BANKS: dict[str, dict[str, Any]] = {
    "USD": {
        "name": "Federal Reserve (Fed)",
        "rate_key": "DFF",
        "current_rate_approx": 5.33,
        "stance": "restrictive",
        "meeting_frequency": "6 weeks",
        "typical_meeting_days": [2],  # Wednesday
    },
    "EUR": {
        "name": "European Central Bank (ECB)",
        "rate_key": "ECBDFR",
        "current_rate_approx": 4.50,
        "stance": "restrictive",
        "meeting_frequency": "6 weeks",
        "typical_meeting_days": [3],  # Thursday
    },
    "GBP": {
        "name": "Bank of England (BoE)",
        "rate_key": "IUDSOIA",
        "current_rate_approx": 5.25,
        "stance": "restrictive",
        "meeting_frequency": "6 weeks",
        "typical_meeting_days": [3],  # Thursday
    },
    "JPY": {
        "name": "Bank of Japan (BoJ)",
        "rate_key": "IRSTCI01JPM156N",
        "current_rate_approx": -0.10,
        "stance": "ultra_accommodative",
        "meeting_frequency": "~6 weeks",
        "typical_meeting_days": [1, 2],  # Mon-Tue
    },
    "CHF": {
        "name": "Swiss National Bank (SNB)",
        "rate_key": "IRSTCI01CHM156N",
        "current_rate_approx": 1.75,
        "stance": "restrictive",
        "meeting_frequency": "quarterly",
        "typical_meeting_days": [3],  # Thursday
    },
    "AUD": {
        "name": "Reserve Bank of Australia (RBA)",
        "rate_key": "RBATCTR",
        "current_rate_approx": 4.35,
        "stance": "restrictive",
        "meeting_frequency": "monthly (except Jan)",
        "typical_meeting_days": [1],  # Tuesday
    },
    "NZD": {
        "name": "Reserve Bank of New Zealand (RBNZ)",
        "rate_key": "IRSTCI01NZM156N",
        "current_rate_approx": 5.50,
        "stance": "restrictive",
        "meeting_frequency": "~6 weeks",
        "typical_meeting_days": [2],  # Wednesday
    },
    "CAD": {
        "name": "Bank of Canada (BoC)",
        "rate_key": "IRSPPBICACM",
        "current_rate_approx": 5.00,
        "stance": "restrictive",
        "meeting_frequency": "~6 weeks",
        "typical_meeting_days": [2],  # Wednesday
    },
}

MAJOR_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "NZDUSD", "USDCAD",
}

MINOR_PAIRS = {
    "EURGBP", "EURJPY", "GBPJPY", "EURCHF",
    "EURAUD", "EURNZD", "GBPAUD", "GBPNZD",
    "GBPCAD", "EURCAD", "AUDJPY", "NZDJPY",
    "CADJPY", "CHFJPY", "AUDNZD", "AUDCAD",
    "NZDCAD", "NZDCHF", "AUDCHF",
}

EXOTIC_PREFIXES = ("USDTRY", "USDMXN", "USDZAR", "USDSGD", "USDNOK", "USDSEK", "USDDKK", "USDPLN", "USDCZK")


# ══════════════════════════════════════════════════════════════════════
# Carry Trade Constants
# ══════════════════════════════════════════════════════════════════════

MIN_INTEREST_RATE_DIFF = 2.0     # Minimum rate differential for carry trade
CARRY_TRADE_RISK_THRESHOLD = 3.0 # Rate diff above this increases roll risk
FUNDING_CURRENCIES = {"JPY", "CHF"}  # Traditional low-rate funding currencies
INVESTMENT_CURRENCIES = {"AUD", "NZD", "USD", "GBP"}  # Higher-rate currencies


# ══════════════════════════════════════════════════════════════════════
# Economic Calendar Constants
# ══════════════════════════════════════════════════════════════════════

FOREX_HIGH_IMPACT_EVENTS = [
    "FOMC Rate Decision",
    "ECB Rate Decision",
    "BoE Rate Decision",
    "BoJ Rate Decision",
    "RBA Rate Decision",
    "RBNZ Rate Decision",
    "BoC Rate Decision",
    "SNB Rate Decision",
    "Nonfarm Payrolls (NFP)",
    "CPI (Consumer Price Index)",
    "Retail Sales",
    "PMI Manufacturing",
    "GDP (Advance/Final)",
    "Unemployment Rate",
    "Trade Balance",
]

FOREX_MEDIUM_IMPACT_EVENTS = [
    "PPI (Producer Price Index)",
    "Durable Goods Orders",
    "Housing Starts",
    "Building Permits",
    "Consumer Confidence",
    "ISM Manufacturing",
    "ISM Services",
    "Current Account",
    "Industrial Production",
]


# ══════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════


def _is_forex_pair(symbol: str) -> bool:
    """Check if a symbol is a forex currency pair."""
    upper = symbol.upper()
    if upper in MAJOR_PAIRS or upper in MINOR_PAIRS:
        return True
    if any(upper.startswith(p) for p in EXOTIC_PREFIXES):
        return True
    # Generic 6-char check: two 3-letter currency codes
    if len(upper) == 6:
        forex_currencies = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"}
        base, quote = upper[:3], upper[3:6]
        if base in forex_currencies and quote in forex_currencies:
            return True
    return False


def _parse_pair(symbol: str) -> tuple[str, str]:
    """
    Parse a currency pair into base and quote currencies.

    Returns (base, quote) tuple. Empty strings if not parseable.
    """
    upper = symbol.upper()
    if len(upper) == 6:
        return upper[:3], upper[3:6]
    return "", ""


def _classify_pair(symbol: str) -> str:
    """Classify a forex pair as major, minor, or exotic."""
    upper = symbol.upper()
    if upper in MAJOR_PAIRS:
        return "major"
    if upper in MINOR_PAIRS:
        return "minor"
    if any(upper.startswith(p) for p in EXOTIC_PREFIXES):
        return "exotic"
    return "unknown"


def _compute_rate_differential(base: str, quote: str) -> float:
    """
    Compute the interest rate differential between two currencies.

    A positive differential means the base currency has a higher rate,
    making the pair a potential long carry trade.
    """
    base_rate = CENTRAL_BANKS.get(base, {}).get("current_rate_approx", 0.0)
    quote_rate = CENTRAL_BANKS.get(quote, {}).get("current_rate_approx", 0.0)
    return round(base_rate - quote_rate, 2)


def _identify_carry_trades() -> list[dict[str, Any]]:
    """
    Identify current carry trade opportunities.

    A carry trade involves borrowing in a low-rate (funding) currency
    and investing in a high-rate (investment) currency. The profit
    comes from the interest rate differential (positive carry).

    Returns list of carry trade opportunities sorted by rate differential.
    """
    opportunities: list[dict[str, Any]] = []

    for base in INVESTMENT_CURRENCIES:
        for quote in FUNDING_CURRENCIES:
            pair = f"{base}{quote}"
            diff = _compute_rate_differential(base, quote)

            if diff >= MIN_INTEREST_RATE_DIFF:
                # Assess carry risk
                if diff >= CARRY_TRADE_RISK_THRESHOLD:
                    risk = "HIGH_ROLL_RISK"
                else:
                    risk = "MODERATE"

                base_cb = CENTRAL_BANKS.get(base, {}).get("name", base)
                quote_cb = CENTRAL_BANKS.get(quote, {}).get("name", quote)

                opportunities.append({
                    "pair": pair,
                    "base_currency": base,
                    "quote_currency": quote,
                    "rate_differential": diff,
                    "base_rate": CENTRAL_BANKS.get(base, {}).get("current_rate_approx", 0.0),
                    "quote_rate": CENTRAL_BANKS.get(quote, {}).get("current_rate_approx", 0.0),
                    "base_central_bank": base_cb,
                    "quote_central_bank": quote_cb,
                    "base_stance": CENTRAL_BANKS.get(base, {}).get("stance", "unknown"),
                    "quote_stance": CENTRAL_BANKS.get(quote, {}).get("stance", "unknown"),
                    "direction": f"LONG {pair} (buy {base}, sell {quote})",
                    "carry_risk": risk,
                    "annual_carry_approx_pct": round(diff, 2),
                })

            # Also check reverse (short carry)
            reverse_pair = f"{quote}{base}"
            reverse_diff = -diff
            if reverse_diff >= MIN_INTEREST_RATE_DIFF:
                opportunities.append({
                    "pair": reverse_pair,
                    "base_currency": quote,
                    "quote_currency": base,
                    "rate_differential": reverse_diff,
                    "base_rate": CENTRAL_BANKS.get(quote, {}).get("current_rate_approx", 0.0),
                    "quote_rate": CENTRAL_BANKS.get(base, {}).get("current_rate_approx", 0.0),
                    "direction": f"LONG {reverse_pair} (buy {quote}, sell {base})",
                    "carry_risk": "MODERATE" if reverse_diff < CARRY_TRADE_RISK_THRESHOLD else "HIGH_ROLL_RISK",
                    "annual_carry_approx_pct": round(reverse_diff, 2),
                })

    # Sort by rate differential (highest first)
    opportunities.sort(key=lambda x: x["rate_differential"], reverse=True)
    return opportunities


def _get_upcoming_cb_events(days_ahead: int = 14) -> list[dict[str, Any]]:
    """
    Get upcoming central bank events.

    In production, this would query an economic calendar API.
    For now, generates a realistic assessment based on typical schedules.
    """
    upcoming: list[dict[str, Any]] = []
    today = datetime.now()

    for currency, cb_data in CENTRAL_BANKS.items():
        meeting_days = cb_data.get("typical_meeting_days", [])

        for i in range(days_ahead):
            future_date = today + timedelta(days=i)
            day_of_week = future_date.weekday()

            if day_of_week in meeting_days:
                # Approximate — not every matching day is an actual meeting
                # Only flag days within the first week as "possible"
                if i <= 7:
                    upcoming.append({
                        "event": f"{cb_data['name']} Meeting (possible)",
                        "currency": currency,
                        "date": future_date.strftime("%Y-%m-%d"),
                        "impact": "HIGH",
                        "current_stance": cb_data["stance"],
                        "days_until": i,
                    })

    # Sort by days_until
    upcoming.sort(key=lambda e: e["days_until"])
    return upcoming


def _assess_cb_risk(
    base: str,
    quote: str,
    upcoming_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Assess central bank risk for a currency pair.

    Risk is elevated when:
      - A CB meeting is imminent for either currency
      - Policy stances are diverging
      - Rate decisions are uncertain
    """
    base_events = [e for e in upcoming_events if e["currency"] == base]
    quote_events = [e for e in upcoming_events if e["currency"] == quote]

    base_stance = CENTRAL_BANKS.get(base, {}).get("stance", "unknown")
    quote_stance = CENTRAL_BANKS.get(quote, {}).get("stance", "unknown")

    # Check for imminent events (within 48 hours)
    base_imminent = any(e["days_until"] <= 2 for e in base_events)
    quote_imminent = any(e["days_until"] <= 2 for e in quote_events)

    # Divergence detection
    stances = {base_stance, quote_stance}
    diverging = False
    if "restrictive" in stances and "accommodative" in stances:
        diverging = True
    if "restrictive" in stances and "ultra_accommodative" in stances:
        diverging = True

    # Risk level
    if base_imminent or quote_imminent:
        risk_level = "HIGH"
        reason = "Central bank decision imminent — expect increased volatility"
    elif diverging:
        risk_level = "MEDIUM"
        reason = "Policy divergence detected — directional bias likely"
    elif base_events or quote_events:
        risk_level = "MEDIUM"
        reason = "Upcoming CB events within 2 weeks — monitor for shifts"
    else:
        risk_level = "LOW"
        reason = "No imminent CB events — standard risk environment"

    return {
        "risk_level": risk_level,
        "reason": reason,
        "base_stance": base_stance,
        "quote_stance": quote_stance,
        "diverging": diverging,
        "base_events_count": len(base_events),
        "quote_events_count": len(quote_events),
        "base_imminent": base_imminent,
        "quote_imminent": quote_imminent,
    }


def _analyze_currency_pair(symbol: str) -> dict[str, Any]:
    """
    Perform forex-specific analysis on a currency pair.

    Returns structured analysis with pair classification, rate differential,
    carry trade potential, and CB risk assessment.
    """
    base, quote = _parse_pair(symbol)
    pair_class = _classify_pair(symbol)

    if not base or not quote:
        return {
            "pair": symbol,
            "valid": False,
            "error": f"Could not parse forex pair: {symbol}",
        }

    rate_diff = _compute_rate_differential(base, quote)

    # Carry trade potential
    carry_potential = "NONE"
    if abs(rate_diff) >= MIN_INTEREST_RATE_DIFF:
        carry_potential = "LONG" if rate_diff > 0 else "SHORT"

    # Pip value estimation (for major pairs)
    pip_value = 10.0  # Standard lot pip value in USD for most major pairs
    if pair_class == "exotic":
        pip_value = 1.0  # Exotic pairs often have different pip values

    # Spread estimation (in pips)
    spread_estimate = {
        "major": 0.5,
        "minor": 2.0,
        "exotic": 15.0,
        "unknown": 5.0,
    }.get(pair_class, 5.0)

    return {
        "pair": symbol,
        "valid": True,
        "base": base,
        "quote": quote,
        "classification": pair_class,
        "rate_differential": rate_diff,
        "carry_potential": carry_potential,
        "pip_value": pip_value,
        "spread_estimate_pips": spread_estimate,
        "base_central_bank": CENTRAL_BANKS.get(base, {}).get("name", base),
        "quote_central_bank": CENTRAL_BANKS.get(quote, {}).get("name", quote),
    }


# ══════════════════════════════════════════════════════════════════════
# Forex Agent Node
# ══════════════════════════════════════════════════════════════════════


async def forex_node(state: AgentState) -> dict[str, Any]:
    """
    Forex Agent node — Currency pair analysis, carry trades & CB tracking.

    Analyzes forex-specific factors including central bank policy,
    interest rate differentials for carry trade identification, and
    economic calendar events that impact currency flows.
    """
    symbol = state.symbol or "EURUSD"
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Validate symbol is a forex pair ────────────────────────────
    if not _is_forex_pair(symbol):
        logger.info("Symbol %s is not a forex pair — forex agent skipping", symbol)
        return {
            "errors": state.errors,
            "agent_trace": state.agent_trace + [
                {
                    "agent": "forex",
                    "status": "skipped",
                    "reason": f"{symbol} is not a forex pair",
                    "timestamp": now,
                }
            ],
        }

    # ── 2. Analyze currency pair ──────────────────────────────────────
    pair_analysis = _analyze_currency_pair(symbol)
    if not pair_analysis.get("valid", False):
        errors.append(pair_analysis.get("error", "Invalid forex pair"))
        pair_analysis = {"pair": symbol, "valid": False}

    # ── 3. Identify carry trade opportunities ─────────────────────────
    carry_opportunities: list[dict[str, Any]] = []
    try:
        carry_opportunities = _identify_carry_trades()
    except Exception as exc:
        logger.error("Carry trade identification failed: %s", exc)
        errors.append(f"Carry trades: {exc}")

    # Check if current pair is a carry trade candidate
    current_pair_carry = [
        c for c in carry_opportunities
        if c["pair"] == symbol
    ]

    # ── 4. Check upcoming CB events ───────────────────────────────────
    upcoming_cb_events: list[dict[str, Any]] = []
    try:
        upcoming_cb_events = _get_upcoming_cb_events(days_ahead=14)
    except Exception as exc:
        logger.error("CB event check failed: %s", exc)
        errors.append(f"CB events: {exc}")

    # ── 5. Assess CB risk for the pair ────────────────────────────────
    base, quote = _parse_pair(symbol)
    cb_risk: dict[str, Any] = {}
    try:
        cb_risk = _assess_cb_risk(base, quote, upcoming_cb_events)
    except Exception as exc:
        logger.error("CB risk assessment failed for %s: %s", symbol, exc)
        errors.append(f"CB risk: {exc}")
        cb_risk = {"risk_level": "UNKNOWN", "reason": str(exc)}

    # ── 6. Build forex context string ─────────────────────────────────
    pair_class = pair_analysis.get("classification", "unknown")
    rate_diff = pair_analysis.get("rate_differential", 0.0)
    carry_potential = pair_analysis.get("carry_potential", "NONE")
    cb_risk_level = cb_risk.get("risk_level", "UNKNOWN")
    cb_risk_reason = cb_risk.get("reason", "")

    event_summary = ""
    if upcoming_cb_events:
        next_event = min(upcoming_cb_events, key=lambda e: e["days_until"])
        event_summary = f"Next CB event: {next_event['event']} ({next_event['days_until']}d away). "

    carry_summary = ""
    if current_pair_carry:
        c = current_pair_carry[0]
        carry_summary = f"Carry trade: {c['direction']} (diff={c['rate_differential']:.2f}%, risk={c['carry_risk']}). "

    forex_context = (
        f"Forex analysis for {symbol} ({pair_class}): "
        f"Rate diff: {rate_diff:+.2f}% | "
        f"Carry: {carry_potential} | "
        f"CB risk: {cb_risk_level} — {cb_risk_reason} | "
        f"{event_summary}"
        f"{carry_summary}"
        f"Base={base}({CENTRAL_BANKS.get(base, {}).get('stance', '?')}), "
        f"Quote={quote}({CENTRAL_BANKS.get(quote, {}).get('stance', '?')})"
    )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "macro_context": forex_context if not state.macro_context else (
            state.macro_context + " | " + forex_context
        ),
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "forex",
                "status": "completed",
                "action": "forex_analysis",
                "symbol": symbol,
                "pair_classification": pair_class,
                "rate_differential": rate_diff,
                "carry_potential": carry_potential,
                "cb_risk_level": cb_risk_level,
                "carry_opportunities_found": len(carry_opportunities),
                "upcoming_cb_events": len(upcoming_cb_events),
                "timestamp": now,
            }
        ],
    }
