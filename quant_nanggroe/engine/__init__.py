"""Quant Nanggroe AI Engine — Core Trading Intelligence.

Provides the complete engine layer:
- Decision synthesis (deterministic decision table)
- Market state detection (regime classification)
- Pressure normalization (sensor fusion)
- Strategy lifecycle (Darwinian evolution)
- Auto-switch failover (provider health)
- Audit logging (full traceability)
- Risk management (constitutional limits)
- Backtesting (walk-forward, Monte Carlo)
- Execution (broker adapters)
- LLM Router (multi-provider failover with cost tracking)
"""

# ── Core Engine Components ─────────────────────────────────────────────

def __getattr__(name: str):
    """Lazy import to break circular dependencies."""
    _lazy_imports = {
        # Decision
        "DecisionSynthesisEngine": ".decision",
        "DecisionRule": ".decision",
        "DecisionResult": ".decision",
        "DECISION_TABLE": ".decision",
        # Market State
        "MarketStateEngine": ".market_state",
        "MarketStateResult": ".market_state",
        # Pressure
        "PressureNormalizationEngine": ".pressure",
        "PressureInput": ".pressure",
        "PressureResult": ".pressure",
        # Strategy Lifecycle
        "StrategyLifecycleManager": ".strategy_lifecycle",
        "StrategyState": ".strategy_lifecycle",
        # AutoSwitch
        "AutoSwitchEngine": ".autoswitch",
        "ProviderHealth": ".llm_router",
        # Audit
        "AuditLogger": ".audit",
        "AuditEntry": ".audit",
        # Risk
        "RiskManager": ".risk.manager",
        "KellyCriterion": ".risk.kelly",
        "KellyMethod": ".risk.kelly",
        "KellyParameters": ".risk.kelly",
        "KellyResult": ".risk.kelly",
        "VaRCalculator": ".risk.var",
        "RiskParityOptimizer": ".risk.risk_parity",
        "PositionSizer": ".risk.position_sizing",
        "DrawdownMonitor": ".risk.drawdown",
        "CorrelationMonitor": ".risk.correlation",
        "RiskCheckGate": ".risk.checks",
        "KillSwitch": ".risk.kill_switch",
        # LLM Router
        "LLMRouter": ".llm_router",
        "LLMProvider": ".llm_router",
        "ModelTier": ".llm_router",
        "get_llm_router": ".llm_router",
        # Microstructure
        "MicrostructureAnalyzer": ".microstructure",
        "MicrostructureMetrics": ".microstructure",
        "VPINCalculator": ".microstructure",
        "KyleLambdaCalculator": ".microstructure",
        "AmihudCalculator": ".microstructure",
        # PSR
        "PSRResult": ".backtest.psr",
        "DSRResult": ".backtest.psr",
        "ValidationReport": ".backtest.psr",
        "estimate_sharpe": ".backtest.psr",
        "probabilistic_sharpe_ratio": ".backtest.psr",
        "deflated_sharpe_ratio": ".backtest.psr",
        # Event Engine
        "EventType": ".event_engine",
        "Event": ".event_engine",
        "EventEngine": ".event_engine",
        # Factors
        "get_all_academic_factors": ".factors.academic",
        "get_all_alpha101_factors": ".factors.alpha101",
        "get_all_gtja191_factors": ".factors.gtja191",
        "get_all_qlib158_factors": ".factors.qlib158",
        # ML
        "FeatureEngineer": ".ml.feature_engineer",
        "ModelManager": ".ml.model_manager",
        # BH-QNA Bridge
        "BHQnaBridge": ".integration.bh_qna_bridge",
        # Shadow Strategy Extractor
        "StrategyExtractor": ".shadow.extractor",
        "ExtractedRule": ".shadow.extractor",
        "ExtractedStrategy": ".shadow.extractor",
    }
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Decision
    "DecisionSynthesisEngine", "DecisionRule", "DecisionResult", "DECISION_TABLE",
    # Market State
    "MarketStateEngine", "MarketStateResult",
    # Pressure
    "PressureNormalizationEngine", "PressureInput", "PressureResult",
    # Strategy Lifecycle
    "StrategyLifecycleManager", "StrategyState",
    # AutoSwitch
    "AutoSwitchEngine", "ProviderHealth",
    # Audit
    "AuditLogger", "AuditEntry",
    # Risk
    "RiskManager", "KellyCriterion", "KellyMethod", "KellyParameters", "KellyResult",
    "VaRCalculator", "RiskParityOptimizer", "PositionSizer",
    "DrawdownMonitor", "CorrelationMonitor", "RiskCheckGate", "KillSwitch",
    # LLM Router
    "LLMRouter", "LLMProvider", "ModelTier", "get_llm_router",
        # Microstructure
        "MicrostructureAnalyzer", "MicrostructureMetrics",
        "VPINCalculator", "KyleLambdaCalculator", "AmihudCalculator",
        # Backtest
        "PSRResult", "DSRResult", "ValidationReport",
        "estimate_sharpe", "probabilistic_sharpe_ratio", "deflated_sharpe_ratio",
        # Event Engine
        "EventType", "Event", "EventEngine",
        # Factors (loaded by name in practice)
        "get_all_academic_factors", "get_all_alpha101_factors",
        "get_all_gtja191_factors", "get_all_qlib158_factors",
        # ML
        "FeatureEngineer", "ModelManager",
        # BH-QNA Bridge
        "BHQnaBridge",
        # Shadow Strategy Extractor
        "StrategyExtractor",
        "ExtractedRule",
        "ExtractedStrategy",
]
