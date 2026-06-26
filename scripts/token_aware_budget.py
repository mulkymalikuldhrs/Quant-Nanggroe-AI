#!/usr/bin/env python3
"""Token-Aware Budget — cost-aware strategy signal execution filtering.

Phase 3.5 of the AUTONOMOUS_ROADMAP. For each strategy signal, estimate
execution cost vs expected signal value. Skip signals where cost exceeds
a strategy-specific tolerance threshold.

Usage:
    python3 scripts/token_aware_budget.py
    python3 scripts/token_aware_budget.py --symbols BTC/USDT,ETH/USDT
    python3 scripts/token_aware_budget.py --strategies Momentum,MeanReversion
    python3 scripts/token_aware_budget.py --min-ratio 2.5
    python3 scripts/token_aware_budget.py --status
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

N_SIGNALS = 200
STATE_PATH = os.path.join(_REPO_ROOT, "paper_state", "budget_state.json")
SLIPPAGE_DOC = os.path.join(_REPO_ROOT, "docs", "SLIPPAGE_CALIBRATION.md")

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]

STRATEGIES = [
    "MarketMaking",
    "MeanReversion",
    "Momentum",
    "PairsTrading",
    "VolatilityArbitrage",
    "StatisticalArbitrage",
    "RegimeBased",
    "CryptoSpecific",
]

STRATEGY_COST_TOLERANCE: Dict[str, float] = {
    "MarketMaking": 1.5,
    "MeanReversion": 1.5,
    "Momentum": 2.0,
    "PairsTrading": 2.0,
    "VolatilityArbitrage": 2.5,
    "StatisticalArbitrage": 2.5,
    "RegimeBased": 2.0,
    "CryptoSpecific": 3.0,
}

BASE_PRICES: Dict[str, float] = {
    "BTC/USDT": 67000.0,
    "ETH/USDT": 3400.0,
    "SOL/USDT": 145.0,
    "XRP/USDT": 0.62,
}

DEFAULT_SLIPPAGE: Dict[str, float] = {
    "BTC/USDT": 10.0,
    "ETH/USDT": 10.0,
    "SOL/USDT": 15.0,
    "XRP/USDT": 15.0,
}

DEFAULT_COMMISSION_BPS: float = 10.0


def load_slippage_defaults() -> Dict[str, float]:
    slippage: Dict[str, float] = dict(DEFAULT_SLIPPAGE)
    if not os.path.isfile(SLIPPAGE_DOC):
        return slippage
    try:
        with open(SLIPPAGE_DOC) as f:
            content = f.read()
        table_section = re.search(r"## Recommended Defaults\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if table_section:
            slip_match = re.search(r"`slippage_bps`:\s*([\d.]+)", table_section.group(1))
            comm_match = re.search(r"`commission_bps`:\s*([\d.]+)", table_section.group(1))
            if slip_match:
                fallback_slip = float(slip_match.group(1))
                for sym in slippage:
                    slippage[sym] = fallback_slip
            if comm_match:
                _ = float(comm_match.group(1))
        symbol_section = re.search(r"## Slippage by Symbol\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if symbol_section:
            for line in symbol_section.group(1).splitlines():
                parts = line.split("|")
                if len(parts) >= 4 and parts[1].strip() in slippage:
                    sym = parts[1].strip()
                    try:
                        slippage[sym] = float(parts[2].strip())
                    except (ValueError, IndexError):
                        pass
    except (OSError, Exception):
        logger.warning("Could not read %s, using defaults", SLIPPAGE_DOC)
    return slippage


def get_round_trip_cost(symbol: str, slippage: Dict[str, float], commission_bps: float) -> float:
    slip = slippage.get(symbol, DEFAULT_SLIPPAGE.get(symbol, 10.0))
    return 2.0 * (slip + commission_bps)


def confidence_to_expected_bps(confidence: float) -> float:
    return confidence * 200.0


def should_execute(
    expected_return_bps: float,
    cost_bps: float,
    min_ratio: float = 2.0,
) -> bool:
    if cost_bps <= 0:
        return True
    return expected_return_bps >= min_ratio * cost_bps


def get_strategy_tolerance(strategy: str) -> float:
    return STRATEGY_COST_TOLERANCE.get(strategy, 2.0)


def adjust_kelly(
    full_kelly: float,
    regime_multiplier: float,
    expected_return_bps: float,
    cost_bps: float,
) -> float:
    cost_penalty = min(1.0, cost_bps / (expected_return_bps + 1e-8))
    adjusted = full_kelly * regime_multiplier * (1.0 - cost_penalty)
    return max(0.0, min(1.0, adjusted))


def generate_signals(
    n: int = N_SIGNALS,
    symbols: Optional[List[str]] = None,
    strategies: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    rng = np.random.default_rng(42)
    syms = symbols or DEFAULT_SYMBOLS
    strats = strategies or STRATEGIES
    signals: List[Dict[str, Any]] = []
    for i in range(n):
        sym = syms[i % len(syms)]
        strat = strats[i % len(strats)]
        base = BASE_PRICES.get(sym, 100.0)
        price = base * (1.0 + rng.normal(0, 0.02))
        confidence = round(rng.uniform(0.1, 0.95), 4)
        signals.append({
            "strategy": strat,
            "symbol": sym,
            "price": round(price, 2),
            "confidence": confidence,
            "expected_return_bps": round(confidence_to_expected_bps(confidence), 1),
        })
    return signals


def budget_report(
    decisions: List[Dict[str, Any]],
    min_ratio: float,
    slippage: Dict[str, float],
    commission_bps: float,
) -> str:
    lines: List[str] = []
    lines.append("Token-Aware Budget Report")
    lines.append("=" * 60)
    lines.append(f"Min ratio: {min_ratio:.1f}x | Commission: {commission_bps:.0f} bps")
    lines.append("")

    by_combo: Dict[str, List[Dict[str, Any]]] = {}
    for d in decisions:
        key = f"{d['strategy']} / {d['symbol']}"
        by_combo.setdefault(key, []).append(d)

    for combo_key in sorted(by_combo):
        combos = by_combo[combo_key]
        agg = combos[-1]
        strat = agg["strategy"]
        sym = agg["symbol"]
        cost_bps = agg["cost_bps"]
        tolerance = get_strategy_tolerance(strat)

        lines.append(f"{strat} / {sym}:")
        for s in combos:
            lines.append(
                f"  Expected return: {s['expected_bps']:.1f} bps  "
                f"Cost: {s['cost_bps']:.1f} bps  "
                f"Ratio: {s['ratio']:.2f}x  "
                f"{'→ EXECUTE' if s['executed'] else '→ SKIP (need >='+str(tolerance)+'x)'}"
            )
            lines.append(f"  Kelly adj: {s['kelly_adj']:.3f}")
        lines.append("")

    executed = sum(1 for d in decisions if d["executed"])
    skipped = len(decisions) - executed
    total_cost = sum(d["cost_bps"] for d in decisions if d["executed"])
    lines.append(f"Summary: {executed} executed, {skipped} skipped")
    lines.append(f"Total round-trip cost of executed signals: {total_cost:.1f} bps")
    lines.append("=" * 60)
    return "\n".join(lines)


def save_budget_state(
    decisions: List[Dict[str, Any]],
    min_ratio: float,
    slippage: Dict[str, float],
    commission_bps: float,
) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    payload: Dict[str, Any] = {
        "version": 1,
        "min_ratio": min_ratio,
        "defaults": {
            "slippage": slippage,
            "commission_bps": commission_bps,
            "strategy_tolerance": STRATEGY_COST_TOLERANCE,
        },
        "decisions": decisions,
        "summary": {
            "total": len(decisions),
            "executed": sum(1 for d in decisions if d["executed"]),
            "skipped": sum(1 for d in decisions if not d["executed"]),
        },
    }
    with open(STATE_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info("Budget state saved to %s", STATE_PATH)


def load_budget_state() -> Dict[str, Any]:
    if not os.path.isfile(STATE_PATH):
        return {"decisions": [], "defaults": {}, "min_ratio": 2.0}
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"decisions": [], "defaults": {}, "min_ratio": 2.0}


def show_status() -> None:
    state = load_budget_state()
    decisions = state.get("decisions", [])
    summary = state.get("summary", {})
    defaults = state.get("defaults", {})
    min_ratio = state.get("min_ratio", 2.0)

    print("Token-Aware Budget — Status")
    print("=" * 50)
    print(f"Min ratio: {min_ratio:.1f}x")
    print(f"Commission: {defaults.get('commission_bps', 'N/A')} bps")
    print(f"Total decisions: {summary.get('total', len(decisions))}")
    print(f"Executed: {summary.get('executed', 0)}")
    print(f"Skipped: {summary.get('skipped', 0)}")
    print()

    if decisions:
        by_strat: Dict[str, int] = {}
        for d in decisions:
            strat = d["strategy"]
            by_strat[strat] = by_strat.get(strat, 0) + 1
        print("Per-strategy decision counts:")
        for strat in sorted(by_strat):
            print(f"  {strat}: {by_strat[strat]}")
    else:
        print("No decisions recorded. Run with --symbols/--strategies to generate.")


def run_budget(
    symbols: List[str],
    strategies: List[str],
    min_ratio: float,
) -> None:
    slippage = load_slippage_defaults()
    commission_bps = DEFAULT_COMMISSION_BPS

    signals = generate_signals(N_SIGNALS, symbols, strategies)

    decisions: List[Dict[str, Any]] = []
    for sig in signals:
        strat = sig["strategy"]
        sym = sig["symbol"]
        expected_bps = sig["expected_return_bps"]
        cost_bps = get_round_trip_cost(sym, slippage, commission_bps)

        effective_min_ratio = get_strategy_tolerance(strat)
        exec_flag = should_execute(expected_bps, cost_bps, effective_min_ratio)
        ratio = expected_bps / cost_bps if cost_bps > 0 else 999.0

        kelly_adj = 0.0
        if exec_flag:
            full_kelly = sig["confidence"] * 0.5
            kelly_adj = adjust_kelly(full_kelly, 1.0, expected_bps, cost_bps)

        decisions.append({
            "strategy": strat,
            "symbol": sym,
            "expected_bps": expected_bps,
            "cost_bps": round(cost_bps, 1),
            "ratio": round(ratio, 2),
            "executed": exec_flag,
            "kelly_adj": round(kelly_adj, 4),
        })

    report = budget_report(decisions, min_ratio, slippage, commission_bps)
    print(report)
    save_budget_state(decisions, min_ratio, slippage, commission_bps)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Token-Aware Budget — cost-aware signal execution filtering"
    )
    parser.add_argument(
        "--symbols", default=None,
        help="Comma-separated symbols (default: all)",
    )
    parser.add_argument(
        "--strategies", default=None,
        help="Comma-separated strategy names (default: all)",
    )
    parser.add_argument(
        "--min-ratio", type=float, default=2.0,
        help="Override minimum cost/signal ratio (default: 2.0)",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show last budget state",
    )
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else DEFAULT_SYMBOLS
    strategies = [s.strip() for s in args.strategies.split(",")] if args.strategies else STRATEGIES

    run_budget(symbols, strategies, args.min_ratio)


if __name__ == "__main__":
    main()
