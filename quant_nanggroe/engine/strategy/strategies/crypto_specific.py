"""Legacy shim — re-exports from canonical engine/strategies path.

Archived original to archive/strategy_legacy_2026-08-28/ via robocopy /MOVE.
"""
from quant_nanggroe.engine.strategies.crypto_specific import CryptoSpecificStrategy  # noqa: F401

# Preserve legacy wrapper class that accepted `params` dict
import pathlib, importlib.util
_archive = pathlib.Path(__file__).resolve().parents[4] / "archive" / "strategy_legacy_2026-08-28" / "engine_strategy" / "strategies" / "crypto_specific.py"
if _archive.exists():
    _spec = importlib.util.spec_from_file_location("_archived_crypto_legacy", _archive)
    _mod = importlib.util.module_from_spec(_spec)
    if _spec.loader:
        try:
            _spec.loader.exec_module(_mod)
            # expose legacy wrapper if present
            if hasattr(_mod, "CryptoSpecificStrategy"):
                CryptoSpecificStrategyLegacy = _mod.CryptoSpecificStrategy  # noqa: F401
        except Exception:
            pass
