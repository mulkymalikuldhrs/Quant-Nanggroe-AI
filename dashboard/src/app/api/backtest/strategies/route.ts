import { NextResponse } from "next/server";
import { execSync } from "child_process";
import path from "path";

// QNA root (relative to dashboard/ at repo root)
const QNA_ROOT = path.resolve(process.cwd(), "..");
const PYTHON = process.env.QNA_PYTHON || "python3";

/**
 * GET /api/backtest/strategies
 * Returns ALL real QNA strategies from the StrategyRegistry + latest audit metrics.
 * No hardcoded fake strategies.
 */
export async function GET() {
  try {
    const script = `
import sys, json, os
sys.path.insert(0, r'${QNA_ROOT}')
from quant_nanggroe.engine.strategies.registry import StrategyRegistry
# Load audit results if present
audit_path = r'${QNA_ROOT}/data/strategy_audit.json'
audit = {}
if os.path.exists(audit_path):
    with open(audit_path) as f:
        import json as j
        data = j.load(f)
        for r in data.get('all', []):
            audit[r['strategy']] = r
strategies = []
for name in StrategyRegistry.list_strategies():
    cls = StrategyRegistry.get(name)
    meta = audit.get(name, {})
    strategies.append({
        "id": name,
        "name": name.replace('_', ' ').title(),
        "description": (getattr(cls, '__doc__', '') or '')[:200],
        "category": "quant",
        "asset_classes": ["BTC", "ETH", "SOL", "EURUSD", "XAUUSD"],
        "timeframes": ["M5", "M15", "H1", "H4"],
        "enabled": True,
        "backtest": {
            "return_pct": meta.get("return_pct"),
            "sharpe": meta.get("sharpe"),
            "max_dd_pct": meta.get("max_dd_pct"),
            "win_rate": meta.get("win_rate"),
            "gate": meta.get("gate"),
            "score": meta.get("score"),
        } if meta else None,
    })
print(json.dumps(strategies))
`;
    const out = execSync(`${PYTHON} -c "${script.replace(/"/g, '\\"')}"`, {
      cwd: QNA_ROOT,
      encoding: "utf-8",
      timeout: 60000,
    });
    const strategies = JSON.parse(out.trim());
    return NextResponse.json(strategies);
  } catch (err: any) {
    console.error("Strategy API error:", err);
    return NextResponse.json(
      { error: "Failed to load strategies", detail: String(err?.message || err) },
      { status: 500 }
    );
  }
}
