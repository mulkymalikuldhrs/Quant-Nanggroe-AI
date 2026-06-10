"""
Strategist Agent — Strategy Lab: generates entry/exit strategies.
================================================================
Combines analysis with market state to produce deterministic trade plans.
Uses PressureNormalizationEngine for multi-sensor fusion and
DecisionSynthesisEngine for machine-readable trade decisions.

Responsibilities:
  - Compile all sensor inputs via PressureNormalizationEngine
  - Run DecisionSynthesisEngine for deterministic trade decisions
  - Calculate entry/exit levels based on ATR multiples
  - Return strategy_signal, entry_price, stop_loss, take_profit, position_size
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.engine.decision import DecisionSynthesisEngine
from quant_nanggroe_ai.engine.math_lib import MathEngine
from quant_nanggroe_ai.engine.pressure import PressureInput, PressureNormalizationEngine
from quant_nanggroe_ai.types import (
    DecisionAction,
    MarketRegime,
    PressureState,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# ATR-based Entry/Exit Calculation Constants
# ══════════════════════════════════════════════════════════════════════

ATR_STOP_MULTIPLIER = 2.0       # Stop loss = 2× ATR from entry
ATR_TP1_MULTIPLIER = 2.0        # TP1 = 2× ATR (1:1 R:R minimum)
ATR_TP2_MULTIPLIER = 4.0        # TP2 = 4× ATR (1:2 R:R)
ATR_TP3_MULTIPLIER = 6.0        # TP3 = 6× ATR (1:3 R:R)
MIN_RISK_REWARD = 2.0           # Minimum acceptable R:R for trade
DEFAULT_ACCOUNT_BALANCE = 10000.0
DEFAULT_RISK_PCT = 0.005        # 0.5% risk per trade (constitutional max)


def _map_smc_signal(ta: dict[str, Any]) -> str:
    """Map technical analysis SMC flags to pressure input signal."""
    if ta.get("smc_bullish_bos"):
        return "bullish_bos"
    if ta.get("smc_bearish_bos"):
        return "bearish_bos"
    if ta.get("smc_bullish_choch"):
        return "bullish_choch"
    if ta.get("smc_bearish_choch"):
        return "bearish_choch"
    return "none"


def _calculate_position_size(
    account_balance: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float,
) -> float:
    """
    Calculate position size using fixed-fractional risk model.

    position_size = (account_balance × risk_pct) / |entry - stop_loss|

    Returns 0.0 if the calculation is not possible.
    """
    if entry_price <= 0 or stop_loss <= 0:
        return 0.0
    risk_distance = abs(entry_price - stop_loss)
    if risk_distance == 0:
        return 0.0
    risk_amount = account_balance * risk_pct
    size = risk_amount / risk_distance
    return max(0.0, round(size, 6))


def _calculate_rr_ratio(entry: float, stop_loss: float, take_profit: list[float]) -> float:
    """
    Calculate the risk:reward ratio.

    Uses the first TP level as the primary reward target.
    Returns 0.0 if inputs are invalid.
    """
    if entry <= 0 or stop_loss <= 0 or not take_profit:
        return 0.0
    risk = abs(entry - stop_loss)
    reward = abs(take_profit[0] - entry)
    if risk == 0:
        return 0.0
    return round(reward / risk, 2)


def _determine_strategy_name(
    signal: str,
    regime: MarketRegime,
    action: DecisionAction,
) -> str:
    """Generate a human-readable strategy name."""
    if signal == "HOLD" or action == DecisionAction.NO_TRADE:
        return "no_trade"

    regime_label = regime.value.lower() if regime else "unknown"
    action_label = "trend_follow" if "TRENDING" in action.value else "counter"

    return f"pressure_{signal.lower()}_{regime_label}_{action_label}"


def _compute_atr_entry_exit(
    signal: str,
    current_price: float,
    atr: float,
) -> dict[str, Any]:
    """
    Compute entry, stop loss, and take profit levels using ATR multiples.

    For BUY signals:
        entry  = current_price
        SL     = current_price - ATR × multiplier
        TP1    = current_price + ATR × 2
        TP2    = current_price + ATR × 4
        TP3    = current_price + ATR × 6

    For SELL signals (mirrored):
        entry  = current_price
        SL     = current_price + ATR × multiplier
        TP1-3  = current_price - ATR × {2, 4, 6}

    Returns dict with entry_price, stop_loss, take_profit, risk_reward_ratio.
    """
    if current_price <= 0 or atr <= 0:
        return {
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": [],
            "risk_reward_ratio": 0.0,
        }

    if signal == "BUY":
        entry_price = current_price
        stop_loss = round(current_price - ATR_STOP_MULTIPLIER * atr, 6)
        take_profit = [
            round(current_price + ATR_TP1_MULTIPLIER * atr, 6),
            round(current_price + ATR_TP2_MULTIPLIER * atr, 6),
            round(current_price + ATR_TP3_MULTIPLIER * atr, 6),
        ]
    elif signal == "SELL":
        entry_price = current_price
        stop_loss = round(current_price + ATR_STOP_MULTIPLIER * atr, 6)
        take_profit = [
            round(current_price - ATR_TP1_MULTIPLIER * atr, 6),
            round(current_price - ATR_TP2_MULTIPLIER * atr, 6),
            round(current_price - ATR_TP3_MULTIPLIER * atr, 6),
        ]
    else:
        return {
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": [],
            "risk_reward_ratio": 0.0,
        }

    rr = _calculate_rr_ratio(entry_price, stop_loss, take_profit)

    return {
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_reward_ratio": rr,
    }


async def strategist_node(state: AgentState) -> dict[str, Any]:
    """
    Strategy Lab Agent node.

    Uses PressureNormalizationEngine to compile all sensor inputs,
    DecisionSynthesisEngine for deterministic trade decisions, and
    ATR-based calculations for entry/exit levels and position sizing.
    """
    symbol = state.symbol or "SPY"
    ta = state.technical_analysis or {}
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Build pressure input from analysis results ──────────────────
    ema_trend = ta.get("ema_trend", "neutral")
    if ema_trend not in ("bullish", "bearish"):
        ema_trend = "neutral"

    smc_signal = _map_smc_signal(ta)
    displacement_strength = ta.get("displacement_strength", 0.0)
    liquidity_sweep = ta.get("liquidity_sweep", False)

    # News/sentiment contribution
    sentiment_score = state.sentiment_score or 0.0
    news_impact = min(1.0, abs(sentiment_score))
    news_uncertainty = 1.0 - abs(sentiment_score)

    # Flow direction from volume analysis
    flow_direction = "neutral"
    flow_imbalance = ta.get("flow_imbalance", 0.0)
    volume_ratio = ta.get("volume_ratio", 1.0)
    if volume_ratio > 1.5 and ema_trend == "bullish":
        flow_direction = "long"
        flow_imbalance = min(1.0, (volume_ratio - 1.0) / 2.0)
    elif volume_ratio > 1.5 and ema_trend == "bearish":
        flow_direction = "short"
        flow_imbalance = min(1.0, (volume_ratio - 1.0) / 2.0)

    pressure_input = PressureInput(
        trend_direction=ema_trend,
        trend_strength=ta.get("trend_strength", 0.0),
        smc_signal=smc_signal,
        displacement_strength=displacement_strength,
        liquidity_sweep=liquidity_sweep,
        news_impact=news_impact,
        news_uncertainty=news_uncertainty,
        flow_direction=flow_direction,
        flow_imbalance=flow_imbalance,
    )

    # ── 2. Compile pressure ────────────────────────────────────────────
    pressure_engine = PressureNormalizationEngine()
    try:
        pressure_result = pressure_engine.compile_pressure(pressure_input)
    except Exception as exc:
        logger.error("Pressure compilation failed: %s", exc)
        errors.append(f"Pressure compilation: {exc}")
        pressure_result = pressure_engine.compile_pressure(PressureInput())

    # ── 3. Run decision synthesis ──────────────────────────────────────
    decision_engine = DecisionSynthesisEngine()
    try:
        decision_result = decision_engine.evaluate(
            regime=state.regime,
            buy_pressure=pressure_result.buy_pressure,
            sell_pressure=pressure_result.sell_pressure,
            confidence=pressure_result.confidence,
            volatility=state.volatility,
            daily_pnl_pct=state.daily_pnl_pct,
        )
    except Exception as exc:
        logger.error("Decision synthesis failed: %s", exc)
        errors.append(f"Decision synthesis: {exc}")
        decision_result = decision_engine.evaluate(
            regime=MarketRegime.UNKNOWN,
            buy_pressure=0.0,
            sell_pressure=0.0,
            confidence=0.0,
        )

    # ── 4. Determine signal and entry/exit parameters ──────────────────
    signal = "HOLD"
    if decision_result.action in (DecisionAction.ALLOW_LONG, DecisionAction.ALLOW_LONG_TRENDING):
        signal = "BUY"
    elif decision_result.action in (DecisionAction.ALLOW_SHORT, DecisionAction.ALLOW_SHORT_TRENDING):
        signal = "SELL"

    # Extract ATR and current price for level calculations
    indicators = ta.get("indicators", {})
    atr_val = indicators.get("atr_14")
    atr_numeric = atr_val if isinstance(atr_val, (int, float)) else 0.0
    current_price = ta.get("current_price", 0.0)

    # Fallback: compute ATR from candles if not in indicators
    if atr_numeric <= 0 and state.candles:
        closes = [c.get("close", 0.0) for c in state.candles if c.get("close")]
        highs = [c.get("high", 0.0) for c in state.candles if c.get("high")]
        lows = [c.get("low", 0.0) for c in state.candles if c.get("low")]
        if len(closes) >= 15 and highs and lows:
            atr_list = MathEngine.atr(highs, lows, closes, 14)
            atr_numeric = atr_list[-1] if atr_list and atr_list[-1] is not None else 0.0

    # Compute entry/exit levels
    levels = _compute_atr_entry_exit(signal, current_price, atr_numeric)

    # ── 5. Position sizing ─────────────────────────────────────────────
    position_size = 0.0
    if signal != "HOLD" and levels["entry_price"] > 0 and levels["stop_loss"] > 0:
        position_size = _calculate_position_size(
            account_balance=DEFAULT_ACCOUNT_BALANCE,
            risk_pct=DEFAULT_RISK_PCT,
            entry_price=levels["entry_price"],
            stop_loss=levels["stop_loss"],
        )

    # ── 6. R:R validation — reject if below minimum ────────────────────
    rr_ratio = levels["risk_reward_ratio"]
    if signal != "HOLD" and rr_ratio < MIN_RISK_REWARD:
        logger.warning(
            "R:R ratio %.2f below minimum %.1f for %s — downgrading to HOLD",
            rr_ratio, MIN_RISK_REWARD, symbol,
        )
        signal = "HOLD"
        levels = {
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": [],
            "risk_reward_ratio": 0.0,
        }
        position_size = 0.0

    # ── 7. Strategy name ───────────────────────────────────────────────
    strategy_name = _determine_strategy_name(signal, state.regime, decision_result.action)

    # ── 8. Pressure state for downstream consumption ───────────────────
    pressure_state = PressureState(
        buy_pressure=pressure_result.buy_pressure,
        sell_pressure=pressure_result.sell_pressure,
        volatility_risk=state.volatility,
        liquidity_condition=state.liquidity,
        confidence_score=pressure_result.confidence,
    )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "strategy_signal": signal,
        "strategy_name": strategy_name,
        "entry_price": levels["entry_price"],
        "stop_loss": levels["stop_loss"],
        "take_profit": levels["take_profit"],
        "position_size": position_size,
        "risk_reward_ratio": rr_ratio,
        "buy_pressure": pressure_result.buy_pressure,
        "sell_pressure": pressure_result.sell_pressure,
        "confidence": pressure_result.confidence,
        "pressure": pressure_state,
        "decision_action": decision_result.action,
        "decision_reason": decision_result.reason,
        "risk_clearance": decision_result.risk_clearance,
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "strategist",
                "status": "completed",
                "signal": signal,
                "action": decision_result.action.value,
                "pressure_verdict": pressure_result.verdict,
                "rr_ratio": rr_ratio,
                "position_size": position_size,
                "strategy_name": strategy_name,
                "timestamp": now,
            }
        ],
    }
