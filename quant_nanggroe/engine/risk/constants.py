"""Constitutional Risk Limits — Single Source of Truth.

All constitutional risk limits are defined HERE and ONLY HERE.
No other module may define these constants independently.

These values are HARDCODED, IMMUTABLE, and CANNOT be overridden
by any agent, config, or API. They represent the MOST CONSERVATIVE
values across all previous definitions to ensure maximum safety.

Previous divergences resolved:
- state.py said MAX_DRAWDOWN = 15%, manager.py said 10% → using 10% (most conservative)
- state.py said MAX_LEVERAGE = 3x, TypeScript said 5x → using 3x (most conservative)
- Kill switch daily thresholds differed between files → unified here
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTITUTIONAL RISK LIMITS — HARDCODED, IMMUTABLE, NO OVERRIDE
# These values are final and cannot be changed by any agent, config, or API.
# All values are fractions (0.005 = 0.5%, 0.01 = 1%, 0.10 = 10%).
# ═══════════════════════════════════════════════════════════════════════════════

# Per-trade risk limit
MAX_RISK_PER_TRADE: float = 0.005       # 0.5% max risk per trade

# Daily / weekly loss limits
MAX_DAILY_LOSS: float = 0.01            # 1% max daily loss
MAX_WEEKLY_LOSS: float = 0.03           # 3% max weekly loss

# Drawdown limit
MAX_DRAWDOWN: float = 0.10              # 10% max drawdown (most conservative)

# Leverage limit
MAX_LEVERAGE: float = 3.0               # 3x max leverage (most conservative)

# Risk:Reward minimum
MIN_RISK_REWARD: float = 2.0            # Minimum 1:2 R:R ratio

# Position limits
MAX_CORRELATED_POSITIONS: int = 3       # Max correlated positions
MAX_POSITION_SIZE_PCT: float = 0.10     # Max 10% of portfolio in single position
MAX_DAILY_TRADES: int = 5               # Max trades per day to prevent overtrading

# Kill switch thresholds
KILL_SWITCH_DAILY_PCT: float = 0.02     # 2% daily triggers kill switch
KILL_SWITCH_WEEKLY_PCT: float = 0.05    # 5% weekly triggers kill switch

# Correlation threshold
MAX_CORRELATION: float = 0.70           # Max pairwise correlation

# Confidence threshold for council debate
CONFIDENCE_THRESHOLD: float = 0.65      # Below this, trigger council debate

# ═══════════════════════════════════════════════════════════════════════════════
# ALIASES — Backward compatibility with different naming conventions
# ═══════════════════════════════════════════════════════════════════════════════

# Aliases used by state.py and risk/agent.py
MAX_RISK_PER_TRADE_PCT: float = MAX_RISK_PER_TRADE
MAX_DAILY_LOSS_PCT: float = MAX_DAILY_LOSS
MAX_WEEKLY_LOSS_PCT: float = MAX_WEEKLY_LOSS
MAX_DRAWDOWN_PCT: float = MAX_DRAWDOWN
MAX_TRADES_PER_DAY: int = MAX_DAILY_TRADES

# Kill switch PnL thresholds (negative values for PnL context)
KILL_SWITCH_DAILY_PNL: float = -KILL_SWITCH_DAILY_PCT   # -0.02 (i.e., -2%)
KILL_SWITCH_WEEKLY_PNL: float = -KILL_SWITCH_WEEKLY_PCT  # -0.05 (i.e., -5%)
