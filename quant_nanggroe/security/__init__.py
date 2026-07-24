"""Security layer: audit, auth, encryption, and key management."""

# Package init - lazy imports to avoid circular deps
# Import modules explicitly when needed, not via __init__
__all__ = [
    'audit',
    'auth',
    'credential_inference',
    'credential_manager',
    'encryption',
    'keyvault',
]

# Lazy imports for submodules
def __getattr__(name):
    import importlib
    try:
        module = importlib.import_module(f".{name}", __package__)
        return module
    except ImportError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
