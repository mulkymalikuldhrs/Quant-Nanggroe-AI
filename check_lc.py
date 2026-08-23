import sys
sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")
from quant_nanggroe.engine.strategy_lifecycle import StrategyLifecycleManager
mgr = StrategyLifecycleManager()
report = mgr.get_strategy_report()
print("Total:", report["total_strategies"])
print("Active:", report["active"])
# Check if smc is tracked
if "smc" in report["strategies"]:
    print(f"smc state: {report['strategies']['smc']}")
else:
    print("smc not tracked by lifecycle")
