"""Agentic Trading — AI-powered trading agent routes.

Termasuk: Agent consensus, Berkshire-style value investing, multi-agent trading decisions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agentic", tags=["Agentic Trading"])


class BerkshireRequest(BaseModel):
    symbol: str
    roe: float = 0.18
    roic: float = 0.14
    gross_margin: float = 0.45
    net_margin: float = 0.15
    debt_to_equity: float = 0.35
    pe_ratio: float = 18.0
    pb_ratio: float = 3.0
    earnings_growth_5y: float = 0.12
    revenue_growth_5y: float = 0.10
    moat_score: float = 70.0
    current_ratio: float = 1.8
    interest_coverage: float = 5.0
    free_cashflow_yield: float = 0.04
    dividend_yield: float = 0.015


class ConsensusRequest(BaseModel):
    symbol: str
    signals: list[dict]


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/berkshire")
async def value_investing_analysis(req: BerkshireRequest) -> dict[str, Any]:
    """Run Berkshire Hathaway-style value investing analysis."""
    try:
        from quant_nanggroe.engine.agentic_trading import (
            BerkshireAnalyzer,
            ValueMetrics,
        )

        metrics = ValueMetrics(
            roe=req.roe,
            roic=req.roic,
            gross_margin=req.gross_margin,
            net_margin=req.net_margin,
            debt_to_equity=req.debt_to_equity,
            pe_ratio=req.pe_ratio,
            pb_ratio=req.pb_ratio,
            earnings_growth_5y=req.earnings_growth_5y,
            revenue_growth_5y=req.revenue_growth_5y,
            moat_score=req.moat_score,
            current_ratio=req.current_ratio,
            interest_coverage=req.interest_coverage,
            free_cashflow_yield=req.free_cashflow_yield,
            dividend_yield=req.dividend_yield,
        )

        analyzer = BerkshireAnalyzer()
        analyzer.set_metrics(metrics)
        decision = analyzer.full_assessment(req.symbol)

        return {
            "status": "success",
            "decision": decision.to_dict(),
            "metrics_summary": metrics.summary(),
            "buffett_score": metrics.buffett_score,
            "lynch_score": metrics.lynch_score,
            "module": "agentic_trading",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/consensus")
async def agent_consensus(req: ConsensusRequest) -> dict[str, Any]:
    """Run multi-agent consensus engine for trading decisions."""
    try:
        from quant_nanggroe.engine.agentic_trading import (
            AgentRole,
            AgentSignal,
            ConsensusEngine,
            DecisionAction,
        )

        signals = []
        for s in req.signals:
            signals.append(
                AgentSignal(
                    role=AgentRole(s.get("role", "research")),
                    action=DecisionAction(s.get("action", "hold")),
                    confidence=s.get("confidence", 0.5),
                    reasoning=s.get("reasoning", ""),
                    metrics=s.get("metrics", {}),
                )
            )

        engine = ConsensusEngine()
        decision = engine.reach_consensus(req.symbol, signals)

        return {
            "status": "success",
            "decision": decision.to_dict(),
            "agent_count": len(signals),
            "module": "agentic_trading",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/agents")
async def list_agent_roles() -> dict[str, Any]:
    """List available agent roles for trading decisions."""
    from quant_nanggroe.engine.agentic_trading import AgentRole

    return {
        "agents": [
            {"role": r.value, "name": r.name.title()}
            for r in AgentRole
        ],
        "actions": [
            {"action": "strong_buy", "confidence": 0.9},
            {"action": "buy", "confidence": 0.7},
            {"action": "hold", "confidence": 0.5},
            {"action": "sell", "confidence": 0.3},
            {"action": "strong_sell", "confidence": 0.1},
        ],
        "module": "agentic_trading",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
