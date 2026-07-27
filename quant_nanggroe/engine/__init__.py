"""Engine orchestrator: agentic trading, event engine, and model registry.

All submodules are imported explicitly at the point of use by callers.
No lazy __getattr__ — fail fast on missing modules.
"""
__all__ = [
    'agentic_trading',
    'audit',
    'autoswitch',
    'decision',
    'event_engine',
    'grounding',
    'llm_router',
    'market_state',
    'microstructure',
    'model_registry',
    'monitor_hub',
    'nim_provider',
    'observability',
    'persistence',
    'pressure',
    'regime_detector',
    'strategy_lifecycle',
    'worker',
]
