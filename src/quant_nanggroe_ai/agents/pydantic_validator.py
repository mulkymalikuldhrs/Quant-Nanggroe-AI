"""
PydanticAI-Style Validation for Agent Outputs
===============================================
Strict validation of trading agent outputs using Pydantic BaseModel
with field constraints, custom validators, and cross-field checks.

Validators:
    - ``TradingSignalValidator`` — Validates trading signals (direction,
      confidence, entry/exit parameters)
    - ``RiskAssessmentValidator`` — Validates risk assessments (drawdown
      limits, position sizing, exposure)
    - ``DecisionValidator`` — Validates decision synthesis outputs
      (action consistency, pressure alignment)

All validators follow the PydanticAI pattern of defining strict type
contracts that LLM outputs must satisfy, providing both validation
and structured error messages for feedback loops.

Design principles:
    - **Fail-fast**: Invalid data is rejected at construction time
    - **Actionable errors**: Validation messages explain *why* and
      suggest corrections
    - **Cross-field checks**: Signal direction must be consistent
      with entry/stop/take-profit ordering
    - **Bounds enforcement**: All numeric fields are range-constrained
    - **Composable**: Validators can be nested (a DecisionValidator
      contains TradingSignalValidator and RiskAssessmentValidator)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════


class SignalDirection(str, Enum):
    """Trading signal direction."""

    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class RiskLevel(str, Enum):
    """Risk severity level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DecisionAction(str, Enum):
    """Decision synthesis action."""

    ALLOW_LONG = "ALLOW_LONG"
    ALLOW_SHORT = "ALLOW_SHORT"
    ALLOW_LONG_TRENDING = "ALLOW_LONG_TRENDING"
    ALLOW_SHORT_TRENDING = "ALLOW_SHORT_TRENDING"
    WATCH_LONG = "WATCH_LONG"
    WATCH_SHORT = "WATCH_SHORT"
    NO_TRADE = "NO_TRADE"


class MarketRegime(str, Enum):
    """Market regime classification."""

    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    TRENDING = "TRENDING"
    RANGE = "RANGE"
    MEAN_REVERT = "MEAN_REVERT"
    RISK_OFF = "RISK_OFF"
    PANIC = "PANIC"
    NO_TRADE = "NO_TRADE"
    CALM = "CALM"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"


class RiskClearance(str, Enum):
    """Risk clearance status."""

    CLEAR = "CLEAR"
    BLOCKED = "BLOCKED"
    PAUSE = "PAUSE"


# ══════════════════════════════════════════════════════════════════════
# TRADING SIGNAL VALIDATOR
# ══════════════════════════════════════════════════════════════════════


