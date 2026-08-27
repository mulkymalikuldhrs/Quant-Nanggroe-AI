"""
QNA Import Chain Smoke Test
Verifies all module imports resolve correctly.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def check_import(module_path, expected_attr=None):
    try:
        mod = __import__(module_path, fromlist=[expected_attr] if expected_attr else [])
        if expected_attr:
            attr = getattr(mod, expected_attr, None)
            assert attr is not None, f"{module_path} has no {expected_attr}"
        print(f"  \u2713 {module_path}" + (f".{expected_attr}" if expected_attr else ""))
        return True
    except Exception as e:
        print(f"  \u2717 {module_path}: {e}")
        return False

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print("QNA IMPORT CHAIN SMOKE TEST")
    print(f"{'='*50}\n")

    imports = [
        # Engine top
        ("quant_nanggroe",),
        ("quant_nanggroe.engine",),

        # Kelly modules (NEW - MVP-3)
        ("quant_nanggroe.engine.kelly",),
        ("quant_nanggroe.engine.kelly.fractional", "FractionalKelly"),
        ("quant_nanggroe.engine.kelly.bayesian", "BayesianKelly"),
        ("quant_nanggroe.engine.kelly.drawdown", "DrawdownControlledKelly"),
        ("quant_nanggroe.engine.kelly.multi_asset", "MultiAssetKelly"),
        ("quant_nanggroe.engine.kelly.backtest_integration", "KellyBacktestBridge"),
        ("quant_nanggroe.engine.kelly.backtest_integration", "StrategyKellyMixin"),

        # Regime modules
        ("quant_nanggroe.engine.regime",),
        ("quant_nanggroe.engine.regime.hmm_detector",),
        ("quant_nanggroe.engine.regime.ensemble",),
        ("quant_nanggroe.engine.regime.volatility_clustering",),
        ("quant_nanggroe.engine.regime.strategy_selector", "RegimeStrategySelector"),

        # Strategy modules (NEW - MVP-4)
        ("quant_nanggroe.engine.strategy",),
        ("quant_nanggroe.engine.strategy.regime_strategy", "RegimeAdaptiveStrategy"),

        # Data modules (NEW - MVP-1 + MVP-7)
        ("quant_nanggroe.engine.data",),
        ("quant_nanggroe.engine.data.fallback_chain", "DataFallbackChain"),
        ("quant_nanggroe.engine.data.data_manager", "DataManager"),

        # Data providers (NEW - MVP-1)
        ("quant_nanggroe.engine.data.providers",),
        ("quant_nanggroe.engine.data.providers.yfinance", "YahooFinanceProvider"),
        ("quant_nanggroe.engine.data.providers.alpha_vantage", "AlphaVantageProvider"),
        ("quant_nanggroe.engine.data.providers.polygon", "PolygonProvider"),
        ("quant_nanggroe.engine.data.providers.binance", "BinanceProvider"),
        ("quant_nanggroe.engine.data.providers.coingecko", "CoinGeckoProvider"),
        ("quant_nanggroe.engine.data.providers.fred", "FREDProvider"),
        ("quant_nanggroe.engine.data.providers.gdelt", "GDELTProvider"),
        ("quant_nanggroe.engine.data.providers.worldbank", "WorldBankProvider"),

        # Execution modules
        ("quant_nanggroe.engine.execution",),
        ("quant_nanggroe.engine.execution.almgren_chriss",),
    ]

    results = []
    for imp in imports:
        module_path = imp[0]
        expected_attr = imp[1] if len(imp) > 1 else None
        ok = check_import(module_path, expected_attr)
        results.append(ok)

    passed = sum(1 for r in results if r)
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{len(results)} imports resolved")
    if passed == len(results):
        print("STATUS: ALL PASSED \u2713")
        sys.exit(0)
    else:
        print(f"STATUS: {len(results)-passed} FAILED \u2717")
        sys.exit(1)
    print(f"{'='*50}")
