"""Vote Chamber — Structured debate + consensus logic."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from quant_nanggroe.engine.agentic.committee.agents import (
    BaseAgent, BullAnalyst, BearAnalyst, MacroAnalyst,
    RiskOfficer, ExecutionAgent, AgentVote,
)

logger = logging.getLogger("QNA.Committee.VoteChamber")

# Consensus thresholds
QUORUM = 3  # min agents that must vote (bull + bear + macro)
CONFIDENCE_THRESHOLD = 0.5  # weighted avg confidence needed
VETO_POWERS = {"risk_officer"}  # agents with absolute veto


@dataclass
class CommitteeVote:
    symbol: str
    final_action: str  # "buy", "sell", "hold"
    final_confidence: float
    bull_vote: AgentVote | None = None
    bear_vote: AgentVote | None = None
    macro_vote: AgentVote | None = None
    risk_vote: AgentVote | None = None
    execution: AgentVote | None = None
    all_evidence: list[str] = field(default_factory=list)
    risk_vetoed: bool = False
    risk_reason: str = ""
    consensus_strength: float = 0.0
    quorum_met: bool = False
    sl: float = 0.0
    tp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "action": self.final_action,
            "confidence": self.final_confidence,
            "consensus": self.consensus_strength,
            "quorum_met": self.quorum_met,
            "risk_vetoed": self.risk_vetoed,
            "risk_reason": self.risk_reason,
            "evidence": self.all_evidence,
            "sl": self.sl,
            "tp": self.tp,
            "bull": {"bias": self.bull_vote.bias, "conf": self.bull_vote.confidence,
                     "evidence": self.bull_vote.evidence} if self.bull_vote else None,
            "bear": {"bias": self.bear_vote.bias, "conf": self.bear_vote.confidence,
                     "evidence": self.bear_vote.evidence} if self.bear_vote else None,
            "macro": {"bias": self.macro_vote.bias, "conf": self.macro_vote.confidence,
                      "evidence": self.macro_vote.evidence} if self.macro_vote else None,
        }


class VoteChamber:
    """Convenes committee, collects votes, determines consensus."""

    def __init__(self):
        self.bull = BullAnalyst()
        self.bear = BearAnalyst()
        self.macro = MacroAnalyst()
        self.risk = RiskOfficer()
        self.execution = ExecutionAgent()

    def convene(self, symbol: str, df: Any, **kwargs) -> CommitteeVote:
        """Run all analysts, collect votes, determine consensus."""
        vote = CommitteeVote(symbol=symbol, final_action="hold", final_confidence=0.0)
        all_evidence = []
        real_votes = 0  # Track actual successful votes for quorum

        # 1. Run analysts (parallel-safe, all pure functions)
        try:
            vote.bull_vote = self.bull.analyze(symbol, df, **kwargs)
            all_evidence.extend([f"[BULL] {e}" for e in vote.bull_vote.evidence])
            real_votes += 1
        except Exception as exc:
            logger.warning("Bull analyst failed for %s: %s", symbol, exc)
            vote.bull_vote = AgentVote("bull_analyst", "neutral", 0.0, [f"error: {exc}"])

        try:
            vote.bear_vote = self.bear.analyze(symbol, df, **kwargs)
            all_evidence.extend([f"[BEAR] {e}" for e in vote.bear_vote.evidence])
            real_votes += 1
        except Exception as exc:
            logger.warning("Bear analyst failed for %s: %s", symbol, exc)
            vote.bear_vote = AgentVote("bear_analyst", "neutral", 0.0, [f"error: {exc}"])

        try:
            vote.macro_vote = self.macro.analyze(symbol, df, **kwargs)
            all_evidence.extend([f"[MACRO] {e}" for e in vote.macro_vote.evidence])
            real_votes += 1
        except Exception as exc:
            logger.warning("Macro analyst failed for %s: %s", symbol, exc)
            vote.macro_vote = AgentVote("macro_analyst", "neutral", 0.0, [f"error: {exc}"])

        # 2. Quorum check — only real votes count, not error fallbacks
        vote.quorum_met = real_votes >= QUORUM

        if not vote.quorum_met:
            vote.all_evidence = all_evidence
            vote.risk_reason = f"Quorum not met: {len(votes)}/{QUORUM}"
            return vote

        # 3. Weighted consensus
        weights = {"bull_analyst": 0.35, "bear_analyst": 0.35, "macro_analyst": 0.30}
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = 0.0

        for v in votes:
            w = weights.get(v.agent_name, 0.33)
            total_weight += w
            if v.bias == "bullish":
                bullish_score += w * v.confidence
            elif v.bias == "bearish":
                bearish_score += w * v.confidence

        if total_weight > 0:
            bullish_score /= total_weight
            bearish_score /= total_weight

        # 4. Determine direction
        if bullish_score > bearish_score and bullish_score >= CONFIDENCE_THRESHOLD:
            vote.final_action = "buy"
            vote.final_confidence = bullish_score
            vote.consensus_strength = bullish_score - bearish_score
        elif bearish_score > bullish_score and bearish_score >= CONFIDENCE_THRESHOLD:
            vote.final_action = "sell"
            vote.final_confidence = bearish_score
            vote.consensus_strength = bearish_score - bullish_score
        else:
            vote.final_action = "hold"
            vote.final_confidence = max(bullish_score, bearish_score)
            vote.consensus_strength = 0.0

        # 5. Risk Officer veto
        try:
            vote.risk_vote = self.risk.analyze(
                symbol, df,
                lot_size=kwargs.get("lot_size", 0.01),
                portfolio_state=kwargs.get("portfolio_state", {}))
            all_evidence.extend([f"[RISK] {e}" for e in vote.risk_vote.evidence])
            if vote.risk_vote.bias == "bearish":
                vote.risk_vetoed = True
                vote.risk_reason = "; ".join(vote.risk_vote.evidence)
                vote.final_action = "hold"
                vote.final_confidence = 0.0
        except Exception as exc:
            logger.warning("Risk officer failed: %s", exc)

        # 6. If approved, compute SL/TP via execution agent
        if vote.final_action in ("buy", "sell") and not vote.risk_vetoed:
            try:
                vote.execution = self.execution.analyze(
                    symbol, df,
                    entry_price=kwargs.get("entry_price", 0.0),
                    atr=kwargs.get("atr", 0.0),
                    side=vote.final_action,
                    timeframe=kwargs.get("timeframe", "M15"))
                # Extract SL/TP from evidence
                for e in vote.execution.evidence:
                    if e.startswith("SL="):
                        vote.sl = float(e.split("=")[1])
                    elif e.startswith("TP="):
                        vote.tp = float(e.split("=")[1])
                all_evidence.extend([f"[EXEC] {e}" for e in vote.execution.evidence])
            except Exception as exc:
                logger.warning("Execution agent failed: %s", exc)

        vote.all_evidence = all_evidence
        logger.info(
            "Committee %s: %s @ %.2f (consensus=%.2f, quorum=%s, risk_veto=%s)",
            symbol, vote.final_action, vote.final_confidence,
            vote.consensus_strength, vote.quorum_met, vote.risk_vetoed)

        return vote
