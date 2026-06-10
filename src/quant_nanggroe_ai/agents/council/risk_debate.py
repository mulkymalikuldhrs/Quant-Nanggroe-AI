"""
Risk Debate System — Multi-Perspective Risk Assessment
======================================================
Three-perspective debate for position sizing and risk management:
    - Aggressive: Favors larger positions, higher risk tolerance
    - Conservative: Favors capital preservation, minimal exposure
    - Neutral: Balanced perspective weighing both sides

The conservative view always wins ties (fail-safe design).

The debate evaluates:
    - Current market regime and volatility
    - Portfolio heat and correlation risk
    - Position sizing relative to account size
    - Leverage and exposure limits
    - Stop loss distance vs. ATR
    - Recent win/loss streak impact on risk tolerance

Output: Risk level (AGGRESSIVE/MODERATE/CONSERVATIVE) with
a numeric risk score and position sizing modifier.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════


class RiskLevel(str, Enum):
    """Risk level from the debate."""

    AGGRESSIVE = "AGGRESSIVE"
    MODERATE = "MODERATE"
    CONSERVATIVE = "CONSERVATIVE"


class RiskArgument(BaseModel):
    """A single risk argument."""

    claim: str
    perspective: RiskLevel
    metric: str = ""  # Which risk metric this refers to
    value: float | None = None
    limit: float | None = None
    weight: float = Field(ge=0.0, le=1.0, default=0.5)
    passed: bool = True


class RiskDebateResult(BaseModel):
    """Result of the risk debate."""

    risk_level: RiskLevel = RiskLevel.CONSERVATIVE
    risk_score: float = Field(ge=0.0, le=1.0, default=0.5)
    recommended_risk_pct: float = Field(ge=0.0, le=0.01, default=0.005)
    position_size_modifier: float = Field(ge=0.1, le=2.0, default=1.0)
    max_leverage: float = Field(ge=1.0, le=5.0, default=1.0)
    aggressive_score: float = Field(ge=0.0, le=1.0, default=0.0)
    conservative_score: float = Field(ge=0.0, le=1.0, default=0.0)
    key_points: list[str] = Field(default_factory=list)
    risk_factors: list[RiskArgument] = Field(default_factory=list)
    vetoed: bool = False
    veto_reasons: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# RISK EVALUATORS
# ══════════════════════════════════════════════════════════════════════


class VolatilityEvaluator:
    """Evaluates risk based on current volatility conditions."""

    def evaluate(self, data: dict[str, Any]) -> list[RiskArgument]:
        """Generate risk arguments from volatility metrics."""
        args = []
        indicators = data.get("indicators", {})
        atr_pct = indicators.get("atr_pct")
        adx_val = indicators.get("adx", {}).get("adx")

        if atr_pct is not None:
            if atr_pct > 3.0:
                args.append(RiskArgument(
                    claim="Extreme volatility — ATR > 3% of price",
                    perspective=RiskLevel.CONSERVATIVE,
                    metric="atr_pct", value=atr_pct, limit=3.0,
                    weight=0.9, passed=False,
                ))
            elif atr_pct > 2.0:
                args.append(RiskArgument(
                    claim="Elevated volatility — ATR > 2% of price",
                    perspective=RiskLevel.CONSERVATIVE,
                    metric="atr_pct", value=atr_pct, limit=2.0,
                    weight=0.7, passed=False,
                ))
            elif atr_pct < 0.5:
                args.append(RiskArgument(
                    claim="Low volatility — favorable for moderate position sizing",
                    perspective=RiskLevel.AGGRESSIVE,
                    metric="atr_pct", value=atr_pct, limit=0.5,
                    weight=0.6, passed=True,
                ))

        if adx_val is not None:
            if adx_val < 20:
                args.append(RiskArgument(
                    claim="Weak trend (ADX < 20) — ranging market, reduce exposure",
                    perspective=RiskLevel.CONSERVATIVE,
                    metric="adx", value=adx_val, limit=20.0,
                    weight=0.6, passed=False,
                ))
            elif adx_val > 40:
                args.append(RiskArgument(
                    claim="Strong trend (ADX > 40) — favorable for trend following",
                    perspective=RiskLevel.AGGRESSIVE,
                    metric="adx", value=adx_val, limit=40.0,
                    weight=0.7, passed=True,
                ))

        return args


class PortfolioHeatEvaluator:
    """Evaluates risk based on portfolio-level metrics."""

    def evaluate(self, data: dict[str, Any]) -> list[RiskArgument]:
        """Generate risk arguments from portfolio heat."""
        args = []
        portfolio = data.get("portfolio", {})

        open_positions = portfolio.get("open_positions", 0)
        max_positions = portfolio.get("max_positions", 10)
        total_exposure_pct = portfolio.get("total_exposure_pct", 0.0)
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0.0)
        weekly_pnl_pct = portfolio.get("weekly_pnl_pct", 0.0)
        correlation_score = portfolio.get("avg_correlation", 0.0)

        # Position count check
        if open_positions >= max_positions:
            args.append(RiskArgument(
                claim=f"Maximum positions reached ({open_positions}/{max_positions})",
                perspective=RiskLevel.CONSERVATIVE,
                metric="open_positions", value=float(open_positions),
                limit=float(max_positions), weight=0.9, passed=False,
            ))

        # Total exposure check
        if total_exposure_pct > 0.8:
            args.append(RiskArgument(
                claim=f"High total exposure ({total_exposure_pct:.0%})",
                perspective=RiskLevel.CONSERVATIVE,
                metric="total_exposure_pct", value=total_exposure_pct,
                limit=0.8, weight=0.8, passed=False,
            ))
        elif total_exposure_pct < 0.3:
            args.append(RiskArgument(
                claim=f"Low exposure ({total_exposure_pct:.0%}) — room for new positions",
                perspective=RiskLevel.AGGRESSIVE,
                metric="total_exposure_pct", value=total_exposure_pct,
                limit=0.3, weight=0.5, passed=True,
            ))

        # Daily loss check
        if daily_pnl_pct < -0.01:
            args.append(RiskArgument(
                claim=f"Daily loss limit reached ({daily_pnl_pct:.2%})",
                perspective=RiskLevel.CONSERVATIVE,
                metric="daily_pnl_pct", value=daily_pnl_pct,
                limit=-0.01, weight=1.0, passed=False,
            ))

        # Weekly loss check
        if weekly_pnl_pct < -0.03:
            args.append(RiskArgument(
                claim=f"Weekly loss limit reached ({weekly_pnl_pct:.2%})",
                perspective=RiskLevel.CONSERVATIVE,
                metric="weekly_pnl_pct", value=weekly_pnl_pct,
                limit=-0.03, weight=1.0, passed=False,
            ))

        # Correlation check
        if correlation_score > 0.7:
            args.append(RiskArgument(
                claim=f"High portfolio correlation ({correlation_score:.2f}) — diversification risk",
                perspective=RiskLevel.CONSERVATIVE,
                metric="avg_correlation", value=correlation_score,
                limit=0.7, weight=0.7, passed=False,
            ))

        return args


class StopLossEvaluator:
    """Evaluates risk based on stop loss placement."""

    def evaluate(self, data: dict[str, Any]) -> list[RiskArgument]:
        """Generate risk arguments from stop loss analysis."""
        args = []
        trade = data.get("trade", {})

        entry_price = trade.get("entry_price", 0)
        stop_loss = trade.get("stop_loss")
        atr = data.get("indicators", {}).get("atr_14")

        if stop_loss and entry_price > 0:
            stop_distance_pct = abs(entry_price - stop_loss) / entry_price

            if atr and atr > 0:
                stop_distance_atr = abs(entry_price - stop_loss) / atr

                if stop_distance_atr < 1.0:
                    args.append(RiskArgument(
                        claim=f"Stop too tight ({stop_distance_atr:.1f} ATR) — likely to be stopped out",
                        perspective=RiskLevel.CONSERVATIVE,
                        metric="stop_distance_atr", value=stop_distance_atr,
                        limit=1.0, weight=0.8, passed=False,
                    ))
                elif stop_distance_atr > 3.0:
                    args.append(RiskArgument(
                        claim=f"Stop too wide ({stop_distance_atr:.1f} ATR) — excessive risk per trade",
                        perspective=RiskLevel.CONSERVATIVE,
                        metric="stop_distance_atr", value=stop_distance_atr,
                        limit=3.0, weight=0.7, passed=False,
                    ))
                else:
                    args.append(RiskArgument(
                        claim=f"Stop well-placed ({stop_distance_atr:.1f} ATR) — appropriate risk",
                        perspective=RiskLevel.MODERATE,
                        metric="stop_distance_atr", value=stop_distance_atr,
                        limit=2.0, weight=0.6, passed=True,
                    ))

            # Risk per trade check
            if stop_distance_pct > 0.02:
                args.append(RiskArgument(
                    claim=f"Stop distance > 2% of entry ({stop_distance_pct:.2%}) — exceeds risk budget",
                    perspective=RiskLevel.CONSERVATIVE,
                    metric="stop_distance_pct", value=stop_distance_pct,
                    limit=0.02, weight=0.9, passed=False,
                ))

        return args


class MarketRegimeEvaluator:
    """Evaluates risk based on market regime."""

    REGIME_RISK_MAP = {
        "TRENDING_UP": (RiskLevel.AGGRESSIVE, 0.3, "Uptrend — favorable for long exposure"),
        "TRENDING_DOWN": (RiskLevel.CONSERVATIVE, 0.8, "Downtrend — reduce long exposure"),
        "RANGE": (RiskLevel.MODERATE, 0.5, "Ranging market — moderate caution"),
        "VOLATILE": (RiskLevel.CONSERVATIVE, 0.7, "Volatile conditions — heightened risk"),
        "RISK_OFF": (RiskLevel.CONSERVATIVE, 0.9, "Risk-off regime — minimize exposure"),
        "PANIC": (RiskLevel.CONSERVATIVE, 1.0, "Panic regime — no new positions"),
        "CALM": (RiskLevel.AGGRESSIVE, 0.2, "Calm market — favorable conditions"),
    }

    def evaluate(self, data: dict[str, Any]) -> list[RiskArgument]:
        """Generate risk arguments from market regime."""
        args = []
        regime = data.get("regime", "UNKNOWN")

        mapping = self.REGIME_RISK_MAP.get(regime)
        if mapping:
            level, weight, claim = mapping
            args.append(RiskArgument(
                claim=claim,
                perspective=level,
                metric="regime", weight=weight, passed=(level != RiskLevel.CONSERVATIVE),
            ))
        else:
            args.append(RiskArgument(
                claim=f"Unknown market regime ({regime}) — default to conservative",
                perspective=RiskLevel.CONSERVATIVE,
                metric="regime", weight=0.6, passed=False,
            ))

        return args


# ══════════════════════════════════════════════════════════════════════
# RISK DEBATE
# ══════════════════════════════════════════════════════════════════════


class RiskDebate:
    """
    Three-perspective risk debate for position sizing and risk management.

    Perspectives:
    - Aggressive: Favors larger positions when conditions support it
    - Conservative: Favors capital preservation, always raises red flags
    - Neutral: Balanced perspective, weighs evidence from both sides

    The conservative view always wins ties (fail-safe design).
    If any HARD veto is triggered (daily loss, weekly loss limits),
    the debate is immediately resolved as CONSERVATIVE.

    Args:
        base_risk_pct: Base risk per trade as fraction of equity
        min_risk_pct: Minimum risk per trade
        max_risk_pct: Maximum risk per trade (constitutional limit)

    Example:
        debate = RiskDebate()
        result = debate.run_debate(
            aggressive_args=[RiskArgument(claim="Strong uptrend confirmed")],
            conservative_args=[RiskArgument(claim="Elevated volatility")],
            data={"regime": "TRENDING_UP", "indicators": {"atr_pct": 1.5}},
        )
        print(result.risk_level, result.recommended_risk_pct)
    """

    def __init__(
        self,
        base_risk_pct: float = 0.005,
        min_risk_pct: float = 0.001,
        max_risk_pct: float = 0.01,
    ) -> None:
        self._base_risk_pct = base_risk_pct
        self._min_risk_pct = min_risk_pct
        self._max_risk_pct = max_risk_pct

        self._evaluators: list[Any] = [
            VolatilityEvaluator(),
            PortfolioHeatEvaluator(),
            StopLossEvaluator(),
            MarketRegimeEvaluator(),
        ]

    def run_debate(
        self,
        aggressive_args: list[RiskArgument | dict[str, str]] | None = None,
        conservative_args: list[RiskArgument | dict[str, str]] | None = None,
        data: dict[str, Any] | None = None,
    ) -> RiskDebateResult:
        """
        Run a risk debate and determine position sizing.

        Args:
            aggressive_args: User-provided aggressive arguments
            conservative_args: User-provided conservative arguments
            data: Market/portfolio data for evaluation

        Returns:
            RiskDebateResult with risk level and sizing recommendations
        """
        data = data or {}
        aggressive_args = aggressive_args or []
        conservative_args = conservative_args or []

        logger.info("Starting risk debate with data keys: %s", list(data.keys()))

        # Step 1: Gather all risk factors from evaluators
        all_risk_factors: list[RiskArgument] = []
        for evaluator in self._evaluators:
            try:
                factors = evaluator.evaluate(data)
                all_risk_factors.extend(factors)
            except Exception as exc:
                logger.warning("Evaluator %s failed: %s", type(evaluator).__name__, exc)

        # Step 2: Add user-provided arguments
        all_risk_factors.extend(self._normalize_args(aggressive_args, RiskLevel.AGGRESSIVE))
        all_risk_factors.extend(self._normalize_args(conservative_args, RiskLevel.CONSERVATIVE))

        # Step 3: Check for hard vetoes (immediate conservative override)
        vetoed, veto_reasons = self._check_vetoes(all_risk_factors)
        if vetoed:
            return RiskDebateResult(
                risk_level=RiskLevel.CONSERVATIVE,
                risk_score=1.0,
                recommended_risk_pct=self._min_risk_pct,
                position_size_modifier=0.25,
                max_leverage=1.0,
                aggressive_score=0.0,
                conservative_score=1.0,
                key_points=veto_reasons,
                risk_factors=all_risk_factors,
                vetoed=True,
                veto_reasons=veto_reasons,
            )

        # Step 4: Calculate scores
        aggressive_score = self._calculate_perspective_score(
            all_risk_factors, RiskLevel.AGGRESSIVE
        )
        conservative_score = self._calculate_perspective_score(
            all_risk_factors, RiskLevel.CONSERVATIVE
        )
        moderate_score = self._calculate_perspective_score(
            all_risk_factors, RiskLevel.MODERATE
        )

        # Step 5: Determine risk level (conservative wins ties)
        total = aggressive_score + conservative_score + moderate_score
        if total == 0:
            risk_level = RiskLevel.CONSERVATIVE
            risk_score = 0.7
        elif conservative_score >= aggressive_score:
            # Conservative bias (fail-safe)
            if conservative_score > aggressive_score * 1.5:
                risk_level = RiskLevel.CONSERVATIVE
                risk_score = 0.8
            else:
                risk_level = RiskLevel.MODERATE
                risk_score = 0.5
        else:
            # Aggressive wins, but with caution
            if aggressive_score > conservative_score * 2:
                risk_level = RiskLevel.AGGRESSIVE
                risk_score = 0.3
            else:
                risk_level = RiskLevel.MODERATE
                risk_score = 0.5

        # Step 6: Calculate position sizing
        recommended_risk = self._calculate_risk_pct(risk_level, risk_score)
        position_modifier = self._calculate_position_modifier(risk_level)
        max_leverage = self._calculate_max_leverage(risk_level)

        # Step 7: Extract key points
        key_points = self._extract_key_points(all_risk_factors)

        result = RiskDebateResult(
            risk_level=risk_level,
            risk_score=round(risk_score, 4),
            recommended_risk_pct=round(recommended_risk, 6),
            position_size_modifier=round(position_modifier, 2),
            max_leverage=max_leverage,
            aggressive_score=round(aggressive_score, 4),
            conservative_score=round(conservative_score, 4),
            key_points=key_points,
            risk_factors=all_risk_factors,
        )

        logger.info(
            "Risk debate result: %s (score=%.2f, risk=%.3f%%, modifier=%.2f)",
            risk_level.value, risk_score, recommended_risk * 100, position_modifier,
        )

        return result

    @staticmethod
    def _normalize_args(
        args: list[RiskArgument | dict[str, str]],
        default_perspective: RiskLevel,
    ) -> list[RiskArgument]:
        """Normalize argument inputs."""
        normalized = []
        for arg in args:
            if isinstance(arg, dict):
                normalized.append(RiskArgument(
                    claim=arg.get("claim", ""),
                    perspective=default_perspective,
                    metric=arg.get("metric", ""),
                    weight=float(arg.get("weight", 0.5)),
                ))
            else:
                normalized.append(arg)
        return normalized

    @staticmethod
    def _check_vetoes(factors: list[RiskArgument]) -> tuple[bool, list[str]]:
        """
        Check for hard veto conditions.

        Hard vetoes are triggered when:
        - Daily loss limit exceeded
        - Weekly loss limit exceeded
        - Maximum positions reached
        - Panic market regime

        Returns:
            (is_vetoed, reasons)
        """
        veto_reasons = []
        for factor in factors:
            if not factor.passed and factor.weight >= 0.9:
                veto_reasons.append(f"VETO: {factor.claim}")

        # Also check for explicit veto keywords
        for factor in factors:
            claim_lower = factor.claim.lower()
            if any(kw in claim_lower for kw in ["daily loss limit", "weekly loss limit", "panic"]):
                if not factor.passed:
                    veto_reasons.append(f"HARD VETO: {factor.claim}")

        return len(veto_reasons) > 0, veto_reasons

    @staticmethod
    def _calculate_perspective_score(
        factors: list[RiskArgument], perspective: RiskLevel
    ) -> float:
        """Calculate weighted score for a perspective."""
        relevant = [f for f in factors if f.perspective == perspective]
        if not relevant:
            return 0.0

        # Weight by both the argument weight and pass/fail status
        score = 0.0
        total_weight = 0.0
        for f in relevant:
            contribution = f.weight if f.passed else f.weight * 0.5
            score += contribution
            total_weight += f.weight

        return score / total_weight if total_weight > 0 else 0.0

    def _calculate_risk_pct(self, risk_level: RiskLevel, risk_score: float) -> float:
        """Calculate recommended risk percentage based on debate outcome."""
        if risk_level == RiskLevel.CONSERVATIVE:
            return self._min_risk_pct
        elif risk_level == RiskLevel.AGGRESSIVE:
            return min(self._base_risk_pct * 1.5, self._max_risk_pct)
        else:
            # Moderate: scale based on risk score
            return self._base_risk_pct * (0.5 + 0.5 * (1 - risk_score))

    @staticmethod
    def _calculate_position_modifier(risk_level: RiskLevel) -> float:
        """Calculate position size modifier."""
        modifiers = {
            RiskLevel.CONSERVATIVE: 0.5,
            RiskLevel.MODERATE: 1.0,
            RiskLevel.AGGRESSIVE: 1.5,
        }
        return modifiers.get(risk_level, 1.0)

    @staticmethod
    def _calculate_max_leverage(risk_level: RiskLevel) -> float:
        """Calculate maximum allowed leverage."""
        leverages = {
            RiskLevel.CONSERVATIVE: 1.0,
            RiskLevel.MODERATE: 1.0,
            RiskLevel.AGGRESSIVE: 1.0,  # Constitutional limit: no leverage
        }
        return leverages.get(risk_level, 1.0)

    @staticmethod
    def _extract_key_points(factors: list[RiskArgument]) -> list[str]:
        """Extract the most important risk points."""
        sorted_factors = sorted(factors, key=lambda f: f.weight, reverse=True)
        return [
            f"[{f.perspective.value}] {f.claim} (weight: {f.weight:.1f}, {'PASS' if f.passed else 'FAIL'})"
            for f in sorted_factors[:8]
        ]
