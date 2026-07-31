"""TradingAgents-inspired multi-agent debate engine with risk management."""

import logging
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Signal direction — aliased to the canonical SignalType (single source of truth).
# Kept as name `Signal` for backward-compatible imports (BUY/SELL/HOLD unchanged).
from quant_nanggroe.types.signals import SignalType as Signal  # noqa: E402


@dataclass
class AgentOpinion:
    agent_id: str
    signal: Signal
    confidence: float
    reasoning: str
    weight: float = 1.0


@dataclass
class RiskMetrics:
    max_position_size: float
    max_leverage: float
    stop_loss_pct: float
    take_profit_pct: float
    var_95: float
    max_drawdown: float


class RiskManager:
    def __init__(self, config: Optional[Dict[str, float]] = None):
        self.config = config or {
            "max_position_pct": 25.0,
            "max_leverage": 2.0,
            "stop_loss_pct": 5.0,
            "take_profit_pct": 15.0,
            "max_drawdown_pct": 20.0,
        }

    def assess(self, opinions: List[AgentOpinion], volatility: float = 0.2) -> RiskMetrics:
        confidence = statistics.mean([o.confidence for o in opinions]) if opinions else 0.5
        var = volatility * 1.645
        return RiskMetrics(
            max_position_size=self.config["max_position_pct"] * confidence,
            max_leverage=min(self.config["max_leverage"], 1.0 / max(volatility, 0.01)),
            stop_loss_pct=self.config["stop_loss_pct"],
            take_profit_pct=self.config["take_profit_pct"],
            var_95=var,
            max_drawdown=self.config["max_drawdown_pct"],
        )


@dataclass
class DebateResult:
    consensus_signal: Signal
    consensus_confidence: float
    opinions: List[AgentOpinion] = field(default_factory=list)
    disagreement: bool = False
    risk: Optional[RiskMetrics] = None
    summary: str = ""


class DebateEngine:
    def __init__(self, min_agents: int = 2, risk_manager: Optional[RiskManager] = None):
        self.min_agents = min_agents
        self.risk_manager = risk_manager or RiskManager()

    def debate(self, opinions: List[AgentOpinion], volatility: float = 0.2) -> DebateResult:
        if len(opinions) < self.min_agents:
            raise ValueError(f"Need at least {self.min_agents} agents")
        total_weight = sum(o.weight for o in opinions)
        signals = {s: 0.0 for s in Signal}
        weighted_conf = 0.0
        for o in opinions:
            signals[o.signal] += o.weight
            weighted_conf += o.confidence * o.weight
        dominant = max(signals, key=signals.get)
        max_votes = signals[dominant]
        disagreement = max_votes <= total_weight * 0.5
        avg_conf = weighted_conf / total_weight
        consensus_conf = avg_conf * (max_votes / total_weight)
        risk = self.risk_manager.assess(opinions, volatility)
        return DebateResult(
            consensus_signal=dominant,
            consensus_confidence=consensus_conf,
            opinions=opinions,
            disagreement=disagreement,
            risk=risk,
            summary=f"Debate: {dominant.value} ({consensus_conf:.1%})",
        )