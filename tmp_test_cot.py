"""Quick integration test for COT module."""
import sys
sys.path.insert(0, ".")

import numpy as np
np.random.seed(42)

# 1. Import checks
from quant_nanggroe.engine.cot import COTAnalyzer, COTFetcher, CME_TO_COT_MAP, POSITIONING_SIGNAL
print("PASS: COT imports")
print("  Symbols mapped:", len(CME_TO_COT_MAP))
print("  Signal types:", list(POSITIONING_SIGNAL.keys()))

# 2. Fetcher creation
fe = COTFetcher(store_txt=False, verbose=False)
print("PASS: COTFetcher created, cache exists:", fe.cache_exists())

# 3. COTAnalyzer fetch and evaluate
az = COTAnalyzer(years_history=1, fetcher=fe)
ok = az.fetch_history()
print("PASS: COTAnalyzer fetch:", ok)

if az.is_loaded:
    print("  Markets:", len(az.available_markets), "Symbols:", len(az.available_symbols))
    eval_gc = az.evaluate("GC1!")
    print("PASS: GC1 eval:", eval_gc.get("signal"), "grade:", eval_gc.get("grade"),
          "pct:", eval_gc.get("percentile_noncomm"))
    eval_es = az.evaluate("ES1!")
    print("PASS: ES1 eval:", eval_es.get("signal"), "grade:", eval_es.get("grade"))
    smry = az.get_summary()
    print("PASS: Summary extremes:", smry.get("n_extreme"))
    assert smry["loaded"] is True
    assert smry["n_symbols"] > 0
else:
    print("SKIP: No COT data loaded (offline?)")

# 4. MasterQuantNanggroeEngine integration
from quant_nanggroe.engine.causal import MasterQuantNanggroeEngine
eng = MasterQuantNanggroeEngine()
result = eng.evaluate_full_pipeline(
    "GEOPOLITICAL_SUPPLY_SHOCK",
    geopolitical_risk_delta=40.0,
    dxy_change=0.4,
    bond_change=0.3,
)
cot_info = result["phase2_cot"]
print("PASS: MasterEngine COT:", cot_info.get("status"),
      "analyzer_used:", cot_info.get("analyzer_used", False))

# 5. RiskEnforcer COT check
from quant_nanggroe.engine_production_bridge import RiskEnforcer
enf = RiskEnforcer()
has_cot = hasattr(enf, "_cot") and enf._cot is not None
print("PASS: RiskEnforcer has COT:", has_cot)

print()
print("ALL TESTS PASSED")
