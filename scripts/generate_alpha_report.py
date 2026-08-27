#!/usr/bin/env python3
"""Generate WS1 Alpha Report from walk-forward results."""
import json
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "quant_nanggroe" / "data" / "backtest" / "results"
REPORT_PATH = REPO / "docs" / "WS1_ALPHA_REPORT.md"

if not RESULTS_DIR.exists():
    print(f"No results dir at {RESULTS_DIR}")
    exit(1)

result_files = sorted(RESULTS_DIR.glob("walkforward_*.json"))
if not result_files:
    print("No results JSON files")
    exit(1)

all_results = []
for f in result_files:
    all_results.extend(json.loads(f.read_text()))

lines = []
lines.append("# WS1 Alpha Validation Report")
lines.append("")
lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
lines.append(f"**Total strategies:** {len(all_results)}")
lines.append("")
lines.append("| Strategy | Backtest Sharpe | WF Avg Sharpe | Consistent |")
lines.append("|----------|----------------|---------------|------------|")
for r in sorted(all_results, key=lambda x: x['backtest'].get('sharpe',0), reverse=True):
    name = r['name']
    bt_sharpe = r['backtest'].get('sharpe', 0)
    wf_sharpe = r['walkforward'].get('avg_sharpe', 0)
    consistent = "✅" if wf_sharpe > 0.5 else "❌"
    lines.append(f"| {name} | {bt_sharpe:.2f} | {wf_sharpe:.2f} | {consistent} |")

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text("\n".join(lines))
print(f"Report written to {REPORT_PATH}")
