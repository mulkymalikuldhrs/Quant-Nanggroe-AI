"""
Analyst Agent — Market Intelligence: Technical Analysis, SMC, Regime Detection.
================================================================================
Processes research data into actionable intelligence.  Runs the full
TechnicalAnalysisTool for MathEngine indicators + SMC detection, classifies
the market regime via MarketStateEngine, and computes volatility/liquidity.

Responsibilities:
  - Run full MathEngine technical analysis (RSI, MACD, Bollinger, ATR, ADX, Stochastic)
  - Detect Smart Money Concepts signals (BOS, CHoCH, liquidity sweeps)
  - Call MarketStateEngine for regime detection
  - Return technical_analysis dict, smc_signals list, regime, volatility, liquidity
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool
from quant_nanggroe_ai.engine.math_lib import MathEngine
from quant_nanggroe_ai.engine.market_state import MarketStateEngine
from quant_nanggroe_ai.types import (
    MarketRegime,
    VolatilityLevel,
    LiquidityLevel,
    MarketState,
)

logger = logging.getLogger(__name__)


def _extract_price_series(candles: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Extract OHLCV lists from candle dicts for MathEngine consumption."""
    closes = [c.get("close", 0.0) for c in candles if c.get("close")]
    highs = [c.get("high", 0.0) for c in candles if c.get("high")]
    lows = [c.get("low", 0.0) for c in candles if c.get("low")]
    volumes = [c.get("volume", 0.0) for c in candles if c.get("volume") is not None]
    return {"closes": closes, "highs": highs, "lows": lows, "volumes": volumes}


def _compute_price_changes(closes: list[float]) -> dict[str, float]:
    """Compute 1-day and 5-day percentage price changes."""
    result: dict[str, float] = {"price_change_1d": 0.0, "price_change_5d": 0.0}
    if len(closes) >= 2:
        prev = closes[-2] if closes[-2] != 0 else 1e-10
        result["price_change_1d"] = (closes[-1] - prev) / prev * 100
    if len(closes) >= 6:
        prev5 = closes[-6] if closes[-6] != 0 else 1e-10
        result["price_change_5d"] = (closes[-1] - prev5) / prev5 * 100
    return result


def _compute_volume_ratio(volumes: list[float], lookback: int = 20) -> float:
    """Compute current volume vs average volume ratio."""
    if not volumes or len(volumes) < lookback + 1:
        return 1.0
    avg = sum(volumes[-lookback - 1 : -1]) / lookback
    return volumes[-1] / avg if avg > 0 else 1.0


def _detect_liquidity_sweaks(
    closes: list[float],
    highs: list[float],
    lows: list[float],
) -> list[dict[str, Any]]:
    """
    Detect liquidity sweep signals.

    A sweep = wick beyond a prior swing point that quickly reverses,
    trapping breakout traders.
    """
    sweeps: list[dict[str, Any]] = []
    n = len(closes)
    if n < 10:
        return sweeps

    # Use last 3 bars to detect recent wick beyond prior range
    lookback = min(20, n - 3)
    recent_high = max(highs[-3:])
    recent_low = min(lows[-3:])
    prior_high = max(highs[-3 - lookback : -3]) if lookback > 0 else 0.0
    prior_low = min(lows[-3 - lookback : -3]) if lookback > 0 else 0.0
    current_close = closes[-1]

    # Buy-side liquidity sweep
    if recent_high > prior_high and current_close < prior_high:
        sweeps.append({
            "type": "LIQUIDITY_SWEEP",
            "direction": "bearish",
            "level": prior_high,
            "sweep_high": recent_high,
            "bar_index": n - 1,
            "description": f"Buy-side liquidity sweep above {prior_high:.4f}, rejected",
        })

    # Sell-side liquidity sweep
    if recent_low < prior_low and current_close > prior_low:
        sweeps.append({
            "type": "LIQUIDITY_SWEEP",
            "direction": "bullish",
            "level": prior_low,
            "sweep_low": recent_low,
            "bar_index": n - 1,
            "description": f"Sell-side liquidity sweep below {prior_low:.4f}, rejected",
        })

    return sweeps


