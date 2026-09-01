"""Legacy shim — loads PairsTrade from archived location.

Original file moved to archive/strategy_legacy_2026-08-28/quant_nanggroe_strategies/
via robocopy /MOVE. This shim preserves `from quant_nanggroe.strategies.pairs_trade import PairsTrade`.
"""
import importlib.util
import pathlib

_archive = pathlib.Path(__file__).resolve().parents[2] / "archive" / "strategy_legacy_2026-08-28" / "quant_nanggroe_strategies" / "pairs_trade.py"
_spec = importlib.util.spec_from_file_location("_archived_pairs_trade", _archive)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
PairsTrade = _mod.PairsTrade
__all__ = ["PairsTrade"]
