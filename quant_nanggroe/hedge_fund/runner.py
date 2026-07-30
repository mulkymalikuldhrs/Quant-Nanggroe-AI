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

import argparse
import json
import sys
from pathlib import Path

# ── Ensure project root is in PYTHONPATH ──
_HERE = Path(__file__).resolve().parent
_QNA_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_QNA_ROOT))

from quant_nanggroe.hedge_fund import run_once


def _fmt_causal_ctx(res: dict) -> str:
    """Format causal context summary for terminal display."""
    ctx = res.get("causal_ctx")
    if ctx is None:
        return "  🌫  CausalContext: none"
    lines = []
    regime = ctx.macro_regime.upper() if ctx.macro_regime else "?"
    lines.append(f"  🌤  Macro regime: {regime}")
    if ctx.biases:
        top = sorted(ctx.biases.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        bias_str = ", ".join(f"{k}={v:+.2f}" for k, v in top)
        lines.append(f"  🧭  Biases ({len(ctx.biases)}): {bias_str}")
    else:
        lines.append("  🧭  Biases: none (no event context)")
    return "\n".join(lines)


def _fmt_signal(res: dict) -> str:
    """Format aggregate signal summary."""
    sig = res.get("signal")
    if sig is None:
        return "  📡  No signal"
    bias = sig.get("bias", "neutral")
    conf = sig.get("confidence", 0.0)
    n_votes = len(sig.get("votes", []))
    return f"  📡  Signal: {bias.upper()} (conf={conf:.2f}, {n_votes} votes)"


def _fmt_status_emoji(res: dict) -> str:
    """Pick an emoji for the outcome status."""
    mapping = {
        "executed":       "✅",
        "vetoed":         "🛡️",
        "no_trade":       "⏭️",
        "positions_trailed": "🔁",
        "gate_failed":    "🚫",
    }
    return mapping.get(res.get("status", ""), "❓")


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
    parser.add_argument(
        "--json", action="store_true",
        help="Output machine-readable JSON (one line per symbol)"
    )
    args = parser.parse_args()

    outputs: list[dict] = []

    for sym in args.symbols:
        if args.json:
            result = run_once(sym)
            outputs.append(result)
        else:
            print(f"\n{'='*60}")
            print(f"  HF RUN: {sym}")
            print(f"{'='*60}")

            result = run_once(sym)
            outputs.append(result)

            status_emoji = _fmt_status_emoji(result)
            print(f"\n{status_emoji}  Status: {result.get('status', '?')}")
            print(_fmt_causal_ctx(result))
            print(_fmt_signal(result))

            if result.get("risk_score") is not None:
                print(f"  🛡️  Risk score: {result['risk_score']:.2f}")
            if result.get("reason"):
                print(f"  💬  {result['reason']}")
            if result.get("executed"):
                print(f"  ✅  Executed on {result['symbol']}")
            print()

    if args.json:
        for entry in outputs:
            print(json.dumps(entry, default=str))
    else:
        print(f"\n{'='*60}")
        print(f"  DONE — {len(outputs)} symbol(s)")
        for entry in outputs:
            emoji = _fmt_status_emoji(entry)
            sym = entry.get("symbol", "?")
            status = entry.get("status", "?")
            sig = entry.get("signal", {})
            bias = sig.get("bias", "-") if sig else "-"
            print(f"  {emoji} {sym}: {status} ({bias})")
        print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
