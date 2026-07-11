"""Constitutional Risk Limits for Quant Nanggroe AI.

These values are ENVIRONMENT-DRIVEN via QNAI_* env vars, with default
fallbacks matching the original hardcoded values.  They represent the
absolute maximum risk tolerances for the system and CANNOT be overridden
at runtime by agents — only by .env / environment variable changes.

THIS FILE IS THE SINGLE SOURCE OF TRUTH for all constitutional risk constants.
All risk modules MUST import constants from this file.

If you need to reference a risk limit, import it from here:
    from quant_nanggroe.engine.risk.constants import MAX_DAILY_LOSS
"""

from typing import Final

# Settings-backed constitutional limits (env-configurable, agent-proof)
from quant_nanggroe.config.settings import get_settings

_settings = get_settings()

# ─── Constitutional Risk Limits (env-driven — agent-proof) ──────────────────

# Per-Trade Limits
MAX_RISK_PER_TRADE: float = _settings.risk_max_per_trade / 100  # 0.5% default
MAX_POSITION_SIZE_PCT: Final[float] = 0.10      # Max 10% of portfolio in single position
MAX_LEVERAGE: Final[float] = 3.0                # Max 3x leverage

# Daily Limits
MAX_DAILY_LOSS: float = _settings.risk_max_daily_loss / 100       # 1% default
MAX_DAILY_TRADES: Final[int] = 5                # Max 5 trades per day to prevent overtrading

# Weekly Limit
MAX_WEEKLY_LOSS: float = _settings.risk_max_weekly_loss / 100     # 3% default

# Drawdown
MAX_DRAWDOWN_PCT: float = _settings.risk_max_drawdown / 100       # 10% default

# Quality Gates
MIN_RISK_REWARD: Final[float] = 2.0             # Minimum 1:2 R:R ratio
CONFIDENCE_THRESHOLD: Final[float] = 0.65        # Below this, trigger council debate
MAX_CORRELATED_POSITIONS: Final[int] = 3         # Max correlated positions

# ─── Per-Asset Risk Budgets (P1-26)
MAX_ASSET_DAILY_LOSS_PCT: Final[float] = 0.01   # 1% max daily loss per asset
HARD_STOP_ATR_MULTIPLIER: Final[float] = 3.0    # Hard stop is 3x ATR from entry (wider than trailing 2.5x)

# ─── Concentration Limits (P1-32)
MAX_TOTAL_CONCENTRATION: Final[float] = 0.80    # Max 80% of portfolio in positions total

# ─── Cost-Aware Budget (P1-32)
TRADING_BUDGET_PCT: Final[float] = 0.001        # 0.1% of initial capital allocated for fees/slippage

# ─── Kill Switch Thresholds (early warning BEFORE hard limits) ──────────────
# Kill switch triggers BEFORE the constitutional hard limits are hit,
# providing an early warning buffer. This prevents the system from
# riding losses all the way to the hard limit.
#
# Logic: If MAX_DAILY_LOSS = 1%, then KILL_SWITCH triggers at 0.8% loss,
# giving the system a 0.2% buffer before hitting the absolute constitutional limit.

KILL_SWITCH_DAILY_PNL: Final[float] = -0.008    # Kill switch at -0.8% daily PnL (before 1% hard limit)
KILL_SWITCH_WEEKLY_PNL: Final[float] = -0.025   # Kill switch at -2.5% weekly PnL (before 3% hard limit)
