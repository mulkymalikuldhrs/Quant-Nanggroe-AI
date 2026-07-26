from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from quant_nanggroe.engine.risk.constants import MAX_DAILY_LOSS as DAILY_LOSS_LIMIT, MAX_WEEKLY_LOSS as WEEKLY_LOSS_LIMIT

logger = logging.getLogger(__name__)


class VetoLevel(Enum):
    PASS = "pass"
    WARNING = "warning"
    VETO = "veto"
    HARD_STOP = "hard_stop"


class VetoReason(Enum):
    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"
    WEEKLY_LOSS_EXCEEDED = "weekly_loss_exceeded"
    POSITION_CONCENTRATION = "position_concentration"
    CORRELATION_EXPOSURE = "correlation_exposure"
    VOLATILITY_SPIKE = "volatility_spike"
    DRAWDOWN_LIMIT = "drawdown_limit"
    LEVERAGE_LIMIT = "leverage_limit"
    NEWS_BREAKER = "news_breaker"
    MACRO_CONTRADICTION = "macro_contradiction"
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"
    SYSTEM_ERROR = "system_error"
    TAIL_RISK_EMERGENCY = "tail_risk_emergency"
    REGIME_MISMATCH = "regime_mismatch"


@dataclass
class VetoResult:
    level: VetoLevel
    reason: VetoReason | None = None
    detail: str = ""
    risk_score: float = 0.0


@dataclass
class GuardState:
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    current_drawdown: float = 0.0
    current_leverage: float = 0.0
    volatility_regime: str = "normal"
    tail_risk_level: str = "none"
    correlation_alert: bool = False
    position_concentration_pct: float = 0.0
    news_breaker_active: bool = False
    macro_contradiction: bool = False
    liquidity_score: float = 1.0
    system_healthy: bool = True

    vetos_triggered: list[str] = field(default_factory=list)


