"""Constitutional Risk Limits for Quant Nanggroe AI.

These values are HARDCODED and CANNOT be overridden at runtime.
They represent the absolute maximum risk tolerances for the system.

All risk modules MUST import constants from this file to avoid circular imports.
These values are the single source of truth — they must match agents/state.py.
"""

# ─── Constitutional Risk Limits (IMMUTABLE) ────────────────────────────────
MAX_RISK_PER_TRADE: float = 0.005       # 0.5% max risk per trade
MAX_DAILY_LOSS: float = 0.01            # 1% max daily loss
MAX_WEEKLY_LOSS: float = 0.03           # 3% max weekly loss
MIN_RISK_REWARD: float = 2.0            # Minimum 1:2 R:R ratio
MAX_CORRELATED_POSITIONS: int = 3       # Max correlated positions
MAX_POSITION_SIZE_PCT: float = 0.10     # Max 10% of portfolio in single position
MAX_LEVERAGE: float = 3.0               # Max 3x leverage
MAX_DRAWDOWN_PCT: float = 0.15          # Max 15% drawdown before kill switch
MAX_DAILY_TRADES: int = 5               # Max 5 trades per day to prevent overtrading
CONFIDENCE_THRESHOLD: float = 0.65      # Below this, trigger council debate
KILL_SWITCH_DAILY_PNL: float = -0.02    # Kill switch at -2% daily PnL
KILL_SWITCH_WEEKLY_PNL: float = -0.05   # Kill switch at -5% weekly PnL
