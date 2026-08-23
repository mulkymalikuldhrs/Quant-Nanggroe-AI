import sys, json
sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")
from quant_nanggroe.engine.analytics.strategy_scorecard import compute_all_strategies
result = compute_all_strategies()
out = json.dumps(result, indent=2, default=str)
open(r"D:\repositories\Quant-Nanggroe-AI-worktree\scorecard_out.txt", "w", encoding="utf-8").write(out)
print("written to scorecard_out.txt")
