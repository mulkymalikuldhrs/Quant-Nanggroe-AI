"""
Risk Agent Tools for Quant Nanggroe AI Trading Framework.

Provides LangChain tool implementations for the Risk agent including
VaR/CVaR computation, drawdown checking, Kelly sizing, and kill switch.
These tools enforce HARDCODED constitutional risk limits.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from typing import Dict, List, Optional

from langchain_core.tools import tool

from quant_nanggroe.agents.state import (
    MAX_CORRELATED_POSITIONS,
    MAX_DAILY_LOSS,
    MAX_DRAWDOWN_PCT,
    MAX_LEVERAGE,
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE,
    MAX_TRADES_PER_DAY,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
)


logger = logging.getLogger(__name__)


# Correlation groups for checking correlated positions
CORRELATION_GROUPS: List[set] = [
    {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"},
    {"USDJPY", "USDCHF", "USDCAD"},
    {"XAUUSD", "XAGUSD"},
    {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"},
    {"SPY", "IVV", "VOO"},
    {"QQQ", "ONEQ", "TQQQ"},
]


def _is_correlated(symbol_a: str, symbol_b: str) -> bool:
    """Check if two symbols are in the same correlation group."""
    a_upper = symbol_a.upper()
    b_upper = symbol_b.upper()
    for group in CORRELATION_GROUPS:
        if a_upper in group and b_upper in group:
            return True
    return False


@tool
def compute_var(
    portfolio_value: float,
    confidence_level: float = 0.95,
    holding_period_days: int = 1,
    daily_volatility: float = 0.02,
) -> str:
    """
    Compute Value at Risk (VaR) using parametric method.

    Args:
        portfolio_value: Total portfolio value in USD
        confidence_level: Confidence level (0.95 or 0.99)
        holding_period_days: Holding period in days
        daily_volatility: Daily volatility estimate

    Returns:
        JSON string with VaR calculation
    """
    # Z-scores for common confidence levels
    z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
    z = z_scores.get(confidence_level, 1.645)

    # Parametric VaR: VaR = Z * sigma * sqrt(T) * Portfolio
    var = z * daily_volatility * math.sqrt(holding_period_days) * portfolio_value

    result = {
        "portfolio_value": portfolio_value,
        "confidence_level": confidence_level,
        "holding_period_days": holding_period_days,
        "daily_volatility": daily_volatility,
        "z_score": z,
        "var_amount": round(var, 2),
        "var_pct": round(var / portfolio_value * 100, 4) if portfolio_value > 0 else 0,
        "method": "parametric",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def compute_cvar(
    portfolio_value: float,
    confidence_level: float = 0.95,
    daily_volatility: float = 0.02,
) -> str:
    """
    Compute Conditional Value at Risk (CVaR / Expected Shortfall).

    Args:
        portfolio_value: Total portfolio value in USD
        confidence_level: Confidence level (0.95 or 0.99)
        daily_volatility: Daily volatility estimate

    Returns:
        JSON string with CVaR calculation
    """
    z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
    z = z_scores.get(confidence_level, 1.645)

    # CVaR = VaR + (sigma * exp(-z^2/2)) / ((1 - alpha) * sqrt(2*pi))
    var = z * daily_volatility * portfolio_value
    pdf_z = math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
    cvar = var + (daily_volatility * portfolio_value * pdf_z) / (1 - confidence_level)

    result = {
        "portfolio_value": portfolio_value,
        "confidence_level": confidence_level,
        "daily_volatility": daily_volatility,
        "var_amount": round(var, 2),
        "cvar_amount": round(cvar, 2),
        "cvar_pct": round(cvar / portfolio_value * 100, 4) if portfolio_value > 0 else 0,
        "interpretation": f"Expected loss beyond VaR at {confidence_level*100}% confidence",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def check_drawdown(
    portfolio_value: float,
    peak_value: float,
    current_drawdown_pct: float = 0.0,
) -> str:
    """
    Check current drawdown against constitutional limits.

    Args:
        portfolio_value: Current portfolio value
        peak_value: Historical peak portfolio value
        current_drawdown_pct: Current drawdown percentage (if pre-calculated)

    Returns:
        JSON string with drawdown assessment
    """
    if current_drawdown_pct > 0:
        drawdown_pct = current_drawdown_pct
    elif peak_value > 0:
        drawdown_pct = (peak_value - portfolio_value) / peak_value * 100
    else:
        drawdown_pct = 0.0

    passed = drawdown_pct < (MAX_DRAWDOWN_PCT * 100)

    result = {
        "current_value": portfolio_value,
        "peak_value": peak_value,
        "drawdown_pct": round(drawdown_pct, 4),
        "max_allowed_pct": MAX_DRAWDOWN_PCT * 100,
        "passed": passed,
        "kill_switch_trigger": drawdown_pct >= MAX_DRAWDOWN_PCT * 100,
        "constitutional_limit": "HARDCODED - NO OVERRIDE",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def kelly_sizing(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    account_balance: float,
) -> str:
    """
    Calculate position size using Kelly Criterion, capped at constitutional limits.

    The Kelly fraction is capped at the constitutional maximum position size.

    Args:
        win_rate: Historical win rate (0.0 - 1.0)
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount
        account_balance: Current account balance

    Returns:
        JSON string with Kelly sizing recommendation
    """
    # Kelly formula: f = (p * b - q) / b
    # where p = win_rate, q = 1 - win_rate, b = avg_win / avg_loss
    if avg_loss <= 0:
        kelly_fraction = 0.0
    else:
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly_fraction = (win_rate * b - q) / b

    # Apply half-Kelly for safety
    half_kelly = max(0, kelly_fraction / 2)

    # Cap at constitutional limit
    capped_fraction = min(half_kelly, MAX_POSITION_SIZE_PCT)

    position_size = account_balance * capped_fraction

    result = {
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "raw_kelly_fraction": round(kelly_fraction, 4),
        "half_kelly_fraction": round(half_kelly, 4),
        "capped_fraction": round(capped_fraction, 4),
        "position_size_usd": round(position_size, 2),
        "position_size_pct": round(capped_fraction * 100, 2),
        "max_position_constitutional": f"{MAX_POSITION_SIZE_PCT * 100}%",
        "capped": half_kelly > MAX_POSITION_SIZE_PCT,
        "note": "Half-Kelly applied for safety. Capped at constitutional maximum.",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def kill_switch(
    action: str,
    daily_pnl_pct: float = 0.0,
    weekly_pnl_pct: float = 0.0,
    reason: str = "MANUAL",
) -> str:
    """
    Manage the emergency kill switch.

    Args:
        action: Action to perform (check, activate, reset)
        daily_pnl_pct: Current daily PnL percentage
        weekly_pnl_pct: Current weekly PnL percentage
        reason: Reason for activation

    Returns:
        JSON string with kill switch status
    """
    should_activate = False
    activation_reason = reason

    # Auto-trigger checks
    if abs(min(0, daily_pnl_pct / 100)) >= MAX_DAILY_LOSS:
        should_activate = True
        activation_reason = "AUTO_DAILY_LIMIT"
    elif abs(min(0, weekly_pnl_pct / 100)) >= MAX_WEEKLY_LOSS:
        should_activate = True
        activation_reason = "AUTO_WEEKLY_LIMIT"

    if action == "activate" or should_activate:
        result = {
            "status": "ACTIVATED",
            "reason": activation_reason,
            "message": "ALL TRADING HALTED. Manual reset required after review.",
            "daily_pnl_pct": daily_pnl_pct,
            "weekly_pnl_pct": weekly_pnl_pct,
            "constitutional_daily_limit": f"{MAX_DAILY_LOSS * 100}%",
            "constitutional_weekly_limit": f"{MAX_WEEKLY_LOSS * 100}%",
            "override_possible": False,
            "timestamp": datetime.now().isoformat(),
        }
    elif action == "reset":
        result = {
            "status": "RESET_REQUIRED",
            "message": "Kill switch requires explicit confirmation: CONFIRM_RESET_AFTER_REVIEW",
            "override_possible": False,
        }
    else:  # check
        result = {
            "status": "OK" if not should_activate else "SHOULD_ACTIVATE",
            "daily_pnl_pct": daily_pnl_pct,
            "weekly_pnl_pct": weekly_pnl_pct,
            "auto_trigger_threshold_daily": f"-{MAX_DAILY_LOSS * 100}%",
            "auto_trigger_threshold_weekly": f"-{MAX_WEEKLY_LOSS * 100}%",
            "should_activate": should_activate,
        }

    return json.dumps(result, indent=2)


RISK_TOOLS = [compute_var, compute_cvar, check_drawdown, kelly_sizing, kill_switch]