class TradingSignalValidator(BaseModel):
    """Validates a trading signal produced by an agent.

    Enforces:
        - Signal direction is one of LONG, SHORT, NEUTRAL
        - Confidence is in [0.0, 1.0]
        - If direction is NEUTRAL, entry_price must be 0
        - If direction is LONG: stop_loss < entry_price < take_profit
        - If direction is SHORT: take_profit < entry_price < stop_loss
        - Position size is non-negative
        - Risk/reward ratio is non-negative
        - Symbol is non-empty

    Example::

        signal = TradingSignalValidator(
            symbol="AAPL",
            direction="LONG",
            confidence=0.75,
            entry_price=150.0,
            stop_loss=147.0,
            take_profit_targets=[156.0, 162.0],
            position_size=100.0,
        )
    """

    model_config = ConfigDict(extra="forbid")

    # ── Identity ──────────────────────────────────────────────────────
    symbol: str = Field(
        min_length=1,
        description="Trading instrument ticker (non-empty)",
    )
    timeframe: str = Field(
        default="1d",
        pattern=r"^\d+[mhdw]$",
        description="Timeframe string (e.g. '5m', '1h', '1d', '1w')",
    )

    # ── Signal ────────────────────────────────────────────────────────
    direction: SignalDirection = Field(
        description="Trading signal direction: LONG, SHORT, or NEUTRAL",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Signal confidence from 0.0 to 1.0",
    )

    # ── Entry parameters ──────────────────────────────────────────────
    entry_price: float = Field(
        ge=0.0,
        default=0.0,
        description="Entry price; must be >0 for LONG/SHORT signals",
    )
    stop_loss: float = Field(
        ge=0.0,
        default=0.0,
        description="Stop-loss price; must be set for directional signals",
    )
    take_profit_targets: list[float] = Field(
        default_factory=list,
        description="Ordered take-profit price levels",
    )

    # ── Position sizing ───────────────────────────────────────────────
    position_size: float = Field(
        ge=0.0,
        default=0.0,
        description="Position size in units; 0 for NEUTRAL signals",
    )
    risk_reward_ratio: float = Field(
        ge=0.0,
        default=0.0,
        description="Risk/reward ratio; must be >0 for directional signals",
    )

    # ── Metadata ──────────────────────────────────────────────────────
    strategy_name: str = Field(
        default="",
        description="Name of the strategy that generated this signal",
    )
    rationale: str = Field(
        default="",
        description="Chain-of-thought reasoning for the signal",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Signal generation timestamp",
    )

    # ── Field validators ──────────────────────────────────────────────

    @field_validator("confidence")
    @classmethod
    def _validate_confidence_precision(cls, v: float) -> float:
        """Round confidence to 4 decimal places to avoid float noise."""
        return round(v, 4)

    @field_validator("take_profit_targets")
    @classmethod
    def _validate_take_profit_targets(cls, v: list[float]) -> list[float]:
        """Ensure all take-profit targets are positive and deduplicated."""
        if any(tp <= 0 for tp in v):
            raise ValueError("All take_profit_targets must be > 0")
        if len(v) != len(set(round(tp, 8) for tp in v)):
            raise ValueError("take_profit_targets contains duplicates")
        return v

    @field_validator("position_size")
    @classmethod
    def _validate_position_size_precision(cls, v: float) -> float:
        """Round position size to 4 decimal places."""
        return round(v, 4)

    # ── Cross-field validators ────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_direction_consistency(self) -> "TradingSignalValidator":
        """Validate that signal direction is consistent with price levels.

        - NEUTRAL: entry_price must be 0, position_size must be 0
        - LONG:    stop_loss < entry_price < all take_profit_targets
        - SHORT:   all take_profit_targets < entry_price < stop_loss
        """
        if self.direction == SignalDirection.NEUTRAL:
            if self.entry_price != 0.0:
                raise ValueError(
                    "NEUTRAL signal must have entry_price=0.0, "
                    f"got {self.entry_price}"
                )
            if self.position_size != 0.0:
                raise ValueError(
                    "NEUTRAL signal must have position_size=0.0, "
                    f"got {self.position_size}"
                )
            return self

        # Directional signals require entry_price > 0
        if self.entry_price <= 0:
            raise ValueError(
                f"{self.direction.value} signal requires entry_price > 0, "
                f"got {self.entry_price}"
            )

        # Stop-loss must be set
        if self.stop_loss <= 0:
            raise ValueError(
                f"{self.direction.value} signal requires stop_loss > 0, "
                f"got {self.stop_loss}"
            )

        if self.direction == SignalDirection.LONG:
            if self.stop_loss >= self.entry_price:
                raise ValueError(
                    f"LONG signal requires stop_loss ({self.stop_loss}) "
                    f"< entry_price ({self.entry_price})"
                )
            for tp in self.take_profit_targets:
                if tp <= self.entry_price:
                    raise ValueError(
                        f"LONG signal requires all take_profit_targets "
                        f"> entry_price ({self.entry_price}), got {tp}"
                    )

        elif self.direction == SignalDirection.SHORT:
            if self.stop_loss <= self.entry_price:
                raise ValueError(
                    f"SHORT signal requires stop_loss ({self.stop_loss}) "
                    f"> entry_price ({self.entry_price})"
                )
            for tp in self.take_profit_targets:
                if tp >= self.entry_price:
                    raise ValueError(
                        f"SHORT signal requires all take_profit_targets "
                        f"< entry_price ({self.entry_price}), got {tp}"
                    )

        return self

    # ── Computed helpers ──────────────────────────────────────────────

    @property
    def risk_per_unit(self) -> float:
        """Absolute risk per unit (distance from entry to stop-loss)."""
        if self.direction == SignalDirection.NEUTRAL:
            return 0.0
        return abs(self.entry_price - self.stop_loss)

    @property
    def reward_per_unit(self) -> float:
        """Reward to first take-profit target per unit."""
        if self.direction == SignalDirection.NEUTRAL:
            return 0.0
        if not self.take_profit_targets:
            return 0.0
        return abs(self.take_profit_targets[0] - self.entry_price)

    @property
    def computed_risk_reward(self) -> float:
        """Compute R:R from entry/stop/TP (0 if not computable)."""
        risk = self.risk_per_unit
        if risk <= 0:
            return 0.0
        return self.reward_per_unit / risk


