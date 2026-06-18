"""Financial intelligence package for AI-MultiColony.

Provides constitutional risk management, emergency kill switches,
market regime detection, buy/sell pressure analysis, and
automatic strategy switching – all designed for production-grade
trading safety.

Modules
-------
risk_guard    – Constitutional risk guard with hardcoded limits
kill_switch   – Emergency kill switch with auto-activation
market_state  – Market regime detection (trending, ranging, volatile, crisis)
pressure      – Market buy/sell pressure engine
autoswitch    – Auto strategy switching based on market conditions
"""

from .risk_guard import (
    ConstitutionalRiskGuard,
    RiskCheckResult,
    RiskLevel,
    TradeRequest,
    TradeAction,
    PortfolioSnapshot,
    MAX_RISK_PER_TRADE_PCT,
    MAX_DAILY_LOSS_PCT,
    MAX_WEEKLY_LOSS_PCT,
    MAX_POSITION_SIZE_PCT,
    MANDATORY_STOP_LOSS_PCT,
)
from .kill_switch import (
    KillSwitch,
    KillSwitchLevel,
    KillSwitchTrigger,
    KillSwitchStatus,
    KillSwitchEvent,
    KillSwitchConfig,
)
from .market_state import (
    MarketRegimeDetector,
    MarketRegime,
    RegimeResult,
    RegimeConfidence,
    RegimeConfig,
)
from .pressure import (
    PressureEngine,
    PressureResult,
    PressureDirection,
    PressureStrength,
    PressureConfig,
    OHLCVBar,
)
from .autoswitch import (
    AutoSwitcher,
    StrategyType,
    StrategyProfile,
    StrategySwitch,
    SwitchReason,
    AutoSwitchConfig,
    REGIME_STRATEGY_MAP,
    STRATEGY_PROFILES,
)

__all__ = [
    # Risk Guard
    "ConstitutionalRiskGuard",
    "RiskCheckResult",
    "RiskLevel",
    "TradeRequest",
    "TradeAction",
    "PortfolioSnapshot",
    "MAX_RISK_PER_TRADE_PCT",
    "MAX_DAILY_LOSS_PCT",
    "MAX_WEEKLY_LOSS_PCT",
    "MAX_POSITION_SIZE_PCT",
    "MANDATORY_STOP_LOSS_PCT",
    # Kill Switch
    "KillSwitch",
    "KillSwitchLevel",
    "KillSwitchTrigger",
    "KillSwitchStatus",
    "KillSwitchEvent",
    "KillSwitchConfig",
    # Market State
    "MarketRegimeDetector",
    "MarketRegime",
    "RegimeResult",
    "RegimeConfidence",
    "RegimeConfig",
    # Pressure
    "PressureEngine",
    "PressureResult",
    "PressureDirection",
    "PressureStrength",
    "PressureConfig",
    "OHLCVBar",
    # Auto Switch
    "AutoSwitcher",
    "StrategyType",
    "StrategyProfile",
    "StrategySwitch",
    "SwitchReason",
    "AutoSwitchConfig",
    "REGIME_STRATEGY_MAP",
    "STRATEGY_PROFILES",
]
