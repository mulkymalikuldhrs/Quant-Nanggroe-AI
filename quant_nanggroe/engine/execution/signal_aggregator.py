"""Signal Aggregation Engine — ONE position per symbol, fixed risk.

FAZE 1 Sprint 1 (v8.0 replan): replaces fragmented multi-strategy entries
with institutional signal netting. Multiple strategies vote, the aggregator
produces ONE decision per symbol with FIXED 0.5% equity risk regardless of
how many strategies agree.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger("QNA.SignalAggregator")


@dataclass
class StrategyVote:
    """A single strategy's vote for one symbol in one cycle."""
    strategy_name: str
    direction: str          # "buy" | "sell" | "hold"
    confidence: float       # 0.0 - 1.0
    weight: float = 1.0     # from allocation/CPCV evidence
    tuned_params: dict = field(default_factory=dict)


@dataclass
class AggregatedSignal:
    """The NET result of aggregating all strategy votes for one symbol."""
    symbol: str
    direction: str              # "buy" | "sell" | "hold"
    conviction: float           # aggregate confidence 0.0-1.0
    buy_weight: float           # total weight of BUY voters
    sell_weight: float          # total weight of SELL voters
    contributors: List[str]     # strategies that voted WITH the majority
    opposers: List[str]         # strategies that voted AGAINST
    abstainers: List[str]      # strategies that voted HOLD
    risk_pct: float             # fixed risk per symbol (0.005 = 0.5%)
    votes_detail: List[Dict[str, Any]]

    @property
    def should_trade(self) -> bool:
        return self.direction != "hold" and self.conviction > 0.30

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "conviction": round(self.conviction, 4),
            "buy_weight": round(self.buy_weight, 4),
            "sell_weight": round(self.sell_weight, 4),
            "contributors": self.contributors,
            "opposers": self.opposers,
            "abstainers": self.abstainers,
            "risk_pct": self.risk_pct,
            "should_trade": self.should_trade,
        }


# Minimum net conviction before an entry is placed
MIN_CONVICTION = 0.30

# Fixed risk per symbol — constitutional, not affected by confidence
FIXED_RISK_PER_SYMBOL = 0.005  # 0.5%


class SignalAggregator:
    """Aggregates multiple strategy signals into ONE decision per symbol."""

    def __init__(self,
                 min_conviction: float = MIN_CONVICTION,
                 risk_per_symbol: float = FIXED_RISK_PER_SYMBOL):
        self.min_conviction = min_conviction
        self.risk_per_symbol = risk_per_symbol

    def aggregate(self, symbol: str,
                  votes: List[StrategyVote]) -> AggregatedSignal:
        """Net all strategy votes into a single trading decision.

        Rules:
        1. Each vote contributes weight × confidence × direction_sign
        2. Net > +threshold → BUY; Net < -threshold → SELL; else HOLD
        3. Conviction = |net| / total_weight (normalized 0-1)
        4. Risk is FIXED per symbol (not scaled by confidence or vote count)
        """
        if not votes:
            return AggregatedSignal(
                symbol=symbol, direction="hold", conviction=0.0,
                buy_weight=0.0, sell_weight=0.0,
                contributors=[], opposers=[], abstainers=[],
                risk_pct=self.risk_per_symbol, votes_detail=[],
            )

        buy_w = 0.0
        sell_w = 0.0
        total_w = 0.0
        contributors: List[str] = []
        opposers: List[str] = []
        abstainers: List[str] = []

        for vote in votes:
            w = vote.weight * vote.confidence
            total_w += vote.weight

            if vote.direction == "buy":
                buy_w += w
                if vote.confidence > 0:
                    contributors.append(vote.strategy_name)
            elif vote.direction == "sell":
                sell_w += w
                if vote.confidence > 0:
                    contributors.append(vote.strategy_name)
            else:  # hold
                abstainers.append(vote.strategy_name)

        net = buy_w - sell_w

        # Determine direction
        if net > 0:
            direction = "buy"
        elif net < 0:
            direction = "sell"
        else:
            direction = "hold"

        # Compute normalized conviction
        if total_w > 0:
            raw_conviction = abs(net) / total_w
            # Boost when more strategies agree (consensus bonus)
            n_voting = len([v for v in votes if v.direction != "hold"])
            consensus_bonus = min(n_voting / len(votes), 1.0) if votes else 0
            conviction = min(1.0, raw_conviction * (0.7 + 0.3 * consensus_bonus))
        else:
            conviction = 0.0

        # Classify contributors vs opposers based on final direction
        if direction == "buy":
            contributors = [v.strategy_name for v in votes if v.direction == "buy"]
            opposers = [v.strategy_name for v in votes if v.direction == "sell"]
        elif direction == "sell":
            contributors = [v.strategy_name for v in votes if v.direction == "sell"]
            opposers = [v.strategy_name for v in votes if v.direction == "buy"]

        # Override: if conviction below threshold → hold
        if conviction < self.min_conviction:
            logger.info(
                "%s: conviction %.3f < threshold %.3f → HOLD",
                symbol, conviction, self.min_conviction)
            direction = "hold"

        return AggregatedSignal(
            symbol=symbol,
            direction=direction,
            conviction=round(conviction, 4),
            buy_weight=round(buy_w, 4),
            sell_weight=round(sell_w, 4),
            contributors=sorted(set(contributors)),
            opposers=sorted(set(opposers)),
            abstainers=sorted(set(abstainers)),
            risk_pct=self.risk_per_symbol,
            votes_detail=[
                {"strategy": v.strategy_name, "direction": v.direction,
                 "confidence": v.confidence, "weight": v.weight}
                for v in votes
            ],
        )
