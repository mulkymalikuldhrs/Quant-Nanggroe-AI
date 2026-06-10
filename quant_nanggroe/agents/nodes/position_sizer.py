"""
ATR-Based Position Sizer for Quant Nanggroe AI Trading Framework v2.

Implements the fixed-fractional risk model with ATR-based TP1/TP2/TP3
take-profit geometry. This module is a graph node that computes precise
position sizes after risk assessment has approved the trade.

Position sizing model:
  1. Determine risk amount = portfolio_value * fractional_risk_pct
  2. Compute ATR from market data (or use provided ATR)
  3. Stop-loss distance = ATR_multiplier_sl * ATR  (default 1.5x)
  4. Position size (units) = risk_amount / stop_loss_distance
  5. TP1 = entry + 1.0 * ATR  (conservative, ~0.67 R:R)
  6. TP2 = entry + 2.0 * ATR  (moderate, ~1.33 R:R)
  7. TP3 = entry + 3.0 * ATR  (aggressive, ~2.0 R:R)

All sizes are capped at constitutional MAX_POSITION_SIZE_PCT.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_nanggroe.agents.state import (
    AgentState,
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE,
    PositionSizingResult,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration defaults
# =============================================================================

# Fixed-fractional risk per trade (fraction of portfolio we are willing to lose)
DEFAULT_FRACTIONAL_RISK_PCT: float = 0.005  # 0.5% = same as MAX_RISK_PER_TRADE

# ATR multiplier for stop-loss distance
DEFAULT_ATR_SL_MULTIPLIER: float = 1.5

# ATR multipliers for take-profit levels
DEFAULT_ATR_TP1_MULTIPLIER: float = 1.0
DEFAULT_ATR_TP2_MULTIPLIER: float = 2.0
DEFAULT_ATR_TP3_MULTIPLIER: float = 3.0

# Minimum ATR value to prevent division by zero or micro-positions
MIN_ATR_VALUE: float = 0.0001


# =============================================================================
# ATR estimation from market data
# =============================================================================

def estimate_atr_from_market_data(
    market_data: Dict[str, Any],
    symbol: str,
    period: int = 14,
) -> float:
    """
    Estimate the Average True Range (ATR) for a symbol from market data.

    If a pre-computed ATR is available in the market data, use it directly.
    Otherwise, compute a simplified estimate from high/low/close.

    This is a simplified ATR calculation suitable for the graph node.
    A production system would use a proper rolling ATR with historical data.

    Args:
        market_data: Market data dictionary keyed by symbol
        symbol: Symbol to compute ATR for
        period: ATR lookback period (default 14)

    Returns:
        Estimated ATR value
    """
    data = market_data.get(symbol, {})

    if not isinstance(data, dict):
        logger.warning(f"No market data dict for {symbol}, using default ATR=1.0")
        return 1.0

    # Check for pre-computed ATR
    if "atr" in data and data["atr"] is not None:
        try:
            atr = float(data["atr"])
            if atr > 0:
                return atr
        except (TypeError, ValueError):
            pass

    # Compute simplified ATR from current bar
    high = data.get("high", 0.0)
    low = data.get("low", 0.0)
    close = data.get("close", data.get("price", 0.0))

    try:
        high = float(high)
        low = float(low)
        close = float(close)
    except (TypeError, ValueError):
        return 1.0

    # True Range approximation from single bar:
    # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
    # With only one bar, we use high - low as the primary estimate
    if high > 0 and low > 0:
        tr = high - low
    elif close > 0:
        # Fallback: estimate ATR as ~2% of price (typical daily range)
        tr = close * 0.02
    else:
        return 1.0

    # Ensure minimum ATR
    atr = max(tr, MIN_ATR_VALUE)
    return atr


# =============================================================================
# Core position sizing computation
# =============================================================================

def compute_position_size(
    symbol: str,
    portfolio_value: float,
    entry_price: float,
    atr: float,
    direction: str = "LONG",
    fractional_risk_pct: float = DEFAULT_FRACTIONAL_RISK_PCT,
    atr_sl_multiplier: float = DEFAULT_ATR_SL_MULTIPLIER,
    atr_tp1_multiplier: float = DEFAULT_ATR_TP1_MULTIPLIER,
    atr_tp2_multiplier: float = DEFAULT_ATR_TP2_MULTIPLIER,
    atr_tp3_multiplier: float = DEFAULT_ATR_TP3_MULTIPLIER,
) -> PositionSizingResult:
    """
    Compute position size using the fixed-fractional + ATR model.

    The model risks a fixed fraction of the portfolio per trade and
    calculates the stop-loss distance and take-profit levels based
    on ATR multiples.

    Args:
        symbol: Trading symbol
        portfolio_value: Total portfolio value in USD
        entry_price: Proposed entry price
        atr: Current ATR value for the symbol
        direction: Trade direction (LONG or SHORT)
        fractional_risk_pct: Fraction of portfolio to risk (e.g., 0.005 = 0.5%)
        atr_sl_multiplier: ATR multiplier for stop-loss distance
        atr_tp1_multiplier: ATR multiplier for TP1
        atr_tp2_multiplier: ATR multiplier for TP2
        atr_tp3_multiplier: ATR multiplier for TP3

    Returns:
        PositionSizingResult with full sizing breakdown
    """
    # Guard against invalid inputs
    if portfolio_value <= 0 or entry_price <= 0 or atr <= 0:
        logger.warning(
            f"Invalid inputs for position sizing: "
            f"portfolio={portfolio_value}, entry={entry_price}, atr={atr}"
        )
        return PositionSizingResult(
            symbol=symbol,
            model="fixed_fractional_atr",
            fractional_risk_pct=fractional_risk_pct,
            atr_value=atr,
        )

    # 1. Risk amount
    risk_amount = portfolio_value * fractional_risk_pct

    # 2. Stop-loss distance in price units
    sl_distance = atr * atr_sl_multiplier

    # 3. Risk per unit (what we lose per unit if stopped out)
    risk_per_unit = sl_distance

    # 4. Position size in units
    if risk_per_unit > 0:
        position_size_units = risk_amount / risk_per_unit
    else:
        position_size_units = 0.0

    # 5. Position size in USD
    position_size_usd = position_size_units * entry_price

    # 6. Position size as % of portfolio
    if portfolio_value > 0:
        position_size_pct = (position_size_usd / portfolio_value) * 100
    else:
        position_size_pct = 0.0

    # 7. Cap at constitutional maximum
    max_position_pct = MAX_POSITION_SIZE_PCT * 100  # Convert to percentage
    if position_size_pct > max_position_pct:
        logger.info(
            f"Position size {position_size_pct:.2f}% exceeds constitutional "
            f"max {max_position_pct:.0f}%. Capping."
        )
        position_size_pct = max_position_pct
        position_size_usd = portfolio_value * (max_position_pct / 100)
        position_size_units = position_size_usd / entry_price if entry_price > 0 else 0.0

    # 8. Calculate stop-loss price
    is_long = direction.upper() in ("LONG", "BUY")
    if is_long:
        stop_loss = entry_price - sl_distance
        tp1 = entry_price + atr * atr_tp1_multiplier
        tp2 = entry_price + atr * atr_tp2_multiplier
        tp3 = entry_price + atr * atr_tp3_multiplier
    else:
        stop_loss = entry_price + sl_distance
        tp1 = entry_price - atr * atr_tp1_multiplier
        tp2 = entry_price - atr * atr_tp2_multiplier
        tp3 = entry_price - atr * atr_tp3_multiplier

    # 9. Calculate Risk:Reward ratios at each TP
    actual_sl_distance = abs(entry_price - stop_loss)
    if actual_sl_distance > 0:
        tp1_rr = abs(tp1 - entry_price) / actual_sl_distance
        tp2_rr = abs(tp2 - entry_price) / actual_sl_distance
        tp3_rr = abs(tp3 - entry_price) / actual_sl_distance
    else:
        tp1_rr = tp2_rr = tp3_rr = 0.0

    result = PositionSizingResult(
        symbol=symbol,
        position_size_units=round(position_size_units, 6),
        position_size_usd=round(position_size_usd, 2),
        position_size_pct=round(position_size_pct, 2),
        risk_per_unit=round(risk_per_unit, 6),
        atr_value=round(atr, 6),
        stop_loss=round(stop_loss, 6),
        tp1=round(tp1, 6),
        tp2=round(tp2, 6),
        tp3=round(tp3, 6),
        tp1_rr=round(tp1_rr, 2),
        tp2_rr=round(tp2_rr, 2),
        tp3_rr=round(tp3_rr, 2),
        fractional_risk_pct=fractional_risk_pct,
        model="fixed_fractional_atr",
    )

    logger.info(
        f"Position sizing for {symbol}: "
        f"size={position_size_units:.4f} units (${position_size_usd:,.2f}), "
        f"SL={stop_loss:.4f}, TP1={tp1:.4f}(RR={tp1_rr:.1f}), "
        f"TP2={tp2:.4f}(RR={tp2_rr:.1f}), TP3={tp3:.4f}(RR={tp3_rr:.1f})"
    )

    return result


# =============================================================================
# LangGraph node function
# =============================================================================

class PositionSizer:
    """
    Position sizing node for the v2 LangGraph trading graph.

    Reads signals from state, computes ATR-based position sizes with
    TP1/TP2/TP3 geometry for each actionable signal, and writes the
    results back to state.
    """

    def __init__(
        self,
        fractional_risk_pct: float = DEFAULT_FRACTIONAL_RISK_PCT,
        atr_sl_multiplier: float = DEFAULT_ATR_SL_MULTIPLIER,
        atr_tp1_multiplier: float = DEFAULT_ATR_TP1_MULTIPLIER,
        atr_tp2_multiplier: float = DEFAULT_ATR_TP2_MULTIPLIER,
        atr_tp3_multiplier: float = DEFAULT_ATR_TP3_MULTIPLIER,
    ) -> None:
        self._fractional_risk_pct = fractional_risk_pct
        self._atr_sl_multiplier = atr_sl_multiplier
        self._atr_tp1_multiplier = atr_tp1_multiplier
        self._atr_tp2_multiplier = atr_tp2_multiplier
        self._atr_tp3_multiplier = atr_tp3_multiplier

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute position sizing for all actionable signals.

        Args:
            state: Current agent state

        Returns:
            State updates with position_sizing_result
        """
        logger.info("=== Position Sizing Phase (Fixed-Fractional ATR) ===")

        signals = state.get("signals", [])
        market_data = state.get("market_data", {})
        portfolio_state = state.get("portfolio_state", {})
        portfolio_value = portfolio_state.get("total_value", 100000.0) if isinstance(portfolio_state, dict) else 100000.0

        sizing_results: Dict[str, Any] = {}
        sized_signals: List[Dict[str, Any]] = []

        for signal in signals:
            if not isinstance(signal, dict):
                continue

            symbol = signal.get("symbol", "")
            action = signal.get("action", "HOLD")

            # Only size actionable signals
            if action not in ("BUY", "SELL"):
                sized_signals.append(signal)
                continue

            # Get entry price
            entry_price = signal.get("entry_price", 0.0)
            if not entry_price:
                # Try to get from market data
                md = market_data.get(symbol, {})
                if isinstance(md, dict):
                    entry_price = md.get("price", md.get("close", 0.0))
                if not entry_price:
                    logger.warning(f"No entry price for {symbol}, skipping position sizing")
                    sized_signals.append(signal)
                    continue

            # Estimate ATR
            atr = estimate_atr_from_market_data(market_data, symbol)

            # Determine direction
            direction = "LONG" if action == "BUY" else "SHORT"

            # Compute position size
            sizing = compute_position_size(
                symbol=symbol,
                portfolio_value=portfolio_value,
                entry_price=entry_price,
                atr=atr,
                direction=direction,
                fractional_risk_pct=self._fractional_risk_pct,
                atr_sl_multiplier=self._atr_sl_multiplier,
                atr_tp1_multiplier=self._atr_tp1_multiplier,
                atr_tp2_multiplier=self._atr_tp2_multiplier,
                atr_tp3_multiplier=self._atr_tp3_multiplier,
            )

            sizing_results[symbol] = sizing.model_dump()

            # Enrich the signal with position sizing data
            enriched_signal = {
                **signal,
                "stop_loss": sizing.stop_loss,
                "take_profit": sizing.tp2,  # Default TP at TP2
                "position_size_pct": sizing.position_size_pct,
                "quantity": sizing.position_size_units,
                "tp1": sizing.tp1,
                "tp2": sizing.tp2,
                "tp3": sizing.tp3,
                "tp1_rr": sizing.tp1_rr,
                "tp2_rr": sizing.tp2_rr,
                "tp3_rr": sizing.tp3_rr,
                "atr_value": sizing.atr_value,
                "sizing_model": sizing.model,
                "risk_reward_ratio": sizing.tp2_rr,  # Use TP2 as primary R:R
            }
            sized_signals.append(enriched_signal)

        return {
            "position_sizing_result": sizing_results,
            "signals": sized_signals,
            "sender": "position_sizer",
        }


def compute_atr_position_sizing(state: AgentState) -> Dict[str, Any]:
    """
    Functional interface for the position sizing node.

    Args:
        state: Current agent state

    Returns:
        State updates with position sizing results
    """
    sizer = PositionSizer()
    return sizer(state)
