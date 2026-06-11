"""
Prediction Market Agent — Polymarket/Kalshi Integration & Cross-Market Hedging
================================================================================
Integrates with Polymarket and Kalshi prediction markets for probability
estimation, cross-market hedging against traditional positions, and smart
contract interaction. Estimates probabilities from multiple sources and
identifies opportunities where prediction market odds diverge from
model-implied probabilities.

Responsibilities:
  - Polymarket/Kalshi integration for market discovery and execution
  - Probability estimation from multiple sources (market odds, models, news)
  - Cross-market hedging (prediction market vs traditional market positions)
  - Smart contract interaction via ethers/web3
  - Return prediction_context, probability_estimates, hedge_opportunities
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Prediction Market Platform Configuration
# ══════════════════════════════════════════════════════════════════════

class PredictionPlatform:
    """Represents a prediction market platform with its characteristics."""

    def __init__(
        self,
        name: str,
        chain: str,
        settlement_time_hours: float,
        min_bet: float,
        max_bet: float,
        fee_pct: float,
        smart_contract_support: bool,
    ) -> None:
        self.name = name
        self.chain = chain
        self.settlement_time_hours = settlement_time_hours
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.fee_pct = fee_pct
        self.smart_contract_support = smart_contract_support


PLATFORMS: dict[str, PredictionPlatform] = {
    "polymarket": PredictionPlatform(
        name="Polymarket",
        chain="polygon",
        settlement_time_hours=1.0,
        min_bet=1.0,
        max_bet=50000.0,
        fee_pct=0.0,
        smart_contract_support=True,
    ),
    "kalshi": PredictionPlatform(
        name="Kalshi",
        chain="none",  # CFTC-regulated, not on-chain
        settlement_time_hours=24.0,
        min_bet=1.0,
        max_bet=25000.0,
        fee_pct=0.0,
        smart_contract_support=False,
    ),
    "metaculus": PredictionPlatform(
        name="Metaculus",
        chain="none",  # Non-monetary forecasting platform
        settlement_time_hours=0.0,
        min_bet=0.0,
        max_bet=0.0,
        fee_pct=0.0,
        smart_contract_support=False,
    ),
    "manifold": PredictionPlatform(
        name="Manifold Markets",
        chain="none",
        settlement_time_hours=1.0,
        min_bet=1.0,
        max_bet=10000.0,
        fee_pct=0.0,
        smart_contract_support=False,
    ),
}


# ══════════════════════════════════════════════════════════════════════
# Probability Estimation Constants
# ══════════════════════════════════════════════════════════════════════

# Minimum edge to consider a prediction market trade
MIN_PROBABILITY_EDGE = 0.05       # 5% edge required
MIN_LIQUIDITY_USD = 1000.0        # Minimum market liquidity
MIN_VOLUME_USD = 500.0            # Minimum 24h volume
MAX_MARKET_AGE_DAYS = 90          # Don't trade markets older than 90 days
CROSS_HEDGE_MIN_CORRELATION = 0.6 # Minimum correlation for cross-market hedging


# ══════════════════════════════════════════════════════════════════════
# Cross-Market Hedging Configuration
# ══════════════════════════════════════════════════════════════════════

# Mapping of prediction market topics to tradable instruments
TOPIC_INSTRUMENT_MAP: dict[str, dict[str, Any]] = {
    "fed_rate_hike": {
        "traditional_instrument": "Fed Funds Futures (ZQ)",
        "correlation": 0.90,
        "direction": "same",  # If YES on rate hike, go long futures
    },
    "recession_2024": {
        "traditional_instrument": "SPY Put Options",
        "correlation": 0.75,
        "direction": "inverse",  # If YES on recession, buy puts
    },
    "btc_100k": {
        "traditional_instrument": "BTCUSDT Perpetual",
        "correlation": 0.85,
        "direction": "same",
    },
    "election_outcome": {
        "traditional_instrument": "USD Index (DXY)",
        "correlation": 0.50,
        "direction": "variable",
    },
    "oil_price_100": {
        "traditional_instrument": "Crude Oil Futures (CL)",
        "correlation": 0.90,
        "direction": "same",
    },
    "inflation_above_3": {
        "traditional_instrument": "TIPS ETF (TIP)",
        "correlation": 0.70,
        "direction": "inverse",
    },
}


# ══════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════


def _is_prediction_market_query(symbol: str) -> bool:
    """
    Check if a symbol/query relates to prediction markets.

    Prediction market symbols often contain descriptive keywords rather
    than standard ticker symbols.
    """
    upper = symbol.upper()
    prediction_keywords = {
        "PREDICT", "POLYMARKET", "KALSHI", "ELECTION",
        "RATE", "HIKE", "CUT", "RECESSION", "BTC100K",
        "INFLATION", "GDP", "YES", "NO",
    }
    return any(kw in upper for kw in prediction_keywords)


async def _discover_markets(query: str) -> list[dict[str, Any]]:
    """
    Discover prediction markets matching a query.

    Uses the PolymarketBroker for Polymarket integration and
    can be extended for other platforms.

    Returns list of market dicts with question, prices, and metadata.
    """
    markets: list[dict[str, Any]] = []

    try:
        from quant_nanggroe_ai.execution.polymarket import PolymarketBroker

        broker = PolymarketBroker()
        polymarket_results = await broker.get_markets(query=query, limit=10)

        for market in polymarket_results:
            # Extract probability from market prices
            yes_price = 0.0
            for outcome in market.outcomes:
                if outcome.outcome.upper() == "YES":
                    yes_price = outcome.price
                    break

            markets.append({
                "platform": "polymarket",
                "question": market.question,
                "condition_id": market.condition_id,
                "yes_price": yes_price,
                "implied_probability": round(yes_price, 4),
                "volume": market.volume,
                "liquidity": market.liquidity,
                "category": market.category,
                "end_date": market.end_date,
                "active": market.active,
            })

    except Exception as exc:
        logger.warning("Polymarket discovery failed: %s", exc)

    # Also add Kalshi placeholder results
    # In production, this would use the Kalshi API
    if not markets:
        markets.append({
            "platform": "placeholder",
            "question": f"Prediction markets for: {query}",
            "note": "No live markets found — API credentials may be required",
            "status": "no_results",
        })

    return markets


async def _estimate_probability(
    market_question: str,
    market_yes_price: float = 0.5,
) -> dict[str, Any]:
    """
    Estimate probability from multiple sources.

    Sources:
      1. Market-implied probability (from YES share price)
      2. Model-based estimation (simplified Bayesian)
      3. News/sentiment adjustment

    Returns a blended probability estimate with confidence bounds.
    """
    # Source 1: Market-implied probability
    market_prob = market_yes_price

    # Source 2: Model-based (simplified — in production, use proper models)
    # Use the market price as a prior, adjusted by available information
    model_prob = market_prob  # Placeholder for model-based estimation

    # Source 3: Sentiment adjustment
    # In production, this would use the sentiment tool
    sentiment_adjustment = 0.0  # Neutral adjustment

    # Blended estimate (weighted average)
    blended = (
        market_prob * 0.50        # Market weight
        + model_prob * 0.30       # Model weight
        + (market_prob + sentiment_adjustment) * 0.20  # Sentiment-adjusted weight
    )

    # Clamp to [0.01, 0.99] — never 0 or 1 in prediction markets
    blended = max(0.01, min(0.99, blended))

    # Confidence interval (wider when sources disagree)
    source_spread = abs(market_prob - model_prob)
    confidence_width = max(0.05, source_spread * 2 + 0.05)

    return {
        "market_implied": round(market_prob, 4),
        "model_estimate": round(model_prob, 4),
        "sentiment_adjustment": round(sentiment_adjustment, 4),
        "blended_estimate": round(blended, 4),
        "confidence_lower": round(max(0.01, blended - confidence_width), 4),
        "confidence_upper": round(min(0.99, blended + confidence_width), 4),
        "confidence_width": round(confidence_width, 4),
        "sources_agree": source_spread < 0.05,
    }


def _find_cross_hedge_opportunities(
    market_question: str,
    estimated_probability: float,
    market_yes_price: float,
) -> list[dict[str, Any]]:
    """
    Identify cross-market hedging opportunities.

    A cross-market hedge exists when a prediction market position can
    be partially offset by a position in a correlated traditional market,
    reducing directional risk while capturing the edge.

    Returns list of hedge opportunities.
    """
    opportunities: list[dict[str, Any]] = []
    question_lower = market_question.lower()

    for topic, mapping in TOPIC_INSTRUMENT_MAP.items():
        # Check if the market question relates to this topic
        topic_keywords = topic.replace("_", " ").split()
        if not any(kw in question_lower for kw in topic_keywords):
            continue

        correlation = mapping["correlation"]
        if correlation < CROSS_HEDGE_MIN_CORRELATION:
            continue

        # Calculate edge
        edge = abs(estimated_probability - market_yes_price)

        # Determine hedge direction
        direction = mapping["direction"]
        traditional_instrument = mapping["traditional_instrument"]

        # If prediction market is underpriced (YES < estimated), go long YES
        # Hedge with traditional position based on correlation
        if market_yes_price < estimated_probability:
            pm_side = "BUY_YES"
            if direction == "same":
                trad_side = "LONG"
            elif direction == "inverse":
                trad_side = "SHORT"
            else:
                trad_side = "NEUTRAL"
        else:
            pm_side = "SELL_YES"  # Or BUY_NO
            if direction == "same":
                trad_side = "SHORT"
            elif direction == "inverse":
                trad_side = "LONG"
            else:
                trad_side = "NEUTRAL"

        # Calculate hedge ratio (simplified Kelly-inspired)
        # Hedge more when correlation is higher
        hedge_ratio = correlation * 0.5  # Conservative: half of correlation

        opportunities.append({
            "topic": topic,
            "prediction_market_side": pm_side,
            "traditional_instrument": traditional_instrument,
            "traditional_side": trad_side,
            "correlation": correlation,
            "edge": round(edge, 4),
            "hedge_ratio": round(hedge_ratio, 4),
            "direction": direction,
            "description": (
                f"Hedge {pm_side} on prediction market with "
                f"{trad_side} {traditional_instrument} "
                f"(correlation={correlation:.2f}, hedge_ratio={hedge_ratio:.2f})"
            ),
        })

    # Sort by edge (highest first)
    opportunities.sort(key=lambda o: o["edge"], reverse=True)
    return opportunities


async def _smart_contract_read(
    condition_id: str,
    platform: str = "polymarket",
) -> dict[str, Any]:
    """
    Read smart contract state for a prediction market.

    Uses ethers/web3 to query on-chain data for market resolution
    status, token balances, and other contract state.

    In production, this uses:
      - ethers.js (via subprocess or py-eth)
      - web3.py for direct contract interaction

    Returns dict with on-chain market state.
    """
    result: dict[str, Any] = {
        "condition_id": condition_id,
        "platform": platform,
        "status": "unknown",
    }

    if platform == "polymarket":
        try:
            # Polymarket uses CTF (Conditional Token Framework) on Polygon
            # In production: query CTF contract for condition resolution
            result.update({
                "chain": "polygon",
                "contract_type": "CTF",
                "resolution_status": "unresolved",  # Placeholder
                "note": "On-chain read requires web3.py or ethers.js with Polygon RPC",
            })
        except Exception as exc:
            logger.warning("Smart contract read failed for %s: %s", condition_id[:8], exc)
            result["error"] = str(exc)
    elif platform == "kalshi":
        # Kalshi is CFTC-regulated, not on-chain
        result.update({
            "chain": "none",
            "note": "Kalshi is a regulated exchange — no smart contract interaction",
            "api_query_required": True,
        })

    return result


def _validate_prediction_market_trade(
    yes_price: float,
    estimated_probability: float,
    market_volume: float = 0.0,
    market_liquidity: float = 0.0,
) -> dict[str, Any]:
    """
    Validate whether a prediction market trade meets our criteria.

    Checks:
      1. Price is in valid range [0.01, 0.99]
      2. Sufficient edge exists (probability vs price)
      3. Sufficient liquidity
      4. Sufficient volume

    Returns dict with validation results.
    """
    checks: dict[str, dict[str, Any]] = {}

    # 1. Price range check
    checks["price_range"] = {
        "name": "price_range",
        "value": f"{yes_price:.4f}",
        "limit": "[0.01, 0.99]",
        "passed": 0.01 <= yes_price <= 0.99,
    }

    # 2. Edge check
    edge = abs(estimated_probability - yes_price)
    checks["edge"] = {
        "name": "edge",
        "value": f"{edge:.4f}",
        "limit": f"{MIN_PROBABILITY_EDGE:.4f}",
        "passed": edge >= MIN_PROBABILITY_EDGE,
    }

    # 3. Liquidity check
    checks["liquidity"] = {
        "name": "liquidity",
        "value": f"${market_liquidity:.0f}",
        "limit": f"${MIN_LIQUIDITY_USD:.0f}",
        "passed": market_liquidity >= MIN_LIQUIDITY_USD,
    }

    # 4. Volume check
    checks["volume"] = {
        "name": "volume",
        "value": f"${market_volume:.0f}",
        "limit": f"${MIN_VOLUME_USD:.0f}",
        "passed": market_volume >= MIN_VOLUME_USD,
    }

    all_passed = all(c["passed"] for c in checks.values())
    failed = [k for k, c in checks.items() if not c["passed"]]

    return {
        "checks": checks,
        "all_passed": all_passed,
        "failed_checks": failed,
        "edge": round(edge, 4),
        "verdict": "PASS" if all_passed else "FAIL",
    }


# ══════════════════════════════════════════════════════════════════════
# Prediction Market Agent Node
# ══════════════════════════════════════════════════════════════════════


async def prediction_market_node(state: AgentState) -> dict[str, Any]:
    """
    Prediction Market Agent node — Polymarket/Kalshi integration & cross-market hedging.

    Discovers relevant prediction markets, estimates probabilities from
    multiple sources, identifies cross-market hedging opportunities,
    and validates trades against prediction market-specific criteria.
    """
    symbol = state.symbol or "SPY"
    query = state.query or state.symbol or "market"
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Discover prediction markets ────────────────────────────────
    discovered_markets: list[dict[str, Any]] = []
    try:
        discovered_markets = await _discover_markets(query)
    except Exception as exc:
        logger.error("Market discovery failed: %s", exc)
        errors.append(f"Market discovery: {exc}")
        discovered_markets = []

    # ── 2. Estimate probabilities for discovered markets ──────────────
    probability_estimates: list[dict[str, Any]] = []
    for market in discovered_markets[:5]:  # Limit to top 5
        if market.get("status") == "no_results":
            continue

        try:
            yes_price = market.get("yes_price", 0.5)
            prob_estimate = await _estimate_probability(
                market_question=market.get("question", ""),
                market_yes_price=yes_price,
            )
            probability_estimates.append({
                "question": market.get("question", ""),
                "platform": market.get("platform", "unknown"),
                "yes_price": yes_price,
                "probability": prob_estimate,
            })
        except Exception as exc:
            logger.warning("Probability estimation failed: %s", exc)
            errors.append(f"Probability estimation: {exc}")

    # ── 3. Identify cross-market hedging opportunities ────────────────
    hedge_opportunities: list[dict[str, Any]] = []
    for est in probability_estimates:
        try:
            hedges = _find_cross_hedge_opportunities(
                market_question=est["question"],
                estimated_probability=est["probability"]["blended_estimate"],
                market_yes_price=est["yes_price"],
            )
            hedge_opportunities.extend(hedges)
        except Exception as exc:
            logger.warning("Cross-hedge identification failed: %s", exc)
            errors.append(f"Cross-hedge: {exc}")

    # ── 4. Validate prediction market trades ──────────────────────────
    trade_validations: list[dict[str, Any]] = []
    for est in probability_estimates:
        try:
            validation = _validate_prediction_market_trade(
                yes_price=est["yes_price"],
                estimated_probability=est["probability"]["blended_estimate"],
                market_volume=0.0,  # Would come from market data
                market_liquidity=0.0,
            )
            trade_validations.append({
                "question": est["question"],
                "validation": validation,
            })
        except Exception as exc:
            logger.warning("Trade validation failed: %s", exc)
            errors.append(f"Trade validation: {exc}")

    # ── 5. Smart contract reads for active markets ────────────────────
    contract_reads: list[dict[str, Any]] = []
    for market in discovered_markets[:3]:
        condition_id = market.get("condition_id", "")
        platform = market.get("platform", "polymarket")
        if condition_id:
            try:
                contract_state = await _smart_contract_read(condition_id, platform)
                contract_reads.append(contract_state)
            except Exception as exc:
                logger.warning("Contract read failed: %s", exc)
                errors.append(f"Contract read: {exc}")

    # ── 6. Build prediction market context ────────────────────────────
    markets_count = len(discovered_markets)
    prob_count = len(probability_estimates)
    hedge_count = len(hedge_opportunities)

    best_hedge = ""
    if hedge_opportunities:
        h = hedge_opportunities[0]
        best_hedge = f" Best hedge: {h['description']} (edge={h['edge']:.2%})."

    best_edge = ""
    if probability_estimates:
        est = probability_estimates[0]
        edge = abs(est["probability"]["blended_estimate"] - est["yes_price"])
        best_edge = f" Top edge: {edge:.2%} on '{est['question'][:50]}...'."

    prediction_context = (
        f"Prediction market analysis for '{query}': "
        f"Discovered {markets_count} markets, "
        f"estimated {prob_count} probabilities, "
        f"found {hedge_count} cross-hedge opportunities."
        f"{best_edge}{best_hedge}"
    )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "macro_context": prediction_context if not state.macro_context else (
            state.macro_context + " | " + prediction_context
        ),
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "prediction_market",
                "status": "completed",
                "action": "prediction_market_analysis",
                "symbol": symbol,
                "query": query,
                "markets_discovered": markets_count,
                "probabilities_estimated": prob_count,
                "hedge_opportunities": hedge_count,
                "contract_reads": len(contract_reads),
                "timestamp": now,
            }
        ],
    }
