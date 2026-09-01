"""Legacy shim — WalkForwardRegistry moved to archive.

Original file archived to archive/strategy_legacy_2026-08-28/engine_strategy/registry.py
via robocopy /MOVE. This shim preserves legacy import path.
"""
import importlib.util
import pathlib
import sys

_archive = pathlib.Path(__file__).resolve().parents[3] / "archive" / "strategy_legacy_2026-08-28" / "engine_strategy" / "registry.py"
_spec = importlib.util.spec_from_file_location("quant_nanggroe.engine.strategy.registry_archived", _archive)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
WalkForwardRegistry = _mod.WalkForwardRegistry
StrategyMetaRegistry = _mod.StrategyMetaRegistry
WalkForwardResult = _mod.WalkForwardResult
StrategyMetadata = _mod.StrategyMetadata
__all__ = ["WalkForwardRegistry", "StrategyMetaRegistry", "WalkForwardResult", "StrategyMetadata"]
