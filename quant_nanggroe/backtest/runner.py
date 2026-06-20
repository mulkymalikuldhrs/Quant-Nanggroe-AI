"""
QNA Backtest Runner
===================
Orchestrates: data fetch → strategy generation → backtest → select → deploy

Usage:
  python3 -m quant_nanggroe.backtest.runner          # Full pipeline
  python3 -m quant_nanggroe.backtest.runner status    # Show last results
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

QNA_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = QNA_DIR / "data"
RESULT_FILE = DATA_DIR / "backtest_results.json"
DEPLOY_FILE = DATA_DIR / "deployed_strategies.json"
LOG_FILE = QNA_DIR / "logs" / "backtest.log"

sys.path.insert(0, str(QNA_DIR))


def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


class BacktestRunner:
    """Full pipeline orchestrator."""

    def __init__(self):
        self.coins = {
            "bitcoin": {"symbol": "BTCUSDT", "alloc": 0.40},
            "ethereum": {"symbol": "ETHUSDT", "alloc": 0.25},
            "solana": {"symbol": "SOLUSDT", "alloc": 0.20},
            "binancecoin": {"symbol": "BNBUSDT", "alloc": 0.15},
        }

    def run_pipeline(self, days=365, max_strategies=0, top_n=20):
        """Full pipeline: fetch → generate → backtest → select → deploy."""
        from quant_nanggroe.backtest.strategy_factory import StrategyFactory, TEMPLATES
        from quant_nanggroe.backtest.backtester import Backtester, DataFetcher

        log("=" * 60)
        log("QNA BACKTEST PIPELINE STARTED")
        log("=" * 60)

        # 1. Strategy generation
        log("Generating strategy variants...")
        factory = StrategyFactory()
        all_variants = factory.generate(max_variants=max_strategies)
        log(f"Generated {len(all_variants)} strategy variants across {len(TEMPLATES)} templates")

        per_template = factory.stats()
        for name, count in sorted(per_template.items()):
            log(f"  {name}: {count} variants")

        # 2. Fetch data + backtest per coin
        fetcher = DataFetcher()
        backtester = Backtester()
        all_results = {}

        for coin_id, info in self.coins.items():
            log(f"\nFetching {coin_id} ({days}d)...")
            candles = fetcher.fetch_historical(coin_id, days)
            log(f"  Got {len(candles)} candles")

            log(f"Backtesting {len(all_variants)} variants on {coin_id}...")
            start = time.time()
            results = backtester.run_batch(all_variants, candles, max_strategies=max_strategies)
            elapsed = time.time() - start
            log(f"  Done in {elapsed:.1f}s ({elapsed/len(all_variants):.2f}s per strategy)")

            # Filter by Sharpe
            filtered = backtester.rank(results, min_sharpe=0.1, max_dd=0.40, min_trades=2, top_n=top_n)
            log(f"  Top {len(filtered)} strategies (Sharpe >= 0.1, DD <= 40%, >= 2 trades):")

            for i, r in enumerate(filtered[:10]):
                log(f"    {i+1}. {r.strategy_name[:60]}: Sharpe={r.sharpe:.2f} "
                    f"Ret={r.total_return:.1%} DD={r.max_drawdown:.1%} "
                    f"Win={r.win_rate:.1%} Trades={r.num_trades}")

            all_results[coin_id] = {
                "results": [r.to_dict() for r in filtered],
                "total_tested": len(results),
                "passed": len(filtered),
                "days": days,
                "timestamp": datetime.now().isoformat(),
            }

        # 3. Save all results
        output = {
            "timestamp": datetime.now().isoformat(),
            "coins": all_results,
            "total_variants": len(all_variants),
            "meta": {
                "days": days,
                "min_sharpe": 0.1,
                "max_drawdown": 0.40,
                "min_trades": 2,
                "top_n": top_n,
            }
        }
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_FILE.write_text(json.dumps(output, indent=2))
        log(f"\nResults saved to {RESULT_FILE}")

        # 4. Select and deploy top strategies across all coins
        self._select_deploy(all_results)
        log("\n" + "=" * 60)
        log("BACKTEST PIPELINE COMPLETE")
        log("=" * 60)
        return output

    def _select_deploy(self, all_results):
        """Select top strategies across all coins and deploy to live engine."""
        all_strategies = []
        for coin_id, data in all_results.items():
            for r in data["results"]:
                r["coin_id"] = coin_id
                all_strategies.append(r)

        all_strategies.sort(key=lambda r: r.get("sharpe", 0), reverse=True)
        deploy = {
            "timestamp": datetime.now().isoformat(),
            "total_backtested": sum(d["total_tested"] for d in all_results.values()),
            "total_passed": sum(d["passed"] for d in all_results.values()),
            "strategies": all_strategies[:50],
        }
        DEPLOY_FILE.write_text(json.dumps(deploy, indent=2))
        log(f"Deployed {len(deploy['strategies'])} strategies to {DEPLOY_FILE}")

    def status(self):
        """Show last backtest results."""
        if not RESULT_FILE.exists():
            log("No backtest results found. Run full pipeline first.")
            return
        data = json.loads(RESULT_FILE.read_text())
        log(f"Last backtest: {data['timestamp']}")
        log(f"Total variants: {data['total_variants']}")
        for coin_id, d in data["coins"].items():
            log(f"\n{coin_id}:")
            log(f"  Tested: {d['total_tested']} | Passed: {d['passed']}")
            for i, r in enumerate(d["results"][:5]):
                log(f"  #{i+1}: {r['name'][:50]} Sharpe={r['sharpe']:.2f} "
                    f"Ret={r['total_return']:.1%} DD={r['max_drawdown']:.1%}")

    def load_deployed(self) -> List[Dict]:
        """Load currently deployed strategies for live engine."""
        if DEPLOY_FILE.exists():
            return json.loads(DEPLOY_FILE.read_text()).get("strategies", [])
        return []


def main():
    import argparse
    parser = argparse.ArgumentParser(description="QNA Backtest Pipeline")
    parser.add_argument("action", nargs="?", default="run",
                        choices=["run", "fast", "status", "deploy"],
                        help="Action: run (full), fast (30d), status, deploy")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--max", type=int, default=0)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    runner = BacktestRunner()

    if args.action == "status":
        runner.status()
        return

    if args.action == "fast":
        args.days = 30
        args.max = 200

    runner.run_pipeline(days=args.days, max_strategies=args.max, top_n=args.top)


if __name__ == "__main__":
    main()
