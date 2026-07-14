# Package init — ponytail: lazy import for hyphenated module names
# Auto-generated __init__.py had syntax errors (from . import bh-cli).
# Replaced with importlib-based lazy loading.

import importlib
import sys
from pathlib import Path

# Module files in this directory (exclude __init__.py itself)
_MODULE_DIR = Path(__file__).parent
_MODULES = [
    f.stem for f in _MODULE_DIR.glob("*.py")
    if f.stem != "__init__"
]

def __getattr__(name: str):
    """Lazy-import any module from this package."""
    if name in _MODULES:
        mod = importlib.import_module(f".{name}", __package__)
        setattr(sys.modules[__package__], name, mod)
        return mod
    raise AttributeError(f"module {__package__!r} has no attribute {name!r}")

def __dir__():
    return _MODULES