# ══════════════════════════════════════════════════════════════════════
# RISK ASSESSMENT VALIDATOR
# ══════════════════════════════════════════════════════════════════════


class RiskAssessmentValidator(BaseModel):
    """Validates a risk assessment produced by the risk engine.

    Enforces:
        - Risk percentage is within acceptable bounds
        - Position sizing respects maximum exposure limits
        - Drawdown limits are not exceeded
        - Risk level is consistent with numeric metrics
        - Clearance status matches the overall verdict

    Example::

        risk = RiskAssessmentValidator(
            symbol="AAPL",
            direction="LONG",
            risk_pct=0.8,
            max_risk_pct=2.0,
            position_value_pct=5.0,
            max_position_pct=10.0,
            daily_drawdown_pct=0.3,
            max_daily_drawdown=1.0,
            risk_level="LOW",
            clearance="CLEAR",
        )
    """

    model_config = ConfigDict(extra="forbid")

    # ── Identity ──────────────────────────────────────────────────────
    symbol: str = Field(min_length=1, description="Trading instrument ticker")
    direction: str = Field(
        description="Trade direction under assessment",
    )

    # ── Risk metrics ──────────────────────────────────────────────────
    risk_pct: float = Field(
        ge=0.0,
        le=100.0,
        description="Current risk as percentage of capital",
    )
    max_risk_pct: float = Field(
        gt=0.0,
        le=100.0,
        default=2.0,
        description="Maximum allowed risk percentage",
    )

    # ── Position sizing ───────────────────────────────────────────────
    position_value_pct: float = Field(
        ge=0.0,
        le=100.0,
        default=0.0,
        description="Position value as percentage of portfolio",
    )
    max_position_pct: float = Field(
        gt=0.0,
        le=100.0,
        default=10.0,
        description="Maximum allowed position size as percentage",
    )
    max_portfolio_exposure_pct: float = Field(
        gt=0.0,
        le=100.0,
        default=30.0,
        description="Maximum total portfolio exposure as percentage",
    )
    current_portfolio_exposure_pct: float = Field(
        ge=0.0,
        le=100.0,
        default=0.0,
        description="Current total portfolio exposure as percentage",
    )

    # ── Drawdown ──────────────────────────────────────────────────────
    daily_drawdown_pct: float = Field(
        ge=-100.0,
        le=0.0,
        default=0.0,
        description="Today's drawdown as percentage (negative)",
    )
    max_daily_drawdown: float = Field(
        gt=-100.0,
        le=0.0,
        default=-1.0,
        description="Maximum allowed daily drawdown (negative)",
    )
    weekly_drawdown_pct: float = Field(
        ge=-100.0,
        le=0.0,
        default=0.0,
        description="Weekly drawdown as percentage (negative)",
    )
    max_weekly_drawdown: float = Field(
        gt=-100.0,
        le=0.0,
        default=-3.0,
        description="Maximum allowed weekly drawdown (negative)",
    )

    # ── Leverage ──────────────────────────────────────────────────────
    leverage: float = Field(
        ge=0.0,
        default=1.0,
        description="Current leverage multiplier",
    )
    max_leverage: float = Field(
        ge=1.0,
        default=1.0,
        description="Maximum allowed leverage",
    )

    # ── Assessment ────────────────────────────────────────────────────
    risk_level: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Overall risk severity",
    )
    clearance: RiskClearance = Field(
        default=RiskClearance.BLOCKED,
        description="Risk clearance status",
    )
    veto_reasons: list[str] = Field(
        default_factory=list,
        description="List of veto reasons if clearance is BLOCKED",
    )

    # ── Metadata ──────────────────────────────────────────────────────
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    # ── Field validators ──────────────────────────────────────────────

    @field_validator("risk_pct", "position_value_pct")
    @classmethod
    def _round_percentages(cls, v: float) -> float:
        return round(v, 4)

    # ── Cross-field validators ────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_risk_consistency(self) -> "RiskAssessmentValidator":
        """Validate that risk metrics are internally consistent.

        Checks:
            - risk_pct <= max_risk_pct (if clearance is CLEAR)
            - position_value_pct <= max_position_pct (if clearance is CLEAR)
            - daily_drawdown >= max_daily_drawdown (drawdown is negative)
            - weekly_drawdown >= max_weekly_drawdown
            - leverage <= max_leverage
            - risk_level is consistent with metrics
            - clearance matches the overall assessment
        """
        # If clearance is CLEAR, basic limits must be respected
        if self.clearance == RiskClearance.CLEAR:
            if self.risk_pct > self.max_risk_pct:
                raise ValueError(
                    f"Clearance is CLEAR but risk_pct ({self.risk_pct}%) "
                    f"exceeds max_risk_pct ({self.max_risk_pct}%)"
                )
            if self.position_value_pct > self.max_position_pct:
                raise ValueError(
                    f"Clearance is CLEAR but position_value_pct "
                    f"({self.position_value_pct}%) exceeds max_position_pct "
                    f"({self.max_position_pct}%)"
                )
            if self.leverage > self.max_leverage:
                raise ValueError(
                    f"Clearance is CLEAR but leverage ({self.leverage}x) "
                    f"exceeds max_leverage ({self.max_leverage}x)"
                )

        # Drawdown limits (note: drawdowns are negative, so "exceeded"
        # means drawdown is more negative than the limit)
        if self.daily_drawdown_pct < self.max_daily_drawdown:
            raise ValueError(
                f"Daily drawdown ({self.daily_drawdown_pct}%) exceeds "
                f"limit ({self.max_daily_drawdown}%)"
            )
        if self.weekly_drawdown_pct < self.max_weekly_drawdown:
            raise ValueError(
                f"Weekly drawdown ({self.weekly_drawdown_pct}%) exceeds "
                f"limit ({self.max_weekly_drawdown}%)"
            )

        # Portfolio exposure check
        new_exposure = self.current_portfolio_exposure_pct + self.position_value_pct
        if new_exposure > self.max_portfolio_exposure_pct:
            if self.clearance == RiskClearance.CLEAR:
                raise ValueError(
                    f"Clearance is CLEAR but total exposure "
                    f"({new_exposure:.2f}%) would exceed max "
                    f"({self.max_portfolio_exposure_pct}%)"
                )

        # Risk level consistency
        if self.risk_level == RiskLevel.LOW:
            if self.risk_pct > self.max_risk_pct * 0.5:
                raise ValueError(
                    f"risk_level is LOW but risk_pct ({self.risk_pct}%) "
                    f"exceeds 50% of max ({self.max_risk_pct * 0.5}%)"
                )
        elif self.risk_level == RiskLevel.CRITICAL:
            if self.clearance == RiskClearance.CLEAR:
                raise ValueError(
                    "risk_level is CRITICAL but clearance is CLEAR — "
                    "critical risk must be BLOCKED"
                )

        # Veto reasons must be provided when clearance is BLOCKED
        if self.clearance == RiskClearance.BLOCKED and not self.veto_reasons:
            raise ValueError(
                "clearance is BLOCKED but no veto_reasons provided — "
                "blocked trades must explain why"
            )

        return self

    # ── Computed helpers ──────────────────────────────────────────────

    @property
    def risk_budget_used_pct(self) -> float:
        """Percentage of risk budget consumed (0-100+)."""
        if self.max_risk_pct <= 0:
            return 0.0
        return (self.risk_pct / self.max_risk_pct) * 100.0

    @property
    def is_within_limits(self) -> bool:
        """Whether all risk limits are within bounds (convenience)."""
        return (
            self.risk_pct <= self.max_risk_pct
            and self.position_value_pct <= self.max_position_pct
            and self.daily_drawdown_pct >= self.max_daily_drawdown
            and self.weekly_drawdown_pct >= self.max_weekly_drawdown
            and self.leverage <= self.max_leverage
        )


