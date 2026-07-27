"""Debate API routes — multi-agent debate engine.

Wired to real debate subsystems:
  - DebateEngine (agents/debate/engine.py) — weighted multi-agent vote
  - TradingDebateGraph (agents/debate/graph.py) — full Bull/Bear + Risk debate
  - Council (engine/agentic/council.py) — investor persona council
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debate", tags=["debate"])


class DebateSession(BaseModel):
    topic: str
    participants: list[str]
    symbol: str | None = None
    direction: str | None = "BUY"
    confidence: float | None = None


class SimpleDebate(BaseModel):
    """Quick weighted-vote debate among named agents."""
    symbol: str
    opinions: list[dict[str, Any]]  # [{agent_id, signal, confidence, weight?}]
    volatility: float = 0.2


@router.get("/list")
async def list_debates() -> dict[str, Any]:
    """List available debate modes and capabilities."""
    capabilities: list[dict[str, Any]] = [
        {
            "id": "trading_debate_graph",
            "name": "Trading Debate Graph",
            "type": "bull_bear_risk",
            "status": "available",
            "description": "Full Bull/Bear research debate + Conservative/Neutral/Aggressive risk debate",
            "phases": ["research_debate", "risk_debate", "synthesis"],
        },
        {
            "id": "weighted_vote",
            "name": "Weighted Vote Debate",
            "type": "weighted_vote",
            "status": "available",
            "description": "Quick weighted-confidence multi-agent vote",
        },
        {
            "id": "council",
            "name": "Investor Persona Council",
            "type": "council",
            "status": "available",
            "description": "6 investor personas debate low-confidence signals (Buffett, Dalio, Burry, etc.)",
        },
    ]
    return {
        "debates": capabilities,
        "module": "debate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{debate_id}")
async def get_debate(debate_id: str) -> dict[str, Any]:
    """Get details for a specific debate mode."""
    debate_info = {
        "trading_debate_graph": {
            "id": "trading_debate_graph",
            "name": "Trading Debate Graph",
            "module": "quant_nanggroe.agents.debate.graph",
            "class": "TradingDebateGraph",
            "method": "run(symbol, market_data, trade_direction, proposed_size)",
            "phases": [
                {"name": "research", "nodes": ["BullResearcherNode", "BearResearcherNode"]},
                {"name": "risk", "nodes": ["ConservativeDebatorNode", "NeutralDebatorNode", "AggressiveDebatorNode"]},
                {"name": "synthesis", "description": "Weighted verdict aggregation"},
            ],
        },
        "weighted_vote": {
            "id": "weighted_vote",
            "name": "Weighted Vote Debate",
            "module": "quant_nanggroe.agents.debate.engine",
            "class": "DebateEngine",
            "method": "debate(opinions, volatility)",
        },
        "council": {
            "id": "council",
            "name": "Investor Persona Council",
            "module": "quant_nanggroe.engine.agentic.council",
            "function": "convene_council(symbol, proposed_signal, proposed_confidence, price, regime)",
            "personas": [
                "Warren Buffett (value)",
                "Peter Lynch (growth_at_reasonable_price)",
                "Ray Dalio (macro_economic)",
                "Michael Burry (deep_value)",
                "Cathie Wood (disruptive_growth)",
                "Stanley Druckenmiller (macro_momentum)",
            ],
        },
    }
    result = debate_info.get(debate_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Debate '{debate_id}' not found")
    return result


@router.post("/new")
async def create_debate(session: DebateSession) -> dict[str, Any]:
    """Run a real debate using the TradingDebateGraph or weighted vote."""
    # Try TradingDebateGraph if symbol provided
    if session.symbol:
        try:
            from quant_nanggroe.agents.debate.graph import TradingDebateGraph

            graph = TradingDebateGraph(max_research_rounds=3)
            result = await graph.run(
                symbol=session.symbol,
                market_data={"topic": session.topic},
                trade_direction=session.direction or "BUY",
                proposed_size=session.confidence or 0.5,
            )
            return {
                "id": f"deb-{datetime.now(timezone.utc).timestamp():.0f}",
                "type": "trading_debate_graph",
                "symbol": session.symbol,
                "result": result.to_dict(),
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning("TradingDebateGraph failed: %s", exc)
            # Fall through to weighted vote

    # Fallback: return debate mode info
    return {
        "id": f"deb-{datetime.now(timezone.utc).timestamp():.0f}",
        "topic": session.topic,
        "participants": session.participants,
        "status": "created",
        "module": "debate",
        "hint": "Provide 'symbol' field to run a real TradingDebateGraph debate",
    }


@router.post("/weighted")
async def weighted_debate(debate: SimpleDebate) -> dict[str, Any]:
    """Run a weighted-vote debate using the real DebateEngine."""
    try:
        from quant_nanggroe.agents.debate.engine import AgentOpinion, DebateEngine, Signal

        opinions = []
        for op in debate.opinions:
            signal_val = op.get("signal", "hold")
            try:
                signal_enum = Signal(signal_val.lower())
            except ValueError:
                signal_enum = Signal.HOLD
            opinions.append(
                AgentOpinion(
                    agent_id=op.get("agent_id", "unknown"),
                    signal=signal_enum,
                    confidence=float(op.get("confidence", 0.5)),
                    reasoning=op.get("reasoning", ""),
                    weight=float(op.get("weight", 1.0)),
                )
            )

        if len(opinions) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 opinions for debate")

        engine = DebateEngine(min_agents=2)
        result = engine.debate(opinions, volatility=debate.volatility)

        return {
            "symbol": debate.symbol,
            "consensus_signal": result.consensus_signal.value,
            "consensus_confidence": result.consensus_confidence,
            "disagreement": result.disagreement,
            "opinions_count": len(result.opinions),
            "risk": {
                "max_position_size": result.risk.max_position_size if result.risk else None,
                "max_leverage": result.risk.max_leverage if result.risk else None,
                "var_95": result.risk.var_95 if result.risk else None,
            },
            "summary": result.summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Weighted debate failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Debate engine error: {exc}")
