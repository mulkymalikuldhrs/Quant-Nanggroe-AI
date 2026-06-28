#!/usr/bin/env python3
"""OOS Decay Tracker — compare live vs backtest Sharpe, weekly alert.

Per Theme 5 decision, P3 priority (but useful early).
Usage:
    python3 scripts/oos_decay_tracker.py --pnl-csv /root/paper_runs/qna-paper-run-001/pnl.csv
    python3 scripts/oos_decay_tracker.py --alert-if-decayed --threshold 0.5
"""

import argparse
import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("oos-decay")

BACKTEST_SHARPE = -0.335  # RegimeBased OOS Sharpe from fixed walk-forward


def load_pnl(pnl_path: str, max_rows: int = 500) -> list[float]:
    path = Path(pnl_path)
    if not path.exists():
        logger.error("PNL CSV not found: %s", pnl_path)
        return []
    returns = []
    with open(path) as f:
        reader = csv.DictReader(f)
        prev_value = None
        for row in reader:
            val = float(row.get("total_value", 0))
            if prev_value is not None and prev_value > 0:
                ret = (val - prev_value) / prev_value
                returns.append(ret)
            prev_value = val
    return returns[-max_rows:]


def compute_sharpe(returns: list[float], annual_factor: float = 252) -> float:
    if len(returns) < 5:
        return 0.0
    arr = np.array(returns)
    return float(np.mean(arr) / max(np.std(arr), 1e-10) * np.sqrt(annual_factor))


def rolling_sharpe(returns: list[float], window: int = 20) -> list[float]:
    if len(returns) < window:
        return []
    sharpes = []
    for i in range(window, len(returns) + 1):
        sharpes.append(compute_sharpe(returns[i - window:i]))
    return sharpes


def main() -> None:
    parser = argparse.ArgumentParser(description="OOS Decay Tracker")
    parser.add_argument("--pnl-csv", default="/root/paper_runs/qna-paper-run-001/pnl.csv")
    parser.add_argument("--window", type=int, default=20, help="Rolling window for Sharpe (default: 20)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Decay alert threshold (default: 0.5)")
    parser.add_argument("--alert-if-decayed", action="store_true", help="Exit 1 if Sharpe decayed below threshold")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    returns = load_pnl(args.pnl_csv)
    if not returns:
        print("No PnL data available yet")
        sys.exit(0)

    live_sharpe = compute_sharpe(returns)
    sharpes = rolling_sharpe(returns, args.window)
    roll_sharpe = sharpes[-1] if sharpes else 0.0
    decay = BACKTEST_SHARPE - live_sharpe
    decay_vs_roll = (sharpes[0] - sharpes[-1]) if len(sharpes) >= args.window else 0.0 if sharpes else 0.0

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "live_sharpe": round(live_sharpe, 4),
        "rolling_sharpe": round(roll_sharpe, 4),
        "backtest_sharpe": BACKTEST_SHARPE,
        "decay_vs_backtest": round(decay, 4),
        "rolling_decay": round(decay_vs_roll, 4),
        "num_cycles": len(returns),
        "window": args.window,
        "decayed": decay > args.threshold,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        logger.info("Live Sharpe: %.4f | Rolling: %.4f | Backtest: %.4f | Decay: %.4f | Cycles: %d",
                     live_sharpe, roll_sharpe, BACKTEST_SHARPE, decay, len(returns))
        if result["decayed"]:
            logger.warning("DECAY ALERT: Live Sharpe %.4f is %.4f below backtest %.4f (threshold: %.2f)",
                           live_sharpe, decay, BACKTEST_SHARPE, args.threshold)

    if args.alert_if_decayed and result["decayed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