# ══════════════════════════════════════════════════════════════════════
# DECISION VALIDATOR
# ══════════════════════════════════════════════════════════════════════


class DecisionValidator(BaseModel):
    """Validates a decision synthesis output from the strategist agent.

    Enforces:
        - Decision action is consistent with regime and pressures
        - Risk clearance matches the decision action
        - Confidence is consistent with pressure alignment
        - No-trade regimes produce NO_TRADE actions
        - Direction-specific actions match pressure direction

    Example::

        decision = DecisionValidator(
            action="ALLOW_LONG",
            regime="TRENDING_UP",
            buy_pressure=0.72,
            sell_pressure=0.28,
            confidence=0.78,
            volatility="NORMAL",
            risk_clearance="CLEAR",
            reason="Strong bullish pressure in trending regime",
        )
    """

    model_config = ConfigDict(extra="forbid")

    # ── Decision ──────────────────────────────────────────────────────
    action: DecisionAction = Field(
        description="Synthesised decision action",
    )
    reason: str = Field(
        min_length=1,
        description="Human-readable reason for the decision",
    )

    # ── Market context ────────────────────────────────────────────────
    regime: MarketRegime = Field(
        default=MarketRegime.UNKNOWN,
        description="Current market regime",
    )
    volatility: str = Field(
        default="NORMAL",
        description="Volatility classification: LOW, NORMAL, HIGH",
    )

    # ── Pressures ─────────────────────────────────────────────────────
    buy_pressure: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Normalized buy pressure [0, 1]",
    )
    sell_pressure: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Normalized sell pressure [0, 1]",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Decision confidence [0, 1]",
    )

    # ── Risk ──────────────────────────────────────────────────────────
    risk_clearance: RiskClearance = Field(
        default=RiskClearance.BLOCKED,
        description="Risk clearance from the risk engine",
    )

    # ── Metadata ──────────────────────────────────────────────────────
    matched_rules: list[str] = Field(
        default_factory=list,
        description="Decision rules that matched",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    # ── Field validators ──────────────────────────────────────────────

    @field_validator("confidence")
    @classmethod
    def _round_confidence(cls, v: float) -> float:
        return round(v, 4)

    @field_validator("buy_pressure", "sell_pressure")
    @classmethod
    def _round_pressures(cls, v: float) -> float:
        return round(v, 4)

    @field_validator("volatility")
    @classmethod
    def _validate_volatility(cls, v: str) -> str:
        allowed = {"LOW", "NORMAL", "HIGH"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(
                f"volatility must be one of {allowed}, got '{v}'"
            )
        return v_upper

    # ── Cross-field validators ────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_action_consistency(self) -> "DecisionValidator":
        """Validate that decision action is consistent with context.

        Checks:
            - NO_TRADE / PANIC / RISK_OFF regimes → NO_TRADE action
            - ALLOW_LONG* requires buy_pressure > sell_pressure
            - ALLOW_SHORT* requires sell_pressure > buy_pressure
            - BLOCKED clearance → only NO_TRADE or WATCH_* actions
            - Confidence >= 0.5 for directional ALLOW_* actions
        """
        # No-trade regimes must produce NO_TRADE
        no_trade_regimes = {
            MarketRegime.NO_TRADE,
            MarketRegime.PANIC,
            MarketRegime.RISK_OFF,
        }
        if self.regime in no_trade_regimes and self.action != DecisionAction.NO_TRADE:
            raise ValueError(
                f"Regime {self.regime.value} requires action=NO_TRADE, "
                f"got {self.action.value}"
            )

        # Long actions require buy_pressure > sell_pressure
        long_actions = {
            DecisionAction.ALLOW_LONG,
            DecisionAction.ALLOW_LONG_TRENDING,
        }
        if self.action in long_actions:
            if self.buy_pressure <= self.sell_pressure:
                raise ValueError(
                    f"{self.action.value} requires buy_pressure "
                    f"({self.buy_pressure}) > sell_pressure "
                    f"({self.sell_pressure})"
                )

        # Short actions require sell_pressure > buy_pressure
        short_actions = {
            DecisionAction.ALLOW_SHORT,
            DecisionAction.ALLOW_SHORT_TRENDING,
        }
        if self.action in short_actions:
            if self.sell_pressure <= self.buy_pressure:
                raise ValueError(
                    f"{self.action.value} requires sell_pressure "
                    f"({self.sell_pressure}) > buy_pressure "
                    f"({self.buy_pressure})"
                )

        # Trending-specific actions require trending regime
        trending_actions = {
            DecisionAction.ALLOW_LONG_TRENDING,
            DecisionAction.ALLOW_SHORT_TRENDING,
        }
        trending_regimes = {
            MarketRegime.TRENDING_UP,
            MarketRegime.TRENDING_DOWN,
            MarketRegime.TRENDING,
        }
        if self.action in trending_actions and self.regime not in trending_regimes:
            raise ValueError(
                f"{self.action.value} requires trending regime "
                f"(TRENDING_UP/DOWN), got {self.regime.value}"
            )

        # ALLOW_LONG_TRENDING specifically requires TRENDING_UP
        if (
            self.action == DecisionAction.ALLOW_LONG_TRENDING
            and self.regime == MarketRegime.TRENDING_DOWN
        ):
            raise ValueError(
                "ALLOW_LONG_TRENDING is inconsistent with TRENDING_DOWN regime"
            )

        # ALLOW_SHORT_TRENDING specifically requires TRENDING_DOWN
        if (
            self.action == DecisionAction.ALLOW_SHORT_TRENDING
            and self.regime == MarketRegime.TRENDING_UP
        ):
            raise ValueError(
                "ALLOW_SHORT_TRENDING is inconsistent with TRENDING_UP regime"
            )

        # Blocked clearance can only produce NO_TRADE or WATCH actions
        if self.risk_clearance == RiskClearance.BLOCKED:
            safe_actions = {
                DecisionAction.NO_TRADE,
                DecisionAction.WATCH_LONG,
                DecisionAction.WATCH_SHORT,
            }
            if self.action not in safe_actions:
                raise ValueError(
                    f"risk_clearance is BLOCKED but action is "
                    f"{self.action.value} — only NO_TRADE or WATCH_* "
                    f"actions are permitted when risk is blocked"
                )

        # Directional ALLOW actions require minimum confidence
        if self.action in long_actions | short_actions:
            if self.confidence < 0.5:
                raise ValueError(
                    f"{self.action.value} requires confidence >= 0.5, "
                    f"got {self.confidence}"
                )

        return self

    # ── Computed helpers ──────────────────────────────────────────────

    @property
    def net_pressure(self) -> float:
        """Net pressure: buy_pressure - sell_pressure."""
        return self.buy_pressure - self.sell_pressure

    @property
    def pressure_alignment(self) -> str:
        """Whether pressures align with the action.

        Returns:
            "aligned" | "misaligned" | "neutral"
        """
        long_actions = {
            DecisionAction.ALLOW_LONG,
            DecisionAction.ALLOW_LONG_TRENDING,
            DecisionAction.WATCH_LONG,
        }
        short_actions = {
            DecisionAction.ALLOW_SHORT,
            DecisionAction.ALLOW_SHORT_TRENDING,
            DecisionAction.WATCH_SHORT,
        }

        if self.action in long_actions:
            return "aligned" if self.buy_pressure > self.sell_pressure else "misaligned"
        elif self.action in short_actions:
            return "aligned" if self.sell_pressure > self.buy_pressure else "misaligned"
        return "neutral"

    @property
    def is_actionable(self) -> bool:
        """Whether this decision represents an actionable trade signal."""
        return self.action not in {
            DecisionAction.NO_TRADE,
            DecisionAction.WATCH_LONG,
            DecisionAction.WATCH_SHORT,
        }


# ══════════════════════════════════════════════════════════════════════
# COMPOSITE VALIDATOR — full pipeline validation
# ══════════════════════════════════════════════════════════════════════


class CompositeValidatorResult(BaseModel):
    """Result of validating a full trading pipeline output.

    Contains all three sub-validators and cross-validator checks
    ensuring they are mutually consistent.
    """

    model_config = ConfigDict(extra="forbid")

    signal: TradingSignalValidator
    risk: RiskAssessmentValidator
    decision: DecisionValidator

    # ── Cross-validator ───────────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_cross_consistency(self) -> "CompositeValidatorResult":
        """Validate that signal, risk, and decision are mutually consistent.

        Checks:
            - Signal direction matches decision action direction
            - Risk clearance matches decision action permission
            - Symbol consistency across all three validators
        """
        # Signal direction must match decision action direction
        long_actions = {
            DecisionAction.ALLOW_LONG,
            DecisionAction.ALLOW_LONG_TRENDING,
            DecisionAction.WATCH_LONG,
        }
        short_actions = {
            DecisionAction.ALLOW_SHORT,
            DecisionAction.ALLOW_SHORT_TRENDING,
            DecisionAction.WATCH_SHORT,
        }

        if self.decision.action in long_actions:
            if self.signal.direction not in (SignalDirection.LONG, SignalDirection.NEUTRAL):
                raise ValueError(
                    f"Decision action {self.decision.action.value} is long-biased "
                    f"but signal direction is {self.signal.direction.value}"
                )
        elif self.decision.action in short_actions:
            if self.signal.direction not in (SignalDirection.SHORT, SignalDirection.NEUTRAL):
                raise ValueError(
                    f"Decision action {self.decision.action.value} is short-biased "
                    f"but signal direction is {self.signal.direction.value}"
                )

        if self.decision.action == DecisionAction.NO_TRADE:
            if self.signal.direction != SignalDirection.NEUTRAL:
                raise ValueError(
                    f"Decision is NO_TRADE but signal direction is "
                    f"{self.signal.direction.value} — must be NEUTRAL"
                )

        # Risk clearance must match decision
        if self.risk.clearance == RiskClearance.BLOCKED:
            if self.decision.is_actionable:
                raise ValueError(
                    f"Risk clearance is BLOCKED but decision action "
                    f"{self.decision.action.value} is actionable"
                )

        # Symbol consistency
        if self.signal.symbol != self.risk.symbol:
            raise ValueError(
                f"Symbol mismatch: signal has '{self.signal.symbol}' "
                f"but risk has '{self.risk.symbol}'"
            )

        return self


# ══════════════════════════════════════════════════════════════════════
# VALIDATION HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════


def validate_trading_signal(data: dict[str, Any]) -> tuple[TradingSignalValidator | None, list[str]]:
    """Validate a trading signal dict and return (model, errors).

    This is the primary entry point for agent output validation.
    On success, returns the validated model and an empty error list.
    On failure, returns None and a list of human-readable error strings.

    Args:
        data: Dict of signal attributes to validate.

    Returns:
        Tuple of (validated model or None, list of error messages).
    """
    try:
        model = TradingSignalValidator(**data)
        return model, []
    except Exception as exc:
        errors = _extract_validation_errors(exc)
        return None, errors


def validate_risk_assessment(data: dict[str, Any]) -> tuple[RiskAssessmentValidator | None, list[str]]:
    """Validate a risk assessment dict and return (model, errors).

    Args:
        data: Dict of risk assessment attributes to validate.

    Returns:
        Tuple of (validated model or None, list of error messages).
    """
    try:
        model = RiskAssessmentValidator(**data)
        return model, []
    except Exception as exc:
        errors = _extract_validation_errors(exc)
        return None, errors


def validate_decision(data: dict[str, Any]) -> tuple[DecisionValidator | None, list[str]]:
    """Validate a decision synthesis dict and return (model, errors).

    Args:
        data: Dict of decision attributes to validate.

    Returns:
        Tuple of (validated model or None, list of error messages).
    """
    try:
        model = DecisionValidator(**data)
        return model, []
    except Exception as exc:
        errors = _extract_validation_errors(exc)
        return None, errors


def validate_composite(
    signal_data: dict[str, Any],
    risk_data: dict[str, Any],
    decision_data: dict[str, Any],
) -> tuple[CompositeValidatorResult | None, list[str]]:
    """Validate a complete trading pipeline output.

    Validates each sub-component individually, then performs
    cross-validation across all three.

    Args:
        signal_data: Dict for TradingSignalValidator.
        risk_data: Dict for RiskAssessmentValidator.
        decision_data: Dict for DecisionValidator.

    Returns:
        Tuple of (validated composite or None, list of all error messages).
    """
    all_errors: list[str] = []

    signal, signal_errors = validate_trading_signal(signal_data)
    all_errors.extend(signal_errors)

    risk, risk_errors = validate_risk_assessment(risk_data)
    all_errors.extend(risk_errors)

    decision, decision_errors = validate_decision(decision_data)
    all_errors.extend(decision_errors)

    if all_errors:
        return None, all_errors

    # Cross-validation
    try:
        composite = CompositeValidatorResult(
            signal=signal,  # type: ignore[arg-type]
            risk=risk,  # type: ignore[arg-type]
            decision=decision,  # type: ignore[arg-type]
        )
        return composite, []
    except Exception as exc:
        cross_errors = _extract_validation_errors(exc)
        return None, cross_errors


def _extract_validation_errors(exc: Exception) -> list[str]:
    """Extract human-readable error messages from a Pydantic ValidationError."""
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        errors = []
        for err in exc.errors():
            loc = " → ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", str(err))
            errors.append(f"{loc}: {msg}" if loc else msg)
        return errors
    return [str(exc)]