class GovernanceVetoGuard:
    """Multi-layer governance veto — institutional-grade fail-closed guard.

    Layers (checked in order):
      1. P&L limits (daily/weekly hard caps)
      2. Risk limits (drawdown, leverage, concentration)
      3. Correlation & regime
      4. News / macro contradiction
      5. Liquidity & system health
      6. Tail risk emergency

    Architecture ported from: ai-market-maker/governance/risk_guard.py
                              BlackHornet circuit-breaker pattern
    """

    def __init__(self):
        self.state = GuardState()
        self._veto_log: list[dict[str, Any]] = []

    def update_state(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self.state, k):
                setattr(self.state, k, v)

    def check(self) -> VetoResult:
        results: list[VetoResult] = []

        # Layer 1: P&L limits
        if self.state.daily_pnl_pct <= -DAILY_LOSS_LIMIT:
            results.append(VetoResult(VetoLevel.HARD_STOP, VetoReason.DAILY_LOSS_EXCEEDED,
                f"Daily loss {self.state.daily_pnl_pct*100:.1f}% >= limit {DAILY_LOSS_LIMIT*100:.1f}%", 1.0))

        if self.state.weekly_pnl_pct <= -WEEKLY_LOSS_LIMIT:
            results.append(VetoResult(VetoLevel.HARD_STOP, VetoReason.WEEKLY_LOSS_EXCEEDED,
                f"Weekly loss {self.state.weekly_pnl_pct*100:.1f}% >= limit {WEEKLY_LOSS_LIMIT*100:.1f}%", 1.0))

        # Layer 2: Risk limits
        if self.state.current_drawdown > DAILY_LOSS_LIMIT * 3:
            results.append(VetoResult(VetoLevel.VETO, VetoReason.DRAWDOWN_LIMIT,
                f"Drawdown {self.state.current_drawdown*100:.1f}% exceeds threshold", 0.9))

        if self.state.position_concentration_pct > 0.25:
            results.append(VetoResult(VetoLevel.VETO, VetoReason.POSITION_CONCENTRATION,
                f"Position concentration {self.state.position_concentration_pct*100:.1f}% > 25%", 0.85))

        if self.state.current_leverage > 3.0:
            results.append(VetoResult(VetoLevel.VETO, VetoReason.LEVERAGE_LIMIT,
                f"Leverage {self.state.current_leverage:.1f}x exceeds 3x limit", 0.9))

        # Layer 3: Correlation & regime
        if self.state.correlation_alert:
            results.append(VetoResult(VetoLevel.WARNING, VetoReason.CORRELATION_EXPOSURE,
                "Correlation exposure alert triggered", 0.7))

        if self.state.volatility_regime in ("high", "extreme"):
            results.append(VetoResult(VetoLevel.WARNING, VetoReason.VOLATILITY_SPIKE,
                f"Volatility regime: {self.state.volatility_regime}", 0.6))

        # Layer 4: News & macro
        if self.state.news_breaker_active:
            results.append(VetoResult(VetoLevel.VETO, VetoReason.NEWS_BREAKER,
                "News breaker circuit triggered — halting all trading", 0.95))

        if self.state.macro_contradiction:
            results.append(VetoResult(VetoLevel.VETO, VetoReason.MACRO_CONTRADICTION,
                "Macro environment contradicts active positions", 0.85))

        # Layer 5: Liquidity & system
        if self.state.liquidity_score < 0.3:
            results.append(VetoResult(VetoLevel.VETO, VetoReason.INSUFFICIENT_LIQUIDITY,
                f"Liquidity score {self.state.liquidity_score:.2f} below 0.3 threshold", 0.9))

        if not self.state.system_healthy:
            results.append(VetoResult(VetoLevel.HARD_STOP, VetoReason.SYSTEM_ERROR,
                "System health check failed — hard stop", 1.0))

        # Layer 6: Tail risk
        if self.state.tail_risk_level in ("hedge", "emergency"):
            results.append(VetoResult(VetoLevel.VETO, VetoReason.TAIL_RISK_EMERGENCY,
                f"Tail risk level: {self.state.tail_risk_level}", 0.9))

        if not results:
            return VetoResult(VetoLevel.PASS, risk_score=0.0, detail="all guards passed")

        # Pick worst result
        worst = max(results, key=lambda r: r.risk_score)

        # Log veto
        self._veto_log.append({
            "timestamp": __import__("time").time(),
            "level": worst.level.value,
            "reason": worst.reason.value if worst.reason else "none",
            "detail": worst.detail,
            "risk_score": worst.risk_score,
            "state": {
                "daily_pnl_pct": self.state.daily_pnl_pct,
                "weekly_pnl_pct": self.state.weekly_pnl_pct,
                "drawdown": self.state.current_drawdown,
                "leverage": self.state.current_leverage,
                "volatility_regime": self.state.volatility_regime,
            },
        })
        self.state.vetos_triggered.append(f"{worst.level.value}:{worst.reason.value}")
        if len(self.state.vetos_triggered) > 100:
            self.state.vetos_triggered = self.state.vetos_triggered[-50:]

        return worst

    def can_trade(self) -> bool:
        result = self.check()
        can = result.level not in (VetoLevel.VETO, VetoLevel.HARD_STOP)
        logger.info("Governance check: %s -> can_trade=%s (risk=%.2f)", result.level.value, can, result.risk_score)
        return can

    def get_veto_history(self, last_n: int = 10) -> list[dict[str, Any]]:
        return self._veto_log[-last_n:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": {
                "daily_pnl_pct": self.state.daily_pnl_pct,
                "weekly_pnl_pct": self.state.weekly_pnl_pct,
                "drawdown": self.state.current_drawdown,
                "leverage": self.state.current_leverage,
                "volatility_regime": self.state.volatility_regime,
                "tail_risk_level": self.state.tail_risk_level,
            },
            "can_trade": self.can_trade(),
            "vetos_triggered": self.state.vetos_triggered[-5:],
        }
