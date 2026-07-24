"""Agent system: base agents, protocols, registry, and orchestration."""

# Package init - lazy imports to avoid circular deps
# Import modules explicitly when needed, not via __init__
__all__ = [
    'base',
    'chinese_wall',
    'debate_engine',
    'gold_trader',
    'graph',
    'marketplace',
    'protocols',
    'registry',
    'state',
    'telegram_bot',
]

# Lazy imports for submodules
def __getattr__(name):
    import importlib
    try:
        module = importlib.import_module(f".{name}", __package__)
        return module
    except ImportError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
