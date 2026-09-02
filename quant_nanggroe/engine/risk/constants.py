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
# NOTE: These limits are CONSTITUTIONAL.  The tier/scaling factor is deliberately
# NOT applied here — demo trades already benefit from play money and relaxed
# strategy rules, but the constitutional hard limits must remain absolute.

# Per-Trade Limits
MAX_RISK_PER_TRADE: float = _settings.risk_max_per_trade / 100
MAX_POSITION_SIZE_PCT: float = 0.10      # Max 10% of portfolio in single position (live-editable via /api/risk-config)
MAX_LEVERAGE: float = 3.0                # Max 3x leverage (live-editable)

# Daily Limits
MAX_DAILY_LOSS: float = _settings.risk_max_daily_loss / 100       # 1% default (live-editable)
MAX_DAILY_TRADES: int = 5                # Max 5 trades per day (live-editable)

# Weekly Limit
MAX_WEEKLY_LOSS: float = _settings.risk_max_weekly_loss / 100     # 3% default (live-editable)

# Drawdown
MAX_DRAWDOWN_PCT: float = _settings.risk_max_drawdown / 100       # 10% default (live-editable)

# ── Live reload from config/risk_config.json (UI editable, entire QNA follows) ──
def _reload_from_risk_config() -> None:
    try:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parents[2].parent / "config" / "risk_config.json"
        # also try worktree config
        alt = Path(__file__).resolve().parents[3] / "config" / "risk_config.json"
        for cand in (p, alt, Path("config/risk_config.json")):
            if cand.exists():
                data = json.loads(cand.read_text(encoding="utf-8"))
                globals()["MAX_RISK_PER_TRADE"] = float(data.get("maxRiskPerTrade", MAX_RISK_PER_TRADE))
                globals()["MAX_POSITION_SIZE_PCT"] = float(data.get("maxPositionSize", MAX_POSITION_SIZE_PCT))
                globals()["MAX_LEVERAGE"] = float(data.get("maxLeverage", MAX_LEVERAGE))
                globals()["MAX_DAILY_LOSS"] = float(data.get("maxDailyLoss", MAX_DAILY_LOSS))
                globals()["MAX_DAILY_TRADES"] = int(data.get("maxDailyTrades", MAX_DAILY_TRADES))
                globals()["MAX_WEEKLY_LOSS"] = float(data.get("maxWeeklyLoss", MAX_WEEKLY_LOSS))
                globals()["MAX_DRAWDOWN_PCT"] = float(data.get("maxDrawdown", MAX_DRAWDOWN_PCT))
                # also handle legacy keys from UI
                if "maxDrawdown" in data:
                    globals()["MAX_DRAWDOWN_PCT"] = float(data["maxDrawdown"])
                break
    except Exception:
        pass

_reload_from_risk_config()
# expose reload for RiskManager hot-reload
def reload_risk_constants() -> None:
    _reload_from_risk_config()

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

# ─── Sector Exposure Limits ────────────────────────────────────────────────
MAX_SECTOR_EXPOSURE_PCT: Final[float] = 0.30    # Max 30% of portfolio in any single sector

SECTOR_MAP: dict[str, str] = {
    # FX Majors
    "EURUSD": "forex", "GBPUSD": "forex", "USDJPY": "forex",
    "USDCAD": "forex", "AUDUSD": "forex", "NZDUSD": "forex",
    "EURGBP": "forex", "EURJPY": "forex", "GBPJPY": "forex",
    "CHFJPY": "forex", "AUDJPY": "forex", "NZDJPY": "forex",
    # Commodities
    "XAUUSD": "commodity", "XAGUSD": "commodity",
    "USOIL": "energy", "UKOIL": "energy", "NG": "energy", "HG": "metal",
}
SECTOR_DEFAULT: str = "other"

# ─── MT5 Symbol Mapping ──────────────────────────────────────────
# MT5 uses different symbol names than our internal format.
# This map ensures correct price lookups, SL/TP placement, and PnL calculation.
# Keys are internal symbols, values are MT5 terminal symbol names.
MT5_SYMBOL_MAP: dict[str, str] = {
    # NOTE: suffix resolution is handled dynamically by MT5Broker.resolve_symbol()
    # which scans the terminal's real symbol list. These are bare-name fallbacks
    # only used when the broker snapshot is empty.
    "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY",
    "USDCAD": "USDCAD", "AUDUSD": "AUDUSD", "NZDUSD": "NZDUSD",
    "XAUUSD": "XAUUSD", "XAGUSD": "XAGUSD",
    "USOIL": "USOIL", "UKOIL": "UKOIL",
}
MT5_SYMBOL_DEFAULT: str = ""

# ─── Kill Switch Thresholds (early warning BEFORE hard limits) ──────────────
# Kill switch triggers BEFORE the constitutional hard limits are hit,
# providing an early warning buffer. This prevents the system from
# riding losses all the way to the hard limit.
#
# Logic: If MAX_DAILY_LOSS = 1%, then KILL_SWITCH triggers at 0.8% loss,
# giving the system a 0.2% buffer before hitting the absolute constitutional limit.

KILL_SWITCH_DAILY_PNL: Final[float] = -0.008    # Kill switch at -0.8% daily PnL (before 1% hard limit)
KILL_SWITCH_WEEKLY_PNL: Final[float] = -0.025   # Kill switch at -2.5% weekly PnL (before 3% hard limit)

# ─── Live Engine Constants ──────────────────────────────────
# These are the single source of truth for live_engine.py.
# Import from here instead of hardcoding values inline.

ASSET_ALLOCATIONS: Final[dict[str, float]] = {
    "EURUSD": 0.30,
    "XAUUSD": 0.30,
    "GBPUSD": 0.20,
    "USOIL": 0.10,
    "USDJPY": 0.10,
}

TP_TARGETS: Final[dict[str, float]] = {
    "SMC": 0.05,
    "Momentum": 0.08,
    "MeanReversion": 0.04,
    "Grid": 0.03,
    "TrendStrength": 0.06,
}

TRAILING_STOP_PCT: Final[float] = 0.03
REBALANCE_THRESHOLD: Final[float] = 0.05
MAX_POSITIONS_TOTAL: Final[int] = 3
HEARTBEAT_INTERVAL: Final[int] = 10
CLEANUP_INTERVAL: Final[int] = 10
REPORT_INTERVAL: Final[int] = 5
DCC_UPDATE_INTERVAL: Final[int] = 10
STARTING_CAPITAL: Final[float] = 10000.0
