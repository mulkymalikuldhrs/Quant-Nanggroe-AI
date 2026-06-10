"""
Engine Package — Deterministic Core
====================================
100% deterministic, no AI, no approximation.
All functions are independently testable.

Includes NautilusTrader adapter for production backtesting.
"""

from quant_nanggroe_ai.engine.math_lib import MathEngine
from quant_nanggroe_ai.engine.market_state import MarketStateEngine, MarketStateResult
from quant_nanggroe_ai.engine.pressure import PressureNormalizationEngine, PressureInput, PressureResult
from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard, RiskCheckResult
from quant_nanggroe_ai.engine.decision import DecisionSynthesisEngine, DecisionResult, DecisionRule, DECISION_TABLE
from quant_nanggroe_ai.engine.kill_switch import KillSwitch, KillSwitchState
from quant_nanggroe_ai.engine.strategy_lifecycle import StrategyLifecycleManager, StrategyState
from quant_nanggroe_ai.engine.audit import AuditLogger, AuditEntry
from quant_nanggroe_ai.engine.autoswitch import AutoSwitchEngine, ProviderHealth

__all__ = [
    # Math
    "MathEngine",
    # Market State
    "MarketStateEngine",
    "MarketStateResult",
    # Pressure
    "PressureNormalizationEngine",
    "PressureInput",
    "PressureResult",
    # Risk Guard
    "ConstitutionalRiskGuard",
    "RiskCheckResult",
    # Decision
    "DecisionSynthesisEngine",
    "DecisionResult",
    "DecisionRule",
    "DECISION_TABLE",
    # Kill Switch
    "KillSwitch",
    "KillSwitchState",
    # Strategy Lifecycle
    "StrategyLifecycleManager",
    "StrategyState",
    # Audit
    "AuditLogger",
    "AuditEntry",
    # AutoSwitch
    "AutoSwitchEngine",
    "ProviderHealth",
]

# Lazy imports for NautilusTrader adapter (optional dependency)
def __getattr__(name: str):
    if name in ("NautilusAdapter", "BacktestConfig", "NautilusResults", "StrategyAdapter", "AbstractStrategyAdapter"):
        from quant_nanggroe_ai.engine.nautilus_adapter import (
            NautilusAdapter, BacktestConfig, NautilusResults,
            StrategyAdapter, AbstractStrategyAdapter, is_nautilus_available,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
