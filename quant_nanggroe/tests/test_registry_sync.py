"""GAP 13 — registry sync verification.

Verifies the 3-registry topology and the WalkForwardRegistry shim's
_strategies property (fixed to reference the module-level _wf_metadata dict).
"""
from __future__ import annotations


def test_strategy_registry_is_canonical():
    from quant_nanggroe.engine.strategies.registry import StrategyRegistry
    from quant_nanggroe.engine.strategy.registry import StrategyRegistry as SR2
    assert SR2 is StrategyRegistry


def test_autoregistry_singleton():
    from quant_nanggroe.engine.registry import AutoRegistry
    assert AutoRegistry() is AutoRegistry()


def test_walkforward_shim_delegates():
    from quant_nanggroe.engine.strategy.registry import WalkForwardRegistry
    wf = WalkForwardRegistry()
    wf.register("gap13_smoke", display_name="Smoke")
    # _strategies property (the fixed line) must resolve module-level dict
    assert "gap13_smoke" in wf._strategies
    assert wf.get("gap13_smoke").name == "gap13_smoke"
    assert isinstance(wf.summary("gap13_smoke"), dict)
    assert isinstance(wf.best_oos(3), list)
    assert wf.decayed("gap13_smoke") is False


def test_walkforward_reexports_resolve():
    from quant_nanggroe.engine.strategy.registry import (
        StrategyMetadata,
        WalkForwardResult,
        get_strategy_metadata,
        list_strategies,
    )
    assert StrategyMetadata and WalkForwardResult
    assert callable(get_strategy_metadata) and callable(list_strategies)
