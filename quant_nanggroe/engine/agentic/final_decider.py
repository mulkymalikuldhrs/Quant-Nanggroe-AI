"""Final Decider - One Final Veto."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
logger = logging.getLogger(__name__)

class Action(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

@dataclass
class RegimeState:
    regime: str = "unknown"
    confidence: float = 0.0
    volatility: str = "normal"

@dataclass
class StrategySignal:
    strategy_name: str = ""
    symbol: str = ""
    action: Action = Action.HOLD
    confidence: float = 0.0
    regime_compatibility: float = 0.5

@dataclass
class PortfolioState:
    total_exposure: float = 0.0
    max_exposure: float = 3.0
    available_balance: float = 1000.0
    position_count: int = 0
    max_positions: int = 5
    concentration_pct: float = 0.0
    max_concentration_pct: float = 0.25

@dataclass
class RiskState:
    kill_switch_active: bool = False
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    max_daily_loss_pct: float = 0.05
    max_weekly_loss_pct: float = 0.10
    current_drawdown: float = 0.0
    max_drawdown: float = 0.15

@dataclass
class FinalDecision:
    action: Action = Action.HOLD
    strategy_name: str = ""
    confidence: float = 0.0
    kelly_fraction: float = 0.0
    position_size_pct: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    reason: str = ""
    vetoed_by: list[str] = field(default_factory=list)
    timestamp: str = ""
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action.value, "strategy": self.strategy_name, "confidence": round(self.confidence, 4), "kelly_fraction": round(self.kelly_fraction, 4), "position_size_pct": round(self.position_size_pct, 4), "sl": round(self.sl, 2), "tp": round(self.tp, 2), "reason": self.reason, "vetoed_by": self.vetoed_by, "timestamp": self.timestamp}

_REGIME_VETO_MAP = {"trending_up": 1.0, "trending_down": 0.4, "bull_trend": 1.0, "bear_trend": 0.4, "ranging": 0.6, "high_volatility": 0.3, "low_volatility": 1.0, "sideways": 0.5, "crisis": 0.05, "recovery": 0.7, "unknown": 0.3}

class FinalDecider:
    def __init__(self, min_confidence_threshold: float = 0.60, min_regime_compatibility: float = 0.35, risk_per_trade: float = 0.01, min_rr_ratio: float = 2.5):
        self.min_confidence = min_confidence_threshold
        self.min_regime_compat = min_regime_compatibility
        self.risk_per_trade = risk_per_trade
        self.min_rr = min_rr_ratio
        self._last_decision: Optional[FinalDecision] = None

    def decide(self, signals: list[StrategySignal], regime: RegimeState, portfolio: PortfolioState, risk: RiskState, atr: Optional[float] = None, current_price: float = 0.0) -> FinalDecision:
        vetoed_by: list[str] = []
        if risk.kill_switch_active:
            return FinalDecision(action=Action.HOLD, reason="Kill switch active", vetoed_by=["kill_switch"])
        if risk.current_drawdown >= risk.max_drawdown:
            return FinalDecision(action=Action.HOLD, reason=f"Max drawdown {risk.max_drawdown:.0%}", vetoed_by=["drawdown"])
        if risk.daily_loss_pct <= -risk.max_daily_loss_pct:
            return FinalDecision(action=Action.HOLD, reason=f"Daily loss {risk.max_daily_loss_pct:.0%}", vetoed_by=["daily_loss"])
        regime_mult = _REGIME_VETO_MAP.get(regime.regime.lower(), 0.3)
        if regime_mult < self.min_regime_compat:
            return FinalDecision(action=Action.HOLD, reason=f"Regime {regime.regime} blocked", vetoed_by=["regime"])
        if not signals:
            return FinalDecision(action=Action.HOLD, reason="No signals", vetoed_by=["no_signals"])
        best = max(signals, key=lambda s: s.confidence * regime_mult)
        if best.action == Action.HOLD or best.confidence < self.min_confidence:
            return FinalDecision(action=Action.HOLD, reason=f"Best: {best.strategy_name} @ {best.confidence:.1%}", vetoed_by=["confidence"])
        if portfolio.total_exposure >= portfolio.max_exposure:
            return FinalDecision(action=Action.HOLD, reason="Max exposure", vetoed_by=["exposure"])
        if portfolio.position_count >= portfolio.max_positions:
            return FinalDecision(action=Action.HOLD, reason="Max positions", vetoed_by=["positions"])
        try:
            from quant_nanggroe.engine.kelly.base import KellyParameters, KellyMethod, compute_kelly
            kp = KellyParameters(win_rate=best.confidence**1.5, avg_win=0.02, avg_loss=0.01, fraction=0.25, max_drawdown=risk.max_drawdown, current_drawdown=risk.current_drawdown)
            kf = compute_kelly(kp, method=KellyMethod.FRACTIONAL).f_star * regime_mult
            kf = min(kf, 0.25)
        except Exception:
            kf = 0.02 * regime_mult
        pct = min(kf, portfolio.max_exposure - portfolio.total_exposure)
        slp, tpp = 0.0, 0.0
        if atr and atr > 0 and current_price > 0:
            vm = 1.5 if regime.volatility == "high" else (0.8 if regime.volatility == "low" else 1.0)
            if best.action in (Action.BUY, Action.STRONG_BUY):
                slp, tpp = current_price - atr*1.5*vm, current_price + atr*3.0*vm
            elif best.action in (Action.SELL, Action.STRONG_SELL):
                slp, tpp = current_price + atr*1.5*vm, current_price - atr*3.0*vm
            if slp > 0 and tpp > 0:
                rr = abs(tpp - current_price) / abs(current_price - slp)
                if rr < self.min_rr:
                    return FinalDecision(action=Action.HOLD, reason=f"R:R {rr:.1f}<{self.min_rr:.1f}", vetoed_by=["rr"])
        d = FinalDecision(action=best.action, strategy_name=best.strategy_name, confidence=best.confidence, kelly_fraction=round(kf,4), position_size_pct=round(pct,4), sl=round(slp,2), tp=round(tpp,2), reason=f"{best.strategy_name} @ {best.confidence:.1%} Kelly={kf:.1%}", vetoed_by=vetoed_by or ["none"])
        self._last_decision = d
        return d

__all__ = ["Action", "RegimeState", "StrategySignal", "PortfolioState", "RiskState", "FinalDecision", "FinalDecider"]