def _derive_ema_trend(indicators: dict[str, Any]) -> str:
    """Derive the EMA trend direction from indicator values."""
    ema_9 = indicators.get("ema_9")
    ema_20 = indicators.get("ema_20")
    ema_50 = indicators.get("ema_50")

    if ema_9 is None or ema_20 is None:
        return "neutral"

    if ema_9 > ema_20:
        if ema_50 is not None and ema_20 > ema_50:
            return "bullish"
        return "bullish"
    elif ema_9 < ema_20:
        if ema_50 is not None and ema_20 < ema_50:
            return "bearish"
        return "bearish"
    return "neutral"


async def analyst_node(state: AgentState) -> dict[str, Any]:
    """
    Market Intelligence Agent node.

    Runs the full MathEngine indicator suite via TechnicalAnalysisTool,
    detects SMC signals, classifies market regime, and returns structured analysis.
    """
    symbol = state.symbol or "SPY"
    candles = state.candles or []
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Extract price series from candles ───────────────────────────
    series = _extract_price_series(candles)
    closes = series["closes"]
    highs = series["highs"]
    lows = series["lows"]
    volumes = series["volumes"]

    # ── 2. Run TechnicalAnalysisTool (MathEngine + SMC + S/R) ──────────
    technical_analysis: dict[str, Any] = {}
    smc_signals: list[dict[str, Any]] = []

    if len(closes) >= 50 and highs and lows:
        try:
            tech_tool = TechnicalAnalysisTool()
            # Use analyze_raw since we already have the data
            technical_analysis = tech_tool.analyze_raw(
                closes=closes, highs=highs, lows=lows, volumes=volumes,
                symbol=symbol, timeframe=state.timeframe,
            )

            # Extract SMC signals from the tool's result
            smc_data = technical_analysis.get("smc", {})
            if smc_data.get("signals"):
                smc_signals = smc_data["signals"]

            # Tag SMC-derived fields for strategist consumption
            latest_signal = smc_data.get("latest_signal")
            if latest_signal:
                sig_type = latest_signal.get("type", "")
                sig_dir = latest_signal.get("direction", "").lower()
                if sig_type == "BOS" and sig_dir in ("bull", "bullish"):
                    technical_analysis["smc_bullish_bos"] = True
                elif sig_type == "BOS" and sig_dir in ("bear", "bearish"):
                    technical_analysis["smc_bearish_bos"] = True
                elif sig_type == "CHoCH" and sig_dir in ("bull", "bullish"):
                    technical_analysis["smc_bullish_choch"] = True
                elif sig_type == "CHoCH" and sig_dir in ("bear", "bearish"):
                    technical_analysis["smc_bearish_choch"] = True

            # Set structure state from SMC
            structure_state = smc_data.get("structure_state", "NEUTRAL")
            technical_analysis["structure_state"] = structure_state

        except Exception as exc:
            logger.error("Technical analysis failed for %s: %s", symbol, exc)
            errors.append(f"Technical analysis: {exc}")
            # Fall back to direct MathEngine call
            try:
                technical_analysis = MathEngine.analyze_sequence(
                    closes, highs, lows, volumes,
                )
                technical_analysis["indicators"] = technical_analysis.get("indicators", {})
            except Exception as exc2:
                logger.error("MathEngine fallback also failed: %s", exc2)
                errors.append(f"MathEngine fallback: {exc2}")
    else:
        errors.append(f"Insufficient candle data ({len(closes)} bars, need 50+)")
        technical_analysis = {"error": "Insufficient data", "bars": len(closes)}

    # ── 3. Compute derived metrics ─────────────────────────────────────
    price_changes = _compute_price_changes(closes)
    volume_ratio = _compute_volume_ratio(volumes)

    # Enrich technical_analysis with derived metrics
    technical_analysis["price_change_1d"] = price_changes["price_change_1d"]
    technical_analysis["price_change_5d"] = price_changes["price_change_5d"]
    technical_analysis["volume_ratio"] = volume_ratio
    technical_analysis["current_price"] = closes[-1] if closes else 0.0

    # Extract key indicator values for regime detection
    indicators = technical_analysis.get("indicators", {})
    rsi_val = indicators.get("rsi_14")
    rsi_numeric = rsi_val if isinstance(rsi_val, (int, float)) else 50.0

    adx_dict = indicators.get("adx", {})
    adx_val = adx_dict.get("adx")
    adx_numeric = adx_val if isinstance(adx_val, (int, float)) else 20.0

    atr_pct_val = indicators.get("atr_pct")
    atr_pct_numeric = atr_pct_val if isinstance(atr_pct_val, (int, float)) else 1.0

    # EMA trend from the TechnicalAnalysisTool or derived
    trend_data = technical_analysis.get("trend", {})
    ema_trend = trend_data.get("ema_trend", _derive_ema_trend(indicators)).lower()
    technical_analysis["ema_trend"] = ema_trend

    # Trend strength
    trend_strength = trend_data.get("trend_strength", min(1.0, adx_numeric / 50.0))
    technical_analysis["trend_strength"] = trend_strength

    # ── 4. Detect additional liquidity sweeps ──────────────────────────
    if closes and highs and lows:
        try:
            sweep_signals = _detect_liquidity_sweaks(closes, highs, lows)
            if sweep_signals:
                smc_signals.extend(sweep_signals)
                technical_analysis["liquidity_sweep"] = True
                technical_analysis["liquidity_sweep_direction"] = sweep_signals[-1].get("direction", "neutral")
        except Exception as exc:
            logger.warning("Liquidity sweep detection failed: %s", exc)

    # Displacement strength
    displacement = 0.0
    if smc_signals and closes:
        best = max(smc_signals, key=lambda s: abs(closes[-1] - s.get("level", closes[-1])))
        displacement = min(1.0, abs(closes[-1] - best.get("level", closes[-1])) / (atr_pct_numeric * closes[-1] / 100 + 1e-10))
    technical_analysis["displacement_strength"] = displacement

    # ── 5. Market regime detection ─────────────────────────────────────
    market_state_engine = MarketStateEngine()
    try:
        regime_result = market_state_engine.detect_regime(
            symbol=symbol,
            price_change_5d=price_changes["price_change_5d"],
            price_change_1d=price_changes["price_change_1d"],
            adx=adx_numeric,
            rsi=rsi_numeric,
            atr_pct=atr_pct_numeric,
            volume_ratio=volume_ratio,
            ema_trend=ema_trend,
        )
        regime = regime_result.regime
        volatility = regime_result.volatility
        liquidity = regime_result.liquidity
        trade_allowed = regime_result.trade_allowed
    except Exception as exc:
        logger.error("Regime detection failed: %s", exc)
        errors.append(f"Regime detection: {exc}")
        regime = MarketRegime.UNKNOWN
        volatility = VolatilityLevel.NORMAL
        liquidity = LiquidityLevel.NORMAL
        trade_allowed = False

    market_state = MarketState(
        regime=regime,
        volatility=volatility,
        liquidity=liquidity,
    )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "technical_analysis": technical_analysis,
        "smc_signals": smc_signals,
        "regime": regime,
        "volatility": volatility,
        "liquidity": liquidity,
        "market_state": market_state,
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "analyst",
                "status": "completed",
                "action": "analyze",
                "symbol": symbol,
                "regime": regime.value,
                "volatility": volatility.value,
                "liquidity": liquidity.value,
                "trade_allowed": trade_allowed,
                "smc_count": len(smc_signals),
                "timestamp": now,
            }
        ],
    }
