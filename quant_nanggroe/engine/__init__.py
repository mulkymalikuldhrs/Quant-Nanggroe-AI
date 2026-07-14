# Package init - lazy imports to avoid circular deps
# Import modules explicitly when needed, not via __init__
__all__ = [
    'agentic_trading',
    'audit',
    'autoswitch',
    'decision',
    'event_engine',
    'grounding',
    'hermes_auditor',
    'hermes_chart',
    'hermes_decision',
    'hermes_journal',
    'hermes_macro',
    'hermes_market_state',
    'hermes_math',
    'hermes_news',
    'hermes_pressure',
    'hermes_shared_state',
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

# Lazy imports for submodules
def __getattr__(name):
    import importlib
    try:
        module = importlib.import_module(f".{name}", __package__)
        return module
    except ImportError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
