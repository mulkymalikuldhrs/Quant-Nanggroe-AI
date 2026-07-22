#!/usr/bin/env python3
"""
Quant Nanggroe — Hedge Fund Runner
===================================
CLI entry point for running the hedge fund aggregator.

Usage:
    python -m quant_nanggroe.hedge_fund.runner [symbols...]

Examples:
    python -m quant_nanggroe.hedge_fund.runner
    python -m quant_nanggroe.hedge_fund.runner EURUSD GBPUSD
    python -m quant_nanggroe.hedge_fund.runner --paper EURUSD
"""

import sys
import argparse
from pathlib import Path

# ── Ensure project root is in PYTHONPATH ──
_HERE = Path(__file__).resolve().parent
_QNA_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_QNA_ROOT))

from quant_nanggroe.hedge_fund import run_once, PAPER_TRADE


def main():
    parser = argparse.ArgumentParser(
        description="Quant Nanggroe Hedge Fund Aggregator"
    )
    parser.add_argument(
        "symbols", nargs="*", default=["EURUSD"],
        help="Symbols to trade (e.g. EURUSD GBPUSD)"
    )
    parser.add_argument(
        "--paper", action="store_true", default=None,
        help="Force paper trading mode"
    )
    args = parser.parse_args()

    if args.paper is not None:
        import os
        os.environ["PAPER_TRADE"] = "true" if args.paper else "false"

    results = []
    for sym in args.symbols:
        print(f"\n{'='*60}")
        print(f"  HF RUN: {sym}")
        print(f"{'='*60}")
        result = run_once(sym)
        results.append((sym, result))
        print(f"  Result: {result}")

    print(f"\n{'='*60}")
    print(f"  DONE — {len(results)} symbols processed")
    for sym, res in results:
        status = "✅" if res and res.get("executed") else "⏭️"
        print(f"  {status} {sym}: {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
