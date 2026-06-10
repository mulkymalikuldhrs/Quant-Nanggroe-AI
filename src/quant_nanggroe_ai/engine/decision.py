"""
Decision Synthesis Engine
=========================
From Quant-Nanggroe-AI + HermesQuantOS — Machine-readable decision table.

Compresses all signals into a single decision:
  - 1 Entry, 1 SL, 1-3 TPs
  - Risk Clearance: CLEAR / BLOCKED / PAUSE

The decision table is deterministic — same inputs always produce same output.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.types import (
    DecisionAction,
    MarketRegime,
    RiskClearance,
    VolatilityLevel,
)


class DecisionRule(BaseModel):
    """A single decision table rule."""

    id: str
    regime_allowed: list[MarketRegime]
    min_buy_pressure: float = 0.0
    max_buy_pressure: float = 1.0
    min_sell_pressure: float = 0.0
    max_sell_pressure: float = 1.0
    allowed_volatility: list[VolatilityLevel] = [
        VolatilityLevel.LOW,
        VolatilityLevel.NORMAL,
        VolatilityLevel.HIGH,
    ]
    min_confidence: float = 0.0
    action: DecisionAction = DecisionAction.NO_TRADE
    description: str = ""


class DecisionResult(BaseModel):
    """Result of decision synthesis."""

    action: DecisionAction = DecisionAction.NO_TRADE
    risk_clearance: RiskClearance = RiskClearance.BLOCKED
    reason: str = ""
    regime: MarketRegime = MarketRegime.UNKNOWN
    buy_pressure: float = 0.0
    sell_pressure: float = 0.0
    confidence: float = 0.0
    volatility: VolatilityLevel = VolatilityLevel.NORMAL
    matched_rules: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# Machine-Readable Decision Table
# ══════════════════════════════════════════════════════════════════════

DECISION_TABLE: list[DecisionRule] = [
    DecisionRule(
        id="DT001",
        regime_allowed=[MarketRegime.TRENDING_UP, MarketRegime.TRENDING, MarketRegime.RANGE, MarketRegime.MEAN_REVERT],
        min_buy_pressure=0.70,
        max_sell_pressure=0.30,
        allowed_volatility=[VolatilityLevel.LOW, VolatilityLevel.NORMAL],
        min_confidence=0.60,
        action=DecisionAction.ALLOW_LONG,
        description="Strong bullish pressure in safe regime",
    ),
    DecisionRule(
        id="DT002",
        regime_allowed=[MarketRegime.TRENDING_DOWN, MarketRegime.TRENDING, MarketRegime.RANGE, MarketRegime.MEAN_REVERT],
        min_sell_pressure=0.70,
        max_buy_pressure=0.30,
        allowed_volatility=[VolatilityLevel.LOW, VolatilityLevel.NORMAL],
        min_confidence=0.60,
        action=DecisionAction.ALLOW_SHORT,
        description="Strong bearish pressure in safe regime",
    ),
    DecisionRule(
        id="DT003",
        regime_allowed=[MarketRegime.TRENDING_UP, MarketRegime.TRENDING],
        min_buy_pressure=0.60,
        max_sell_pressure=0.40,
        allowed_volatility=[VolatilityLevel.LOW, VolatilityLevel.NORMAL, VolatilityLevel.HIGH],
        min_confidence=0.55,
        action=DecisionAction.ALLOW_LONG_TRENDING,
        description="Moderate bullish in trending regime",
    ),
    DecisionRule(
        id="DT004",
        regime_allowed=[MarketRegime.TRENDING_DOWN, MarketRegime.TRENDING],
        min_sell_pressure=0.60,
        max_buy_pressure=0.40,
        allowed_volatility=[VolatilityLevel.LOW, VolatilityLevel.NORMAL, VolatilityLevel.HIGH],
        min_confidence=0.55,
        action=DecisionAction.ALLOW_SHORT_TRENDING,
        description="Moderate bearish in trending regime",
    ),
    DecisionRule(
        id="DT005",
        regime_allowed=[MarketRegime.PANIC, MarketRegime.RISK_OFF, MarketRegime.NO_TRADE],
        min_buy_pressure=1.10,  # Impossible threshold = always blocked
        action=DecisionAction.NO_TRADE,
        description="Dangerous regime — all trading blocked",
    ),
    DecisionRule(
        id="DT006",
        regime_allowed=[MarketRegime.TRENDING_UP, MarketRegime.TRENDING, MarketRegime.RANGE, MarketRegime.MEAN_REVERT],
        min_buy_pressure=0.55,
        max_buy_pressure=0.69,
        allowed_volatility=[VolatilityLevel.LOW, VolatilityLevel.NORMAL],
        min_confidence=0.55,
        action=DecisionAction.WATCH_LONG,
        description="Weak bullish — monitor but don't enter",
    ),
    DecisionRule(
        id="DT007",
        regime_allowed=[MarketRegime.TRENDING_DOWN, MarketRegime.TRENDING, MarketRegime.RANGE, MarketRegime.MEAN_REVERT],
        min_sell_pressure=0.55,
        max_sell_pressure=0.69,
        allowed_volatility=[VolatilityLevel.LOW, VolatilityLevel.NORMAL],
        min_confidence=0.55,
        action=DecisionAction.WATCH_SHORT,
        description="Weak bearish — monitor but don't enter",
    ),
]


class DecisionSynthesisEngine:
    """
    Deterministic decision table that synthesizes pressure + regime → trade decision.

    The decision is made by evaluating the decision table rules in order.
    The first matching rule determines the action.

    Risk clearance is then applied on top:
    - CLEAR: ALLOW_* actions pass risk check
    - PAUSE: WATCH_* actions need monitoring
    - BLOCKED: NO_TRADE or risk limits exceeded
    """

    def __init__(self) -> None:
        self.last_decision: DecisionResult | None = None

    def evaluate(
        self,
        regime: MarketRegime,
        buy_pressure: float,
        sell_pressure: float,
        confidence: float,
        volatility: VolatilityLevel = VolatilityLevel.NORMAL,
        daily_pnl_pct: float = 0.0,
    ) -> DecisionResult:
        """
        Evaluate market state against decision table.

        Args:
            regime: Market regime classification
            buy_pressure: Normalized buy pressure (0-1)
            sell_pressure: Normalized sell pressure (0-1)
            confidence: Signal confidence (0-1)
            volatility: Market volatility level
            daily_pnl_pct: Current daily PnL percentage

        Returns:
            DecisionResult with action, risk_clearance, and details
        """
        matched_rules: list[str] = []

        for rule in DECISION_TABLE:
            # Check regime
            if regime not in rule.regime_allowed:
                continue

            # Check pressure thresholds
            if buy_pressure < rule.min_buy_pressure:
                continue
            if sell_pressure > rule.max_sell_pressure:
                continue
            if sell_pressure < rule.min_sell_pressure:
                continue
            if buy_pressure > rule.max_buy_pressure:
                continue

            # Check volatility
            if volatility not in rule.allowed_volatility:
                continue

            # Check confidence
            if confidence < rule.min_confidence:
                continue

            matched_rules.append(rule.id)

        # Determine action
        if not matched_rules:
            action = DecisionAction.NO_TRADE
            risk_clearance = RiskClearance.BLOCKED
            reason = "No decision rule matched — conditions not met"
        else:
            best_rule = next(r for r in DECISION_TABLE if r.id == matched_rules[0])
            action = best_rule.action

            # Additional risk clearance check
            from quant_nanggroe_ai.config import MAX_DAILY_LOSS

            if abs(min(0.0, daily_pnl_pct)) >= MAX_DAILY_LOSS:
                risk_clearance = RiskClearance.BLOCKED
                reason = f"Daily loss limit reached: {daily_pnl_pct:.2%}"
                action = DecisionAction.NO_TRADE
            elif "ALLOW" in action.value:
                risk_clearance = RiskClearance.CLEAR
                reason = best_rule.description
            elif "WATCH" in action.value:
                risk_clearance = RiskClearance.PAUSE
                reason = f"Monitoring: {best_rule.description}"
            else:
                risk_clearance = RiskClearance.BLOCKED
                reason = best_rule.description

        decision = DecisionResult(
            action=action,
            risk_clearance=risk_clearance,
            reason=reason,
            regime=regime,
            buy_pressure=round(buy_pressure, 4),
            sell_pressure=round(sell_pressure, 4),
            confidence=round(confidence, 4),
            volatility=volatility,
            matched_rules=matched_rules,
        )

        self.last_decision = decision
        return decision

    def status(self) -> dict[str, Any]:
        """Get current decision engine status."""
        return {
            "last_decision": self.last_decision.model_dump() if self.last_decision else None,
            "available_actions": [a.value for a in DecisionAction],
            "decision_rules": len(DECISION_TABLE),
            "timestamp": datetime.now().isoformat(),
        }
