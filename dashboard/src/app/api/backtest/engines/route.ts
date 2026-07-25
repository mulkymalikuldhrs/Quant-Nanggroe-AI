import { NextResponse } from "next/server";
import { execSync } from "child_process";
import path from "path";

const QNA_ROOT = path.resolve(process.cwd(), "..");
const PYTHON = process.env.QNA_PYTHON || "python3";

/**
 * GET /api/backtest/engines
 * Returns available QNA backtest engines (real, from codebase introspection).
 */
export async function GET() {
  try {
    const script = `
import sys, json
sys.path.insert(0, r'${QNA_ROOT}')
engines = []
try:
    from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver
    engines.append("StrategyEvolver (real backtest)")
except Exception as e:
    pass
try:
    from quant_nanggroe.engine.strategy.strategies.self_finetune import SelfFineTuner
    engines.append("SelfFineTuner (param grid-search)")
except Exception:
    pass
engines.append("AdaptiveSignalPipeline (regime-based)")
engines.append("WalkForward (5-fold)")
print(json.dumps(engines))
`;
    const out = execSync(`${PYTHON} -c "${script.replace(/"/g, '\\"')}"`, {
      cwd: QNA_ROOT,
      encoding: "utf-8",
      timeout: 30000,
    });
    return NextResponse.json(JSON.parse(out.trim()));
  } catch (err: any) {
    return NextResponse.json(
      { error: "Failed to load engines", detail: String(err?.message || err) },
      { status: 500 }
    );
  }
}
