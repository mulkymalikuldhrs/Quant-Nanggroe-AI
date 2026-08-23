"""Wire scorecard verdicts into StrategyLifecycleManager.

FAZE 2 (replan): the lifecycle manager had ZERO strategies registered.
This script bootstraps it by:
1. Registering all known strategies
2. Computing REAL scorecards from synced journal
3. Transitioning strategies based on verdicts (KEEP/TUNE/KILL)

After this, get_active_strategies() returns only PROVEN strategies.
"""
import sys
sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")

import quant_nanggroe.engine.strategies  # noqa: F401
from quant_nanggroe.engine.strategy_lifecycle import (
    StrategyLifecycleManager, StrategyStatus,
)
from quant_nanggroe.engine.analytics.strategy_scorecard import compute_all_strategies


def main():
    mgr = StrategyLifecycleManager()
    scores = compute_all_strategies()

    print("=== BOOTSTRAP LIFECYCLE FROM SCORECARD ===")
    registered = 0
    killed = 0
    kept = 0

    for strat_name, card in scores["strategies"].items():
        n = card["n_trades"]
        verdict = card["verdict"]
        expectancy = card["expectancy"]

        if strat_name not in mgr.strategies:
            mgr.register_strategy(strat_name)
            registered += 1

        if verdict == "NEGATIVE_EDGE" and n >= 20:
            mgr._transition(strat_name, StrategyStatus.KILLED,
                            f"Scorecard: negative edge (expectancy={expectancy}, n={n})")
            killed += 1
            print(f"  KILLED {strat_name}: expectancy={expectancy} n={n}")
        elif verdict in ("PROVEN_GOOD", "MARGINAL_POSITIVE"):
            mgr._transition(strat_name, StrategyStatus.ACTIVE,
                            f"Scorecard: positive edge (expectancy={expectancy})")
            kept += 1
            print(f"  ACTIVE {strat_name}: expectancy={expectancy}")
        else:
            # INSUFFICIENT_DATA / NEUTRAL -> HIBERNATING until proven
            mgr._transition(strat_name, StrategyStatus.HIBERNATING,
                            f"Scorecard: {verdict} (n={n})")
            print(f"  HIBERNATE {strat_name}: {verdict} n={n}")

    # Also register top CPCV specialists that don't have journal trades yet
    from quant_nanggroe.engine.strategy_allocation import allocation_map
    alloc = allocation_map()
    for asset_class, strategies in alloc.items():
        for s in strategies:
            if s not in mgr.strategies:
                mgr.register_strategy(s)
                registered += 1
                print(f"  REGISTERED {s} (CPCV specialist for {asset_class})")

    active = mgr.get_active_strategies()
    print(f"\n=== RESULT ===")
    print(f"Registered: {registered}")
    print(f"Killed: {killed}")
    print(f"Active: {len(active)} -> {active[:10]}")
    print(f"Report: active={report['active']}, total={mgr.get_strategy_report()['total_strategies']}")

    return mgr


if __name__ == "__main__":
    main()
