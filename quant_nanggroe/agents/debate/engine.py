"""
Debate Engine - Multi-agent structured investment debate system.

Provides Signal, AgentOpinion, RiskMetrics, RiskManager, DebateResult, DebateEngine
for conducting weighted multi-agent debates on trading decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class Signal(str, Enum):
    # DEPRECATED — use quant_nanggroe.types.signals.SignalType instead.
    """Trading signal direction."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class AgentOpinion:
    """Opinion from a single agent in a debate."""
    agent_id: str
    signal: Signal
    confidence: float  # 0.0 to 1.0
    reasoning: str = ""
    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskMetrics:
    """Risk assessment metrics from debate consensus."""
    max_position_size: float = 0.0
    max_leverage: float = 1.0
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 15.0
    var_95: float = 0.0
    max_drawdown: float = 20.0


DEFAULT_RISK_CONFIG: Dict[str, float] = {
    "max_position_pct": 25.0,
    "max_leverage": 2.0,
    "stop_loss_pct": 5.0,
    "take_profit_pct": 15.0,
    "max_drawdown_pct": 20.0,
}


class RiskManager:
    """Risk manager for debate-driven trading decisions."""

    def __init__(self, config: Optional[Dict[str, float]] = None):
        self.config = config or dict(DEFAULT_RISK_CONFIG)

    def assess(
        self,
        opinions: List[AgentOpinion],
        volatility: float = 0.2,
    ) -> RiskMetrics:
        """Assess risk based on agent opinions and market volatility."""
        if not opinions:
            avg_confidence = 0.5
        else:
            total_weight = sum(o.weight for o in opinions)
            avg_confidence = (
                sum(o.confidence * o.weight for o in opinions) / total_weight
                if total_weight > 0 else 0.5
            )

        max_pos = self.config["max_position_pct"] * avg_confidence
        max_lev = min(
            self.config["max_leverage"],
            1.0 / volatility if volatility > 0 else self.config["max_leverage"],
        )
        stop_loss = self.config["stop_loss_pct"]
        take_profit = self.config["take_profit_pct"]
        var_95 = volatility * 1.645
        max_dd = self.config["max_drawdown_pct"]

        return RiskMetrics(
            max_position_size=round(max_pos, 4),
            max_leverage=round(max_lev, 4),
            stop_loss_pct=stop_loss,
            take_profit_pct=take_profit,
            var_95=round(var_95, 4),
            max_drawdown=max_dd,
        )


@dataclass
class DebateResult:
    """Result of a multi-agent debate."""
    consensus_signal: Signal = Signal.HOLD
    consensus_confidence: float = 0.0
    disagreement: bool = False
    opinions: List[AgentOpinion] = field(default_factory=list)
    risk: Optional[RiskMetrics] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    summary: str = ""


class DebateEngine:
    """Conducts structured multi-agent debates to reach trading decisions."""

    def __init__(
        self,
        min_agents: int = 2,
        risk_manager: Optional[RiskManager] = None,
    ):
        self.min_agents = min_agents
        self.risk_manager = risk_manager or RiskManager()

    def debate(
        self,
        opinions: List[AgentOpinion],
        volatility: float = 0.2,
    ) -> DebateResult:
        """Run a debate and return consensus result."""
        if len(opinions) < self.min_agents:
            raise ValueError(
                f"Need at least {self.min_agents} agents for debate, got {len(opinions)}"
            )

        # Weighted vote counting
        signal_weights: Dict[Signal, float] = {s: 0.0 for s in Signal}
        for op in opinions:
            signal_weights[op.signal] += op.confidence * op.weight

        # Determine consensus
        total_weighted = sum(signal_weights.values())
        if total_weighted == 0:
            return DebateResult(
                consensus_signal=Signal.HOLD,
                consensus_confidence=0.0,
                disagreement=True,
                opinions=opinions,
                risk=self.risk_manager.assess(opinions, volatility),
            )

        consensus_signal = max(signal_weights, key=signal_weights.get)
        consensus_confidence = signal_weights[consensus_signal] / total_weighted

        # Disagreement detection: check if signals are mixed
        unique_signals = {op.signal for op in opinions}
        disagreement = len(unique_signals) > 1 and consensus_confidence < 0.6

        # Build summary string
        sig_counts = {s: sum(1 for op in opinions if op.signal == s) for s in {op.signal for op in opinions}}
        summary = f"Debate: {consensus_signal.value} ({consensus_confidence:.0%}), {len(opinions)} agents, {len(unique_signals)} signals"
        if disagreement:
            summary += " — DISAGREEMENT"

        risk = self.risk_manager.assess(opinions, volatility)

        return DebateResult(
            consensus_signal=consensus_signal,
            consensus_confidence=round(consensus_confidence, 4),
            disagreement=disagreement,
            opinions=opinions,
            risk=risk,
            summary=summary,
        )


__all__ = [
    "Signal",
    "AgentOpinion",
    "RiskMetrics",
    "RiskManager",
    "DebateResult",
    "DebateEngine",
]
