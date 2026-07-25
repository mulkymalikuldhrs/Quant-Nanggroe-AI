"""Backward-compatibility shim — re-exports ``regime_based`` from archive."""
import importlib.util
import sys
from pathlib import Path

_ARCHIVE_FILE = Path(__file__).resolve().parent.parent.parent.parent.parent \
    / "archive" \u002f "strategies_legacy" \u002f "regime_based.py"

if _ARCHIVE_FILE.exists():
    spec = importlib.util.spec_from_file_location(
        f"quant_nanggroe.engine.strategy.strategies.regime_based",
        _ARCHIVE_FILE,
    )
    _mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = _mod
    spec.loader.exec_module(_mod)
    # Re-export names
    for _name in [RegimeBasedStrategy, REGIME_LABELS]:
        if hasattr(_mod, _name.strip()):
            locals()[_name.strip()] = getattr(_mod, _name.strip())
else:
    raise ImportError(f"Archived strategy module not found: {_ARCHIVE_FILE}")

__all__ = [RegimeBasedStrategy, REGIME_LABELS]
