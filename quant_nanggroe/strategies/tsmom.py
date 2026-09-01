"""Legacy shim — loads TSMOM from archived location."""
import importlib.util
import pathlib

_archive = pathlib.Path(__file__).resolve().parents[2] / "archive" / "strategy_legacy_2026-08-28" / "quant_nanggroe_strategies" / "tsmom.py"
_spec = importlib.util.spec_from_file_location("_archived_tsmom", _archive)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
TSMOM = _mod.TSMOM
__all__ = ["TSMOM"]
