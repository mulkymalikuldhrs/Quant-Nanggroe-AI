"""Ensemble Voting API Routes — multi-signal consensus endpoint."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ensemble", tags=["Ensemble"])


class VoteRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol (e.g., EURUSD)")
    primary_bias: str = Field("neutral", description="Primary signal: buy/sell/neutral")
    primary_confidence: float = Field(0.5, ge=0, le=1, description="Primary confidence 0-1")
    adapters: Optional[list[str]] = Field(None, description="Specific adapters to use (None=all)")


class VoteResponse(BaseModel):
    symbol: str
    final_bias: str
    confidence: float
    consensus: float
    total_signals: int
    dissenters: int
    votes: list[dict[str, Any]]
    second_opinion: dict[str, Any] | None = Field(
        None, description="Independent TradingAgents 2nd-opinion cross-check (confirm/contradict/neutral/abstain)."
    )
    timestamp: str


@router.post("/vote", response_model=VoteResponse)
async def ensemble_vote(req: VoteRequest):
    """Run ensemble voting on a symbol with multiple signal providers.

    Aggregates signals from registered adapters (wyckoff, aihf, hidden_regime,
    tradingagents, mtf) with the primary strategy signal using weighted consensus.
    """
    try:
        from quant_nanggroe.engine.agentic.voting import SignalVotingSystem, Signal, Bias
        from quant_nanggroe.engine.agentic.adapters import ALL_ADAPTERS, fetch_all_signals

        voter = SignalVotingSystem()
        bias_map = {"buy": Bias.BUY, "sell": Bias.SELL, "neutral": Bias.NEUTRAL}

        # Build signal list
        signals = [
            Signal(
                bias=bias_map.get(req.primary_bias, Bias.NEUTRAL),
                confidence=req.primary_confidence,
                source="primary_strategy",
            )
        ]

        # Fetch adapter signals
        active_adapters = None
        if req.adapters:
            active_adapters = [a for a in ALL_ADAPTERS if a.source_name in req.adapters]

        external = fetch_all_signals(req.symbol, adapters=active_adapters)
        signals.extend(external)

        # Vote
        result = voter.vote(signals)

        # Q3 — 2nd-opinion cross-check (independent arbitrator, fail-closed).
        # It only CONFIRMs / CONTRADICTs / ABSTAINS; a disabled/unavailable
        # TradingAgents can never silently swing the primary vote.
        from quant_nanggroe.engine.agentic.adapters import TradingAgentsValidator

        try:
            verdict = TradingAgentsValidator().evaluate(result, req.symbol)
            second_opinion = {
                "status": verdict.status,
                "reason": verdict.reason,
                "external_bias": verdict.signal.bias.value if verdict.signal else None,
            }
        except Exception as e:  # never let the 2nd-opinion break the primary vote
            logger.warning("2nd-opinion validator error: %s", e)
            second_opinion = {"status": "abstain", "reason": f"validator error: {e}", "external_bias": None}

        from datetime import datetime, timezone
        return VoteResponse(
            symbol=req.symbol,
            final_bias=result.final_bias.value,
            confidence=round(result.weighted_confidence, 4),
            consensus=round(result.consensus_strength, 4),
            total_signals=len(result.votes),
            dissenters=len(result.dissenters),
            votes=[
                {"source": v.source, "bias": v.bias.value, "confidence": v.confidence}
                for v in result.votes
            ],
            second_opinion=second_opinion,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adapters")
async def list_adapters():
    """List all registered signal adapters."""
    from quant_nanggroe.engine.agentic.adapters import ALL_ADAPTERS
    return {
        "count": len(ALL_ADAPTERS),
        "adapters": [
            {"name": a.source_name, "class": a.__class__.__name__}
            for a in ALL_ADAPTERS
        ],
    }


@router.get("/risk/kelly")
async def kelly_analysis(
    win_rate: float = 60,
    avg_win: float = 100,
    avg_loss: float = 80,
    balance: float = 1000,
):
    """Run Kelly Criterion position sizing analysis."""
    from quant_nanggroe.engine.risk.enhanced_analytics import EnhancedRiskAnalytics
    ra = EnhancedRiskAnalytics()
    result = ra.kelly_criterion(win_rate, avg_win, avg_loss, balance)
    return result.to_dict()


@router.get("/risk/monte-carlo")
async def monte_carlo_analysis(
    trades: str = "50,-30,80,-20,60,-40,70,-10,90,-50",
    simulations: int = 10000,
):
    """Run Monte Carlo simulation on trade P&Ls."""
    from quant_nanggroe.engine.risk.enhanced_analytics import EnhancedRiskAnalytics
    ra = EnhancedRiskAnalytics()
    pnl_list = [float(x) for x in trades.split(",")]
    result = ra.monte_carlo(pnl_list, simulations=simulations)
    return result.to_dict()


@router.get("/scanner/summary")
async def scanner_summary():
    """Get multi-pair scanner summary."""
    from quant_nanggroe.engine.scanner.multi_pair import MultiPairScanner
    sc = MultiPairScanner()
    return sc.get_summary()


@router.get("/scanner/pairs")
async def scanner_pairs(category: str = None):
    """Get pairs, optionally filtered by category."""
    from quant_nanggroe.engine.scanner.multi_pair import MultiPairScanner
    sc = MultiPairScanner()
    if category:
        cats = sc.get_by_category()
        pairs = cats.get(category, [])
    else:
        pairs = sc.get_tradeable()
    return {
        "count": len(pairs),
        "pairs": [p.to_dict() for p in pairs],
    }
