"""
Smart Order Executor for Quant Nanggroe AI Trading Framework v2.

Implements smart order routing with venue scoring, latency monitoring,
and asset-class-aware venue selection. This module acts as the enhanced
execution node that replaces the simple order submission in the v1 graph.

Venue scoring model:
  score = w_fill * fill_rate + w_fee * (1 - fee_bps/100) + w_latency * (1 - latency_ms/1000) + w_slippage * (1 - slippage_bps/100)
  (normalised to 0-100)

Each asset class has its own set of supported venues with different
fee structures, latency profiles, and fill rates.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_nanggroe.agents.state import (
    AgentState,
    AssetClass,
    SmartOrderRouting,
    VenueScore,
    TradeAction,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Venue registry
# =============================================================================

# Default venue configurations per asset class.
# In production, these would be loaded from a config store and updated
# dynamically based on real-time monitoring.

VENUE_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    AssetClass.CRYPTO.value: [
        {
            "venue_id": "jupiter",
            "venue_name": "Jupiter (Solana DEX)",
            "fee_bps": 0.0,
            "avg_latency_ms": 400,
            "avg_fill_rate": 0.95,
            "avg_slippage_bps": 5,
        },
        {
            "venue_id": "raydium",
            "venue_name": "Raydium (Solana DEX)",
            "fee_bps": 0.0,
            "avg_latency_ms": 500,
            "avg_fill_rate": 0.92,
            "avg_slippage_bps": 8,
        },
        {
            "venue_id": "binance",
            "venue_name": "Binance (CEX)",
            "fee_bps": 10.0,
            "avg_latency_ms": 50,
            "avg_fill_rate": 0.99,
            "avg_slippage_bps": 2,
        },
        {
            "venue_id": "coinbase",
            "venue_name": "Coinbase Pro (CEX)",
            "fee_bps": 15.0,
            "avg_latency_ms": 80,
            "avg_fill_rate": 0.98,
            "avg_slippage_bps": 3,
        },
        {
            "venue_id": "okx",
            "venue_name": "OKX (CEX)",
            "fee_bps": 8.0,
            "avg_latency_ms": 60,
            "avg_fill_rate": 0.98,
            "avg_slippage_bps": 3,
        },
    ],
    AssetClass.FOREX.value: [
        {
            "venue_id": "oanda",
            "venue_name": "OANDA",
            "fee_bps": 1.0,
            "avg_latency_ms": 30,
            "avg_fill_rate": 0.99,
            "avg_slippage_bps": 1,
        },
        {
            "venue_id": "ibkr_fx",
            "venue_name": "Interactive Brokers FX",
            "fee_bps": 0.5,
            "avg_latency_ms": 20,
            "avg_fill_rate": 0.99,
            "avg_slippage_bps": 0.5,
        },
        {
            "venue_id": "fxcm",
            "venue_name": "FXCM",
            "fee_bps": 2.0,
            "avg_latency_ms": 50,
            "avg_fill_rate": 0.97,
            "avg_slippage_bps": 2,
        },
    ],
    AssetClass.EQUITY.value: [
        {
            "venue_id": "alpaca",
            "venue_name": "Alpaca Markets",
            "fee_bps": 0.0,
            "avg_latency_ms": 100,
            "avg_fill_rate": 0.98,
            "avg_slippage_bps": 3,
        },
        {
            "venue_id": "ibkr",
            "venue_name": "Interactive Brokers",
            "fee_bps": 0.5,
            "avg_latency_ms": 30,
            "avg_fill_rate": 0.99,
            "avg_slippage_bps": 1,
        },
        {
            "venue_id": "td_ameritrade",
            "venue_name": "TD Ameritrade",
            "fee_bps": 0.0,
            "avg_latency_ms": 150,
            "avg_fill_rate": 0.97,
            "avg_slippage_bps": 4,
        },
    ],
    AssetClass.PREDICTION_MARKET.value: [
        {
            "venue_id": "polymarket",
            "venue_name": "Polymarket",
            "fee_bps": 0.0,
            "avg_latency_ms": 2000,
            "avg_fill_rate": 0.85,
            "avg_slippage_bps": 15,
        },
        {
            "venue_id": "kalshi",
            "venue_name": "Kalshi",
            "fee_bps": 0.0,
            "avg_latency_ms": 3000,
            "avg_fill_rate": 0.80,
            "avg_slippage_bps": 20,
        },
    ],
}

# Scoring weights
WEIGHT_FILL_RATE: float = 0.35
WEIGHT_FEE: float = 0.25
WEIGHT_LATENCY: float = 0.20
WEIGHT_SLIPPAGE: float = 0.20

# Maximum normalisation factors for scoring
MAX_FEE_BPS: float = 20.0       # Fees above 20 bps score 0 on fee dimension
MAX_LATENCY_MS: float = 5000.0  # Latency above 5s scores 0 on latency dimension
MAX_SLIPPAGE_BPS: float = 30.0  # Slippage above 30 bps scores 0 on slippage dimension


# =============================================================================
# Venue scoring logic
# =============================================================================

def score_venue(
    venue_config: Dict[str, Any],
    asset_class: str,
    order_size_usd: float = 0.0,
) -> VenueScore:
    """
    Score a single venue based on its characteristics.

    The scoring model is a weighted combination of:
    - Fill rate (higher is better)
    - Fee (lower is better)
    - Latency (lower is better)
    - Slippage (lower is better)

    Args:
        venue_config: Venue configuration dictionary
        asset_class: Target asset class
        order_size_usd: Order size in USD (for size-aware scoring)

    Returns:
        VenueScore with computed score and recommendation
    """
    fill_rate = venue_config.get("avg_fill_rate", 0.0)
    fee_bps = venue_config.get("fee_bps", 100.0)
    latency_ms = venue_config.get("avg_latency_ms", 10000.0)
    slippage_bps = venue_config.get("avg_slippage_bps", 100.0)

    # Normalise each dimension to 0-1
    fill_score = fill_rate  # Already 0-1
    fee_score = max(0.0, 1.0 - (fee_bps / MAX_FEE_BPS))
    latency_score = max(0.0, 1.0 - (latency_ms / MAX_LATENCY_MS))
    slippage_score = max(0.0, 1.0 - (slippage_bps / MAX_SLIPPAGE_BPS))

    # Weighted score (0-100)
    overall = (
        WEIGHT_FILL_RATE * fill_score
        + WEIGHT_FEE * fee_score
        + WEIGHT_LATENCY * latency_score
        + WEIGHT_SLIPPAGE * slippage_score
    ) * 100

    # Size penalty for large orders on low-liquidity venues
    if order_size_usd > 100000 and fill_rate < 0.95:
        overall *= 0.9  # 10% penalty for large orders on low-fill venues

    # Check asset class support
    supported_venues = VENUE_REGISTRY.get(asset_class, [])
    supports_asset = any(
        v.get("venue_id") == venue_config.get("venue_id")
        for v in supported_venues
    )

    return VenueScore(
        venue_id=venue_config.get("venue_id", "unknown"),
        venue_name=venue_config.get("venue_name", "Unknown"),
        score=round(overall, 2),
        latency_ms=latency_ms,
        fee_bps=fee_bps,
        fill_rate=fill_rate,
        slippage_bps=slippage_bps,
        supports_asset_class=supports_asset,
    )


def score_all_venues(
    asset_class: str,
    order_size_usd: float = 0.0,
) -> List[VenueScore]:
    """
    Score all venues for a given asset class.

    Args:
        asset_class: Target asset class
        order_size_usd: Order size in USD

    Returns:
        List of VenueScore objects, sorted by score descending
    """
    venues = VENUE_REGISTRY.get(asset_class, [])
    scores: List[VenueScore] = []

    for venue in venues:
        vs = score_venue(venue, asset_class, order_size_usd)
        scores.append(vs)

    # Sort by score descending
    scores.sort(key=lambda s: s.score, reverse=True)

    # Mark the top venue as recommended
    if scores:
        # Update the top score to be recommended
        top = scores[0]
        recommended_score = VenueScore(
            venue_id=top.venue_id,
            venue_name=top.venue_name,
            score=top.score,
            latency_ms=top.latency_ms,
            fee_bps=top.fee_bps,
            fill_rate=top.fill_rate,
            slippage_bps=top.slippage_bps,
            supports_asset_class=top.supports_asset_class,
            recommended=True,
        )
        scores[0] = recommended_score

    return scores


# =============================================================================
# Smart order routing
# =============================================================================

def route_order(
    symbol: str,
    asset_class: str,
    action: str,
    quantity: float,
    order_size_usd: float = 0.0,
) -> SmartOrderRouting:
    """
    Determine the optimal venue and routing strategy for an order.

    Args:
        symbol: Trading symbol
        asset_class: Asset class for venue selection
        action: Trade action (BUY/SELL)
        quantity: Order quantity
        order_size_usd: Order size in USD

    Returns:
        SmartOrderRouting with venue scores and routing decision
    """
    # Score all venues for this asset class
    venue_scores = score_all_venues(asset_class, order_size_usd)

    # Select primary venue (highest score)
    primary_venue = ""
    routing_decision = "No suitable venue found"
    estimated_slippage = 0.0
    estimated_latency = 0.0

    if venue_scores:
        best = venue_scores[0]
        primary_venue = best.venue_id
        estimated_slippage = best.slippage_bps
        estimated_latency = best.latency_ms
        routing_decision = (
            f"Routed to {best.venue_name} (score={best.score:.1f}, "
            f"fill_rate={best.fill_rate:.0%}, fee={best.fee_bps:.1f}bps, "
            f"latency={best.latency_ms:.0f}ms)"
        )

    result = SmartOrderRouting(
        symbol=symbol,
        primary_venue=primary_venue,
        venue_scores=venue_scores,
        routing_decision=routing_decision,
        estimated_slippage_bps=estimated_slippage,
        estimated_latency_ms=estimated_latency,
    )

    logger.info(
        f"Smart routing for {symbol} ({asset_class}): "
        f"primary_venue={primary_venue}, "
        f"slippage={estimated_slippage:.1f}bps, "
        f"latency={estimated_latency:.0f}ms"
    )

    return result


# =============================================================================
# LangGraph node
# =============================================================================

class SmartExecutor:
    """
    Smart execution node for the v2 LangGraph trading graph.

    Replaces the simple execution node with venue-scoring-based
    smart order routing. For each actionable decision, it scores
    available venues, selects the best one, and routes the order.
    """

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute smart order routing for all actionable decisions.

        Args:
            state: Current agent state

        Returns:
            State updates with venue_scores and smart_routing_result
        """
        logger.info("=== Smart Order Execution Phase ===")

        decisions = state.get("decisions", [])
        asset_class = state.get("asset_class", AssetClass.EQUITY.value)

        all_venue_scores: List[Dict[str, Any]] = []
        routing_results: Dict[str, Any] = {}
        orders_placed: List[Dict[str, Any]] = []

        for decision in decisions:
            if not isinstance(decision, dict):
                continue

            action = decision.get("action", "")
            if action not in (TradeAction.BUY.value, TradeAction.SELL.value, TradeAction.CLOSE.value):
                continue

            symbol = decision.get("symbol", "")
            quantity = decision.get("quantity", 0)
            entry_price = decision.get("entry_price", 0) or 0

            # Estimate order size
            order_size_usd = quantity * entry_price if entry_price > 0 else 0

            # Route order
            routing = route_order(
                symbol=symbol,
                asset_class=asset_class,
                action=action,
                quantity=quantity,
                order_size_usd=order_size_usd,
            )

            routing_results[symbol] = routing.model_dump()

            # Collect venue scores
            for vs in routing.venue_scores:
                all_venue_scores.append(vs.model_dump())

            # Build order record
            orders_placed.append({
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "venue": routing.primary_venue,
                "estimated_slippage_bps": routing.estimated_slippage_bps,
                "estimated_latency_ms": routing.estimated_latency_ms,
                "status": "ROUTED",
                "routed_at": datetime.now().isoformat(),
            })

            logger.info(
                f"Order routed: {action} {quantity} {symbol} → "
                f"{routing.primary_venue} "
                f"(slippage={routing.estimated_slippage_bps:.1f}bps)"
            )

        return {
            "venue_scores": all_venue_scores,
            "smart_routing_result": routing_results,
            "orders_placed": orders_placed,
            "execution_output": (
                f"Smart-routed {len(orders_placed)} order(s) "
                f"across {len(set(o['venue'] for o in orders_placed))} venue(s)"
                if orders_placed
                else "No actionable orders to route"
            ),
            "sender": "smart_executor",
        }


def route_order_smart(state: AgentState) -> Dict[str, Any]:
    """
    Functional interface for the smart execution node.

    Args:
        state: Current agent state

    Returns:
        State updates with smart routing results
    """
    executor = SmartExecutor()
    return executor(state)
