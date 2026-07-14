"""
Agentic Trading Module — LLM-Powered Trading Agent Flow
========================================================
Implementasi dari Open-Finance-Lab/AgenticTrading dan ai-berkshire
(xbtlin/ai-berkshire) untuk trading decision dengan LLM agents.

Arsitektur Agentic Trading:
1. Market Research Agent → mengumpulkan data fundamental & teknikal
2. Sentiment Agent → menganalisis news/social media sentiment
3. Risk Agent → mengecek risk constraints & position sizing
4. Execution Agent → generate trading decision dengan konteks lengkap
5. Reflection → review & improve dari hasil sebelumnya

Integrasi dengan existing QNA agent system (LangGraph).
"""

from __future__ import annotations
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    RESEARCH = "research"
    SENTIMENT = "sentiment"
    RISK = "risk"
    VALUATION = "valuation"
    EXECUTION = "execution"
    REFLECTION = "reflection"
    BERKSHIRE = "berkshire"  # value investing specialist


class DecisionAction(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"
    REDUCE = "reduce"
    ADD = "add"
    NOTHING = "nothing"


@dataclass
class AgentSignal:
    """Signal output from a single agent."""
    role: AgentRole
    action: DecisionAction
    confidence: float          # 0.0 - 1.0
    reasoning: str = ""        # ponytail: optional — not all callers (e.g. API, quick signals) supply it
    metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class TradingDecision:
    """Final trading decision from agent consensus."""
    symbol: str
    action: DecisionAction
    confidence: float
    position_size_pct: float   # % of portfolio
    reasoning: str
    agents: list[AgentSignal] = field(default_factory=list)
    risk_score: float = 0.5
    conviction: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "confidence": self.confidence,
            "position_size_pct": self.position_size_pct,
            "reasoning": self.reasoning,
            "agents": [s.__dict__ for s in self.agents],
            "risk_score": self.risk_score,
            "conviction": self.conviction,
            "timestamp": self.timestamp,
        }


# ── Value Investing Framework (AI Berkshire) ──────────────────────────────

@dataclass
class ValueMetrics:
    """Value investing metrics — AI Berkshire style.

    Menggabungkan metodologi Buffett, Munger, Lynch, Dalio.
    """
    # Profitability
    roe: float = 0.0           # Return on Equity
    roic: float = 0.0          # Return on Invested Capital
    gross_margin: float = 0.0
    net_margin: float = 0.0
    operating_margin: float = 0.0

    # Growth
    revenue_growth_5y: float = 0.0
    earnings_growth_5y: float = 0.0
    book_value_growth: float = 0.0

    # Valuation
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    ps_ratio: float = 0.0
    ev_ebitda: float = 0.0
    dividend_yield: float = 0.0
    free_cashflow_yield: float = 0.0
    market_cap: float = 0.0  # ponytail: absolute market cap — needed by valuation/fundamental callers

    # Financial Health
    debt_to_equity: float = 0.0
    current_ratio: float = 0.0
    interest_coverage: float = 0.0

    # Moat (qualitative proxy)
    moat_score: float = 0.0    # 0-100
    competitive_advantage: str = ""
    industry_position: str = ""

    # Munger's psychology
    psychology_score: float = 0.0  # cognitive bias avoidance

    @property
    def buffett_score(self) -> float:
        """Buffett's checklist: high ROE, low debt, predictable earnings."""
        score = 0.0
        if self.roe > 0.15:
            score += 20
        if self.roic > 0.12:
            score += 20
        if self.debt_to_equity < 0.5:
            score += 20
        if self.earnings_growth_5y > 0.1:
            score += 20
        if self.free_cashflow_yield > 0.05:
            score += 10
        if self.moat_score > 60:
            score += 10
        return min(score, 100)

    @property
    def lynch_score(self) -> float:
        """Peter Lynch's PEG ratio approach."""
        if self.pe_ratio <= 0 or self.earnings_growth_5y <= 0:
            return 0
        peg = self.pe_ratio / (self.earnings_growth_5y * 100 + self.dividend_yield)
        if peg < 0.5:
            return 100
        if peg < 1.0:
            return 80
        if peg < 1.5:
            return 60
        if peg < 2.0:
            return 40
        return 20

    def summary(self) -> str:
        return (
            f"Buffett={self.buffett_score:.0f}/100 | "
            f"Lynch={self.lynch_score:.0f}/100 | "
            f"ROE={self.roe:.1%} ROIC={self.roic:.1%} | "
            f"D/E={self.debt_to_equity:.2f} | "
            f"Moat={self.moat_score:.0f}"
        )


