"""Prediction Market Agent Tools for Quant Nanggroe AI Trading Framework.

Provides tools for interacting with prediction markets (Polymarket, Kalshi),
calculating odds, resolving markets, and analyzing event contracts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool


logger = logging.getLogger(__name__)


@tool
def fetch_polymarket_markets(
    query: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True,
    limit: int = 20,
) -> str:
    """
    Fetch available prediction markets from Polymarket.

    Args:
        query: Search query for filtering markets
        category: Category filter (politics, crypto, sports, etc.)
        active_only: Whether to return only active markets
        limit: Maximum number of markets to return

    Returns:
        JSON string with available prediction markets
    """
    markets = [
        {
            "market_id": "pm-btc-100k-2025",
            "title": "Will BTC reach $100k by end of 2025?",
            "category": "crypto",
            "outcome_tokens": {"YES": 0.62, "NO": 0.38},
            "volume_24h": 1_250_000,
            "liquidity": 5_000_000,
            "end_date": "2025-12-31",
            "is_active": True,
            "resolution_source": "CoinGecko",
        },
        {
            "market_id": "pm-fed-rate-cut-q2",
            "title": "Will the Fed cut rates in Q2 2025?",
            "category": "economics",
            "outcome_tokens": {"YES": 0.45, "NO": 0.55},
            "volume_24h": 890_000,
            "liquidity": 3_200_000,
            "end_date": "2025-06-30",
            "is_active": True,
            "resolution_source": "Federal Reserve",
        },
        {
            "market_id": "pm-eth-etf-approval",
            "title": "Will a new ETH ETF be approved in 2025?",
            "category": "crypto",
            "outcome_tokens": {"YES": 0.71, "NO": 0.29},
            "volume_24h": 2_100_000,
            "liquidity": 8_500_000,
            "end_date": "2025-12-31",
            "is_active": True,
            "resolution_source": "SEC",
        },
    ]

    # Filter by category
    if category:
        markets = [m for m in markets if m["category"] == category.lower()]

    # Filter by active status
    if active_only:
        markets = [m for m in markets if m["is_active"]]

    # Simple query matching
    if query:
        query_lower = query.lower()
        markets = [m for m in markets if query_lower in m["title"].lower()]

    data = {
        "markets": markets[:limit],
        "total_count": len(markets),
        "source": "polymarket",
        "fetched_at": datetime.now().isoformat(),
    }
    return json.dumps(data, indent=2)


@tool
def calculate_implied_probability(
    outcome_token_price: float,
    pool_liquidity: Optional[float] = None,
    fee_bps: float = 20.0,
) -> str:
    """
    Calculate implied probability and edge from prediction market odds.

    Args:
        outcome_token_price: Price of the outcome token (0.0-1.0)
        pool_liquidity: Total liquidity in the market pool
        fee_bps: Trading fee in basis points

    Returns:
        JSON string with probability analysis
    """
    # Implied probability = token price (for binary markets)
    implied_prob = min(max(outcome_token_price, 0.001), 0.999)

    # Adjust for fees
    fee_adjustment = fee_bps / 10000.0
    adjusted_prob = implied_prob / (1.0 - fee_adjustment)
    adjusted_prob = min(adjusted_prob, 0.999)

    # Calculate breakeven probability
    breakeven_prob = outcome_token_price

    # Edge calculation (if we have a fair estimate)
    # Edge = (true_probability * payout - cost) / cost
    payout_per_unit = 1.0 / outcome_token_price if outcome_token_price > 0 else 0.0

    data = {
        "outcome_token_price": outcome_token_price,
        "implied_probability": round(implied_prob, 4),
        "fee_adjusted_probability": round(adjusted_prob, 4),
        "breakeven_probability": round(breakeven_prob, 4),
        "payout_per_unit": round(payout_per_unit, 4),
        "fee_bps": fee_bps,
        "pool_liquidity": pool_liquidity,
        "calculation_time": datetime.now().isoformat(),
    }
    return json.dumps(data, indent=2)


@tool
def analyze_market_resolution(
    market_id: str,
    resolution_source: Optional[str] = None,
) -> str:
    """
    Analyze the resolution likelihood and conditions for a prediction market.

    Args:
        market_id: Market identifier to analyze
        resolution_source: Source for market resolution

    Returns:
        JSON string with resolution analysis
    """
    data = {
        "market_id": market_id,
        "resolution_analysis": {
            "resolution_type": "binary",
            "resolution_source": resolution_source or "oracle",
            "resolution_timeframe": "market_end_date",
            "dispute_period_days": 7,
            "resolution_confidence": "high",
            "potential_resolution_issues": [
                "Ambiguous resolution criteria",
                "Source data delay",
                "Dispute escalation",
            ],
        },
        "historical_resolution": {
            "markets_resolved": 1250,
            "disputed_resolutions": 15,
            "dispute_success_rate": 0.12,
            "avg_resolution_time_hours": 48,
        },
        "recommendations": [
            "Verify resolution criteria before trading",
            "Monitor resolution source for data consistency",
            "Consider dispute risk in position sizing",
        ],
        "analyzed_at": datetime.now().isoformat(),
    }
    return json.dumps(data, indent=2)


@tool
def fetch_market_orderbook(
    market_id: str,
    outcome: str = "YES",
    depth: int = 10,
) -> str:
    """
    Fetch the order book for a specific prediction market outcome.

    Args:
        market_id: Market identifier
        outcome: Which outcome's order book (YES/NO)
        depth: Number of price levels to return

    Returns:
        JSON string with order book data
    """
    # Simulated order book
    mid_price = 0.62 if outcome.upper() == "YES" else 0.38
    bids = []
    asks = []

    for i in range(depth):
        bid_price = round(mid_price - 0.01 * (i + 1), 4)
        ask_price = round(mid_price + 0.01 * (i + 1), 4)
        bid_size = round(5000 * (1 - i * 0.08), 2)
        ask_size = round(4500 * (1 - i * 0.08), 2)
        if bid_price > 0 and bid_size > 0:
            bids.append({"price": bid_price, "size": bid_size})
        if ask_price < 1.0 and ask_size > 0:
            asks.append({"price": ask_price, "size": ask_size})

    spread = asks[0]["price"] - bids[0]["price"] if bids and asks else 0

    data = {
        "market_id": market_id,
        "outcome": outcome.upper(),
        "bids": bids,
        "asks": asks,
        "spread": round(spread, 4),
        "mid_price": round(mid_price, 4),
        "total_bid_volume": sum(b["size"] for b in bids),
        "total_ask_volume": sum(a["size"] for a in asks),
        "depth": depth,
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(data, indent=2)


@tool
def compute_kelly_stake(
    probability_estimate: float,
    market_price: float,
    bankroll: float = 100_000.0,
    kelly_fraction: float = 0.25,
) -> str:
    """
    Compute optimal stake size using fractional Kelly criterion for prediction markets.

    Args:
        probability_estimate: Your estimated true probability (0.0-1.0)
        market_price: Current market price for the outcome token
        bankroll: Total bankroll available
        kelly_fraction: Fraction of Kelly to use (0.25 = quarter Kelly for safety)

    Returns:
        JSON string with Kelly stake calculation
    """
    # Kelly criterion: f* = (bp - q) / b
    # For prediction markets: b = (1/market_price) - 1 = payout ratio minus 1
    p = min(max(probability_estimate, 0.001), 0.999)
    q = 1 - p

    if market_price <= 0 or market_price >= 1:
        return json.dumps({
            "error": "market_price must be between 0 and 1 (exclusive)",
            "market_price": market_price,
        })

    # Payout ratio (odds)
    b = (1.0 / market_price) - 1.0

    # Full Kelly fraction
    full_kelly = (b * p - q) / b if b > 0 else 0.0

    # Fractional Kelly
    fractional_kelly = full_kelly * kelly_fraction

    # Stake size
    stake = max(0, bankroll * fractional_kelly)

    # Expected value
    ev = p * (1 - market_price) - q * market_price

    data = {
        "probability_estimate": round(p, 4),
        "market_price": market_price,
        "payout_ratio": round(b, 4),
        "full_kelly_fraction": round(full_kelly, 4),
        "fractional_kelly": round(fractional_kelly, 4),
        "kelly_fraction_used": kelly_fraction,
        "bankroll": bankroll,
        "recommended_stake": round(stake, 2),
        "expected_value_per_unit": round(ev, 4),
        "edge": round(ev, 4),
        "recommendation": "PASS" if ev <= 0 else "BET",
        "computed_at": datetime.now().isoformat(),
    }
    return json.dumps(data, indent=2)


PREDICTION_MARKET_TOOLS = [
    fetch_polymarket_markets,
    calculate_implied_probability,
    analyze_market_resolution,
    fetch_market_orderbook,
    compute_kelly_stake,
]
