"""Integration test for ThesisDriftGuard module."""
import sys
sys.path.insert(0, ".")

import numpy as np
np.random.seed(42)

# 1. Import checks
from quant_nanggroe.engine.risk.thesis_drift_guard import (
    ThesisDriftGuard, TradeThesis, ThesisStage, STAGE_LABELS, STAGE_ACTIONS,
)
print("PASS: ThesisDriftGuard imports")
print("  Stages:", [s.name for s in ThesisStage])
assert len(ThesisStage) == 3

# 2. Create guard
guard = ThesisDriftGuard(advisory_threshold=1, warning_threshold=2)
print("PASS: Guard created")

# 3. Register a position with a macro thesis
thesis = TradeThesis(
    direction="bullish",
    event_type="GEOPOLITICAL_SUPPLY_SHOCK",
    expected_weather="RISK_OFF",
    expected_bias_sign=1,
    notes="Gold long on geopolitical supply shock",
)
guard.register_position("XAUUSD", "long", thesis=thesis, entry_price=3100.0)
print("PASS: Position registered, count:", guard.n_positions)
assert guard.n_positions == 1

# 4. Check with NO contradictions (same event, NEUTRAL weather)
result = guard.check(
    event_type="GEOPOLITICAL_SUPPLY_SHOCK",
    weather="NEUTRAL_MIXED",
    cot_signal="BALANCED",
    smt_divergence=False,
)
print("PASS: No contradictions — stage:", result["label"], "stage_int:", result["stage_int"])
assert result["stage_int"] == 1  # MONITORING (0 contradictions)

# 5. Check with 1 contradiction (RISK_OFF weather vs long = 1 contradiction -> WARNING)
result = guard.check(
    event_type="GEOPOLITICAL_SUPPLY_SHOCK",
    weather="RISK_OFF",
    cot_signal="BALANCED",
)
print("PASS: 1 contradiction — stage:", result["label"], "contr:", 
      len(result.get("positions", {}).get("XAUUSD", {}).get("latest_contradictions", [])))
assert result["stage_int"] == 2  # WARNING

# 6. Check with 2+ contradictions (2 = HARD_EXIT)
result = guard.check(
    event_type="CENTRAL_BANK_DOVISH",
    weather="RISK_OFF",
    cot_signal="EXTREME_LONG_OVERBOUGHT",
    smt_divergence=True,
)
print("PASS: Hard exit check — stage:", result["label"], "hard_exit:", result.get("has_hard_exit"))
if guard.hard_exit_enabled:
    assert result["has_hard_exit"] is True

# 7. Check get_status
status = guard.get_status()
print("PASS: Status — positions:", status["n_positions"], "last_stage:", status["last_max_stage"])
assert status["n_positions"] == 1

# 8. Unregister
guard.unregister_position("XAUUSD")
print("PASS: Unregistered, count:", guard.n_positions)
assert guard.n_positions == 0

# 9. Wire into ProductionEngine
from quant_nanggroe.engine_production_bridge import RiskEnforcer, create_production_engine
enf = RiskEnforcer()
has_thesis = hasattr(enf, "_thesis") and enf._thesis is not None
print("PASS: RiskEnforcer has thesis guard:", has_thesis)
assert has_thesis

# Test thesis methods on RiskEnforcer
ok = enf.thesis_register_position("BTCUSDT", "long", event_type="GEOPOLITICAL_SUPPLY_SHOCK", entry_price=67000)
print("PASS: RiskEnforcer thesis_register:", ok)
assert ok

thesis_check = enf.thesis_check("GEOPOLITICAL_SUPPLY_SHOCK", "NEUTRAL_MIXED")
print("PASS: RiskEnforcer thesis_check — stage:", thesis_check.get("label"), "n_pos:", len(thesis_check.get("positions", {})))

enf.thesis_unregister("BTCUSDT")
print("PASS: RiskEnforcer thesis_unregister")
assert enf._thesis.n_positions == 0

status = enf.thesis_get_status()
print("PASS: RiskEnforcer thesis_get_status — active:", status.get("active"))

print()
print("ALL TESTS PASSED")