class BerkshireAnalyzer:
    """AI Berkshire — value investing analysis engine.

    Mensimulasikan 4 master investor methodology.
    """

    def __init__(self):
        self.metrics = ValueMetrics()

    def set_metrics(self, metrics: ValueMetrics) -> None:
        self.metrics = metrics

    def buffett_assessment(self) -> AgentSignal:
        """Warren Buffett: durable competitive advantage, fair price."""
        m = self.metrics
        score = m.buffett_score
        reasons = []
        if m.roe > 0.15:
            reasons.append(f"Strong ROE ({m.roe:.1%}) indicates pricing power")
        if m.roic > 0.12:
            reasons.append(f"High ROIC ({m.roic:.1%}) confirms capital efficiency")
        if m.debt_to_equity < 0.5:
            reasons.append(f"Low debt (D/E={m.debt_to_equity:.2f}) — conservative financing")
        if m.moat_score < 50:
            reasons.append(f"Weak moat ({m.moat_score:.0f}) — no durable advantage")

        if score >= 70:
            action = DecisionAction.BUY
            conviction = f"Classic Buffett opportunity (score {score:.0f}/100)"
        elif score >= 50:
            action = DecisionAction.ADD
            conviction = f"Acceptable but not ideal (score {score:.0f}/100)"
        elif score >= 30:
            action = DecisionAction.HOLD
            conviction = f"Below threshold, wait for better price (score {score:.0f}/100)"
        else:
            action = DecisionAction.NOTHING
            conviction = "Does not meet Buffett criteria"

        return AgentSignal(
            role=AgentRole.BERKSHIRE,
            action=action,
            confidence=score / 100,
            reasoning=" | ".join(reasons) or conviction,
            metrics={"buffett_score": score, "roe": m.roe, "debt_to_equity": m.debt_to_equity},
        )

    def lynch_assessment(self) -> AgentSignal:
        """Peter Lynch: PEG ratio, understand what you own."""
        score = self.metrics.lynch_score
        peg = self.metrics.pe_ratio / (self.metrics.earnings_growth_5y * 100 + self.metrics.dividend_yield + 1e-8)

        if score >= 80:
            action = DecisionAction.BUY
        elif score >= 60:
            action = DecisionAction.ADD
        elif score >= 40:
            action = DecisionAction.HOLD
        else:
            action = DecisionAction.SELL

        return AgentSignal(
            role=AgentRole.VALUATION,
            action=action,
            confidence=score / 100,
            reasoning=f"PEG ratio {peg:.2f} → Lynch score {score:.0f}/100",
            metrics={"peg": peg, "lynch_score": score},
        )

    def munger_assessment(self) -> AgentSignal:
        """Charlie Munger: mental models, psychology, avoid stupidity."""
        m = self.metrics
        score = m.psychology_score
        reasons = []

        if m.interest_coverage > 3:
            reasons.append("Strong interest coverage — low distress risk")

        if len(reasons) == 0:
            reasons.append("Standard risk profile")

        action = DecisionAction.HOLD if score >= 50 else DecisionAction.NOTHING
        return AgentSignal(
            role=AgentRole.RISK,
            action=action,
            confidence=score / 100,
            reasoning=" | ".join(reasons),
            metrics={"psychology_score": score},
        )

    def full_assessment(self, symbol: str) -> TradingDecision:
        """Run all 4 assessments and aggregate."""
        signals = [
            self.buffett_assessment(),
            self.lynch_assessment(),
            self.munger_assessment(),
        ]

        # Weighted consensus
        weights = {"berkshire": 0.4, "valuation": 0.3, "risk": 0.3}
        action_scores = {}
        for sig in signals:
            w = weights.get(sig.role.value, 0.33)
            action_scores[sig.action.value] = action_scores.get(sig.action.value, 0) + w * sig.confidence

        best_action = max(action_scores, key=action_scores.get)
        consensus_conf = action_scores[best_action]
        all_reasons = "\n".join(f"[{s.role.value}] {s.reasoning}" for s in signals)

        return TradingDecision(
            symbol=symbol,
            action=DecisionAction(best_action),
            confidence=consensus_conf,
            position_size_pct=min(consensus_conf * 0.15, 0.05),  # max 15% with 5% typical
            reasoning=all_reasons,
            agents=signals,
            risk_score=1 - self.metrics.debt_to_equity if self.metrics.debt_to_equity < 2 else 0.3,
            conviction="Strong conviction" if consensus_conf > 0.7 else "Moderate conviction",
        )


