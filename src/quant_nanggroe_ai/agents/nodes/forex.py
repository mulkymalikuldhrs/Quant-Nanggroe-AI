"""
Forex Specialist Agent — Currency pair analysis, central bank policy, and FX structure.
======================================================================================
Analyzes forex-specific market data including interest rate differentials,
central bank policy divergence, carry trade dynamics, and currency correlations.

Responsibilities:
  - Analyze interest rate differentials between currency pairs
  - Assess central bank policy divergence
  - Calculate carry trade attractiveness
  - Evaluate currency correlation structure
  - Return forex_context for the trading graph
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Forex Risk Levels
# ══════════════════════════════════════════════════════════════════════

FOREX_RISK_LOW = "LOW"
FOREX_RISK_MEDIUM = "MEDIUM"
FOREX_RISK_HIGH = "HIGH"
FOREX_RISK_EXTREME = "EXTREME"


# ══════════════════════════════════════════════════════════════════════
# Currency Central Bank Reference Rates (approximate, updated periodically)
# ══════════════════════════════════════════════════════════════════════

CENTRAL_BANK_RATES: dict[str, dict[str, Any]] = {
    "USD": {"rate": 5.25, "bank": "Fed", "stance": "holding"},
    "EUR": {"rate": 4.50, "bank": "ECB", "stance": "holding"},
    "GBP": {"rate": 5.25, "bank": "BoE", "stance": "holding"},
    "JPY": {"rate": 0.10, "bank": "BoJ", "stance": "easing"},
    "CHF": {"rate": 1.75, "bank": "SNB", "stance": "holding"},
    "AUD": {"rate": 4.35, "bank": "RBA", "stance": "holding"},
    "NZD": {"rate": 5.50, "bank": "RBNZ", "stance": "holding"},
    "CAD": {"rate": 5.00, "bank": "BoC", "stance": "easing"},
}


# ══════════════════════════════════════════════════════════════════════
# Currency Classification
# ══════════════════════════════════════════════════════════════════════

MAJOR_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
}

CROSS_PAIRS = {
    "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "AUDJPY", "EURAUD", "GBPAUD",
    "GBPCAD", "EURCAD", "AUDNZD", "CADJPY", "CHFJPY",
}

EXOTIC_CURRENCIES = {
    "TRY", "ZAR", "MXN", "BRL", "SGD", "HKD", "NOK", "SEK", "DKK", "PLN",
    "CZK", "HUF", "THB", "MYR", "IDR", "PHP", "CNY",
}


def _classify_forex_pair(symbol: str) -> dict[str, Any]:
    """
    Classify a forex pair into categories.

    Returns classification with pair type, session info, and risk tier.
    """
    upper = symbol.upper().replace("/", "").replace("_", "")

    if upper in MAJOR_PAIRS:
        return {
            "pair_type": "major",
            "risk_tier": 1,
            "typical_daily_range_pips": 80,
            "liquidity": "VERY_HIGH",
            "session_overlap": "london_ny",
        }
    elif upper in CROSS_PAIRS:
        return {
            "pair_type": "cross",
            "risk_tier": 2,
            "typical_daily_range_pips": 120,
            "liquidity": "HIGH",
            "session_overlap": "london",
        }
    else:
        # Check for exotic
        for exotic in EXOTIC_CURRENCIES:
            if exotic in upper:
                return {
                    "pair_type": "exotic",
                    "risk_tier": 4,
                    "typical_daily_range_pips": 300,
                    "liquidity": "LOW",
                    "session_overlap": "regional",
                }
        return {
            "pair_type": "minor",
            "risk_tier": 3,
            "typical_daily_range_pips": 150,
            "liquidity": "MEDIUM",
            "session_overlap": "london",
        }


def _extract_currencies(symbol: str) -> tuple[str, str]:
    """
    Extract base and quote currencies from a forex pair symbol.

    Handles formats like EURUSD, EUR/USD, EUR_USD.
    """
    upper = symbol.upper().replace("/", "").replace("_", "")
    if len(upper) == 6:
        return upper[:3], upper[3:]
    return upper[:3], upper[3:6] if len(upper) >= 6 else ""


def _calculate_rate_differential(base: str, quote: str) -> dict[str, Any]:
    """
    Calculate interest rate differential between two currencies.

    This drives carry trade decisions and forward rate expectations.
    """
    base_info = CENTRAL_BANK_RATES.get(base, {"rate": 0.0, "bank": "Unknown", "stance": "unknown"})
    quote_info = CENTRAL_BANK_RATES.get(quote, {"rate": 0.0, "bank": "Unknown", "stance": "unknown"})

    base_rate = base_info["rate"]
    quote_rate = quote_info["rate"]
    differential = base_rate - quote_rate

    # Carry trade: buy high-yield, sell low-yield
    carry_attractive = differential > 1.0
    carry_cost = differential < -1.0

    return {
        "base_currency": base,
        "quote_currency": quote,
        "base_rate": base_rate,
        "quote_rate": quote_rate,
        "differential_bps": round(differential * 100, 1),
        "base_stance": base_info["stance"],
        "quote_stance": quote_info["stance"],
        "carry_attractive": carry_attractive,
        "carry_cost": carry_cost,
        "policy_divergence": abs(differential) > 2.0,
    }


def _assess_forex_risk(
    classification: dict[str, Any],
    rate_diff: dict[str, Any],
) -> tuple[str, str]:
    """
    Assess forex-specific risk level.

    Returns (risk_level, risk_reason) tuple.
    """
    pair_type = classification.get("pair_type", "minor")
    policy_divergence = rate_diff.get("policy_divergence", False)
    carry_cost = rate_diff.get("carry_cost", False)
    carry_attractive = rate_diff.get("carry_attractive", False)

    # Extreme risk: exotic pairs
    if pair_type == "exotic":
        return FOREX_RISK_EXTREME, (
            "Exotic currency pair — very wide spreads, low liquidity, "
            "and potential capital controls. Use minimal position sizes."
        )

    # High risk: policy divergence
    if policy_divergence:
        base = rate_diff.get("base_currency", "")
        quote = rate_diff.get("quote_currency", "")
        return FOREX_RISK_HIGH, (
            f"Significant policy divergence between {base} and {quote} "
            f"(differential: {rate_diff['differential_bps']:.0f} bps). "
            f"Expect increased volatility around central bank decisions."
        )

    # Medium risk: carry cost (paying to hold position)
    if carry_cost:
        return FOREX_RISK_MEDIUM, (
            f"Negative carry on this position (paying "
            f"{abs(rate_diff['differential_bps']):.0f} bps). "
            f"Position costs money to hold each day."
        )

    # Low risk: carry attractive major
    if pair_type == "major" and carry_attractive:
        return FOREX_RISK_LOW, (
            f"Major pair with positive carry ({rate_diff['differential_bps']:.0f} bps). "
            f"Favorable for carry trade strategy."
        )

    # Cross pair default
    if pair_type == "cross":
        return FOREX_RISK_MEDIUM, (
            f"Cross currency pair — may have wider spreads and "
            f"less predictable behavior during off-hours."
        )

    # Default: medium risk
    return FOREX_RISK_MEDIUM, (
        f"Standard forex risk environment for {pair_type} pair. "
        f"Monitor central bank communications for policy shifts."
    )


async def forex_node(state: AgentState) -> dict[str, Any]:
    """
    Forex Specialist Agent node.

    Analyzes forex-specific market data including interest rate
    differentials, central bank policy divergence, carry trade
    dynamics, and currency correlations.

    This node enriches the agent state with forex-specific context
    that is not captured by the generic analyst node.
    """
    symbol = state.symbol or "EURUSD"
    errors: list[str] = []

    # ── 1. Classify the forex pair ─────────────────────────────────────
    classification = _classify_forex_pair(symbol)

    # ── 2. Extract currencies and calculate rate differential ──────────
    base, quote = _extract_currencies(symbol)
    rate_diff = _calculate_rate_differential(base, quote)

    # ── 3. Assess forex risk ───────────────────────────────────────────
    forex_risk_level, forex_risk_reason = _assess_forex_risk(
        classification=classification,
        rate_diff=rate_diff,
    )

    # ── 4. Build forex context string ──────────────────────────────────
    pair_type = classification.get("pair_type", "unknown")
    carry_str = (
        f"Positive carry ({rate_diff['differential_bps']:.0f} bps)"
        if rate_diff.get("carry_attractive")
        else (
            f"Negative carry ({rate_diff['differential_bps']:.0f} bps)"
            if rate_diff.get("carry_cost")
            else f"Near-neutral carry ({rate_diff['differential_bps']:.0f} bps)"
        )
    )

    forex_context = (
        f"Forex analysis for {symbol} ({base}/{quote}, type: {pair_type}): "
        f"Rate differential: {base} {rate_diff['base_rate']:.2f}% vs "
        f"{quote} {rate_diff['quote_rate']:.2f}% "
        f"(diff: {rate_diff['differential_bps']:.0f} bps). "
        f"Policy stance: {rate_diff['base_stance']}/{rate_diff['quote_stance']}. "
        f"{carry_str}. "
        f"Risk level: {forex_risk_level} — {forex_risk_reason}. "
        f"Liquidity: {classification.get('liquidity', 'UNKNOWN')}. "
        f"Typical daily range: ~{classification.get('typical_daily_range_pips', 'N/A')} pips."
    )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "macro_context": (
            (state.macro_context + "\n" + forex_context)
            if state.macro_context
            else forex_context
        ),
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "forex",
                "status": "completed",
                "action": "forex_analysis",
                "symbol": symbol,
                "pair_type": pair_type,
                "base_currency": base,
                "quote_currency": quote,
                "rate_differential_bps": rate_diff["differential_bps"],
                "forex_risk_level": forex_risk_level,
                "carry_attractive": rate_diff.get("carry_attractive", False),
                "timestamp": datetime.now().isoformat(),
            }
        ],
    }
