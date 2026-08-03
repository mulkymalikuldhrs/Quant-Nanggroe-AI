import sys
sys.path.insert(0, ".")
try:
    from quant_nanggroe.engine.strategies.registry import StrategyRegistry
    n = len(StrategyRegistry.strategies)
    print(f"STRATEGIES_REGISTERED={n}")
    names = sorted(StrategyRegistry.strategies.keys())[:10]
    print(f"SAMPLE={names}")
except Exception as e:
    print(f"REGISTRY_ERR={type(e).__name__}: {str(e)[:300]}")
