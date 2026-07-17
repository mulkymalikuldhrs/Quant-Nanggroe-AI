#!/usr/bin/env python
"""QNA Autonomous Trading Cron — runs every 15 minutes.

Usage: 
  python scripts/autonomous_cron.py              # paper mode
  QNA_LIVE_TRADING=1 python scripts/autonomous_cron.py   # live MT5

Output: JSON result to stdout. Empty if nothing to report.
"""
import json, os, sys, time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QNA_LIVE_TRADING", "0")

try:
    from quant_nanggroe.engine.agentic import AutonomousPipeline
except ImportError:
    # Fallback to direct import
    sys.path.insert(0, ".")
    from quant_nanggroe.engine.autonomous.pipeline import AutonomousPipeline

DEFAULT_SYMBOLS = ["BTC-USD", "ETH-USD", "EURUSD=X", "AUDUSD=X"]


def run():
    pipeline = AutonomousPipeline()
    results = []
    errors = []

    for sym in DEFAULT_SYMBOLS:
        try:
            # Use asyncio to run the async pipeline
            import asyncio
            r = asyncio.run(pipeline.run_cycle([sym]))
            results.append({
                "symbol": sym,
                "signals": r.get("signals_generated", 0),
                "trades": r.get("trades_executed", 0),
                "errors": r.get("errors", []),
            })
        except Exception as e:
            errors.append({"symbol": sym, "error": str(e)})

    # Compact output — only report when there's activity
    total_signals = sum(r["signals"] for r in results)
    total_trades = sum(r["trades"] for r in results)

    if total_signals == 0 and total_trades == 0 and not errors:
        # Silent — nothing to report
        return

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "cycle_id": int(time.time()),
        "summary": f"{total_signals} signals, {total_trades} trades across {len(results)} symbols",
        "details": results,
    }
    if errors:
        report["errors"] = errors

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
