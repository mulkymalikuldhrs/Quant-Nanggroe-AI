#!/usr/bin/env python3
"""Seed paper_state files with realistic demo data for QNA dashboard."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper_state"
DOCS = ROOT / "docs"
PAPER.mkdir(exist_ok=True)

# state.json
json.dump({"cycle_count": 42, "uptime_hours": 12.5, "mode": "paper",
           "started_at": "2026-07-08T14:00:00Z"}, (PAPER / "state.json").open("w"))

# pnl.csv
with open(PAPER / "pnl.csv", "w") as f:
    f.write("cycle,signals,cash,total_value,unrealized_pnl,realized_pnl,total_pnl,positions,drawdown_pct,timestamp\n")
    for i in range(1, 6):
        f.write(f"{i},8,8500.00,12500.00,1500.00,500.00,2000.00,4,12.5,2026-07-09T0{i}:00:00Z\n")

# auto_disable_state.json
AD = {"strategies": {
    s: {"disabled": False, "sharpe_ratio": 0.5, "psr": 1, "dsr": 1, "verdict": "PASS"}
    for s in ["Momentum", "RegimeBased", "PairsTrading", "StatisticalArbitrage",
              "VolatilityArbitrage", "MeanReversion", "CryptoSpecific", "MarketMaking"]
}, "global_max_drawdown_pct": 25.0}
AD["strategies"]["VolatilityArbitrage"].update({"disabled": False, "sharpe_ratio": -0.7164, "psr": 0, "dsr": 0, "verdict": "FAIL"})
AD["strategies"]["MeanReversion"].update({"disabled": False, "sharpe_ratio": -2.6370, "psr": 0, "dsr": 0, "verdict": "FAIL"})
json.dump(AD, (PAPER / "auto_disable_state.json").open("w"), indent=2)

# alpha_report.json  (sources sharpe/psr/dsr/verdict for strategy-table)
json.dump({"strategies": {
    "Momentum":             {"aggregate": {"mean_sharpe": 0.8983, "mean_psr": 1, "mean_dsr": 1}, "verdict": "PASS"},
    "RegimeBased":          {"aggregate": {"mean_sharpe": 2.2581, "mean_psr": 1, "mean_dsr": 1}, "verdict": "PASS"},
    "PairsTrading":         {"aggregate": {"mean_sharpe": 0.4249, "mean_psr": 1, "mean_dsr": 1}, "verdict": "PASS"},
    "StatisticalArbitrage": {"aggregate": {"mean_sharpe": 0.6060, "mean_psr": 1, "mean_dsr": 1}, "verdict": "PASS"},
    "VolatilityArbitrage":  {"aggregate": {"mean_sharpe": -0.7164, "mean_psr": 0, "mean_dsr": 0}, "verdict": "FAIL"},
    "MeanReversion":        {"aggregate": {"mean_sharpe": -2.6370, "mean_psr": 0, "mean_dsr": 0}, "verdict": "FAIL"},
    "CryptoSpecific":       {"aggregate": {"mean_sharpe": 0.5156, "mean_psr": 1, "mean_dsr": 1}, "verdict": "PASS"},
    "MarketMaking":         {"aggregate": {"mean_sharpe": 0.1972, "mean_psr": 1, "mean_dsr": 1}, "verdict": "PASS"},
}}, (DOCS / "alpha_report.json").open("w"), indent=2)

# kill_switch_state.json
json.dump({"is_active": False, "level": None, "trigger_history": []}, (PAPER / "kill_switch_state.json").open("w"))

# kill switch state inferred fallback → placeholder
json.dump({"active": False, "levels": {"Level 1": {"active": False}}}, (PAPER / "kill_switch_fallback.json").open("w"))

# remaining state stubs (prevent 404 from the dashboard fetches)
for name, data in [
    ("tuned_params", {}),
    ("correlation_state", {"correlations": "pending"}),
    ("budget_state", {"budget_remaining": 1000}),
    ("anomaly_state", {"alerts": []}),
    ("regime_adapted_params", {"regime": "neutral", "confidence": 0.65, "multiplier": 1.0}),
]:
    json.dump(data, (PAPER / f"{name}.json").open("w"))

# daemon.pid
(PAPER / "daemon.pid").write_text("42")

print("paper_state seeded")
