"""Legacy shim — loads TrendFollow from archived location."""
import importlib.util
import pathlib

_archive = pathlib.Path(__file__).resolve().parents[2] / "archive" / "strategy_legacy_2026-08-28" / "quant_nanggroe_strategies" / "trend_follow.py"
_spec = importlib.util.spec_from_file_location("_archived_trend_follow", _archive)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
TrendFollow = _mod.TrendFollow
__all__ = ["TrendFollow"]
