"""
Engine Package — Deterministic Core
====================================
100% deterministic, no AI, no approximation.
All functions are independently testable.
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
from quant_nanggroe_ai.engine.simulation import MonteCarloSimulationEngine, SimulationConfig, SimulationResult, RegimeSimulationConfig, WalkForwardSimulationResult
from quant_nanggroe_ai.engine.models import FactorModelsEngine, FactorModelResult, FactorExposure, FactorReturnDecomposition, RiskAttribution, ZScoreResult
from quant_nanggroe_ai.engine.regime import RegimeDetectionEngine, RegimeDetectionResult, HMMConfig, RegimeProbability, RegimeTransitionMatrix, RegimeClassification
from quant_nanggroe_ai.engine.event_bus import EventBusEngine, Event, EventType, EventPriority, MarketDataEvent, AgentSignalEvent, ExecutionCommandEvent, RiskAlertEvent, DeadLetterEntry

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
    # Simulation
    "MonteCarloSimulationEngine",
    "SimulationConfig",
    "SimulationResult",
    "RegimeSimulationConfig",
    "WalkForwardSimulationResult",
    # Factor Models
    "FactorModelsEngine",
    "FactorModelResult",
    "FactorExposure",
    "FactorReturnDecomposition",
    "RiskAttribution",
    "ZScoreResult",
    # Regime Detection
    "RegimeDetectionEngine",
    "RegimeDetectionResult",
    "HMMConfig",
    "RegimeProbability",
    "RegimeTransitionMatrix",
    "RegimeClassification",
    # Event Bus
    "EventBusEngine",
    "Event",
    "EventType",
    "EventPriority",
    "MarketDataEvent",
    "AgentSignalEvent",
    "ExecutionCommandEvent",
    "RiskAlertEvent",
    "DeadLetterEntry",
]