# ── Agent Consensus Engine ────────────────────────────────────────────────


class ConsensusEngine:
    """Aggregate multiple agent signals into a trading decision.

    Supports:
    - Simple majority vote
    - Weighted consensus (by confidence)
    - Veto power (any agent says STRONG_SELL → block)
    """

    def __init__(self, veto_roles: Optional[list[AgentRole]] = None):
        self.veto_roles = veto_roles or [AgentRole.RISK]

    def reach_consensus(
        self,
        symbol: str,
        signals: list[AgentSignal],
        weights: Optional[dict[str, float]] = None,
    ) -> TradingDecision:
        """Aggregate signals into final trading decision."""
        if not signals:
            return TradingDecision(
                symbol=symbol, action=DecisionAction.NOTHING,
                confidence=0.0, position_size_pct=0.0,
                reasoning="No agent signals available",
            )

        # Veto check
        for sig in signals:
            if sig.role in self.veto_roles and sig.action in (DecisionAction.STRONG_SELL, DecisionAction.SELL):
                return TradingDecision(
                    symbol=symbol, action=DecisionAction.NOTHING,
                    confidence=0.0, position_size_pct=0.0,
                    reasoning=f"Vetoed by {sig.role.value}: {sig.reasoning}",
                    agents=signals,
                )

        default_weights = {role.value: 1.0 for role in AgentRole}
        w = (weights or {})
        merged = {**default_weights, **w}

        action_scores: dict[str, float] = {}
        total_weight = 0.0

        for sig in signals:
            role_weight = merged.get(sig.role.value, 1.0)
            action_scores[sig.action.value] = action_scores.get(sig.action.value, 0) + role_weight * sig.confidence
            total_weight += role_weight

        if not action_scores:
            return TradingDecision(
                symbol=symbol, action=DecisionAction.NOTHING,
                confidence=0.0, position_size_pct=0.0,
                reasoning="No actionable signals",
                agents=signals,
            )

        best_action = max(action_scores, key=action_scores.get)
        consensus_conf = min(action_scores[best_action] / (total_weight + 1e-8), 1.0)

        # Position sizing: Kelly-inspired
        kelly_fraction = (2 * consensus_conf - 1) * 0.5
        position_pct = max(0, min(0.25, kelly_fraction))

        # Build reasoning
        all_reasons = "\n".join(
            f"[{s.role.value}:{s.action.value} ({s.confidence:.0%})] {s.reasoning[:200]}"
            for s in signals
        )

        return TradingDecision(
            symbol=symbol,
            action=DecisionAction(best_action),
            confidence=consensus_conf,
            position_size_pct=position_pct,
            reasoning=all_reasons,
            agents=signals,
            risk_score=np.mean([s.confidence for s in signals]),
            conviction=f"{best_action} @ {consensus_conf:.0%} confidence",
        )
