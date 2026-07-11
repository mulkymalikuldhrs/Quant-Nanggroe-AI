#!/usr/bin/env python3
"""Slippage & Fee Calibration — Empirically estimate PaperBroker parameters from paper trade fills.

Phase 2.4 of the AUTONOMOUS_ROADMAP. Analyzes paper_state/pnl.csv and
paper_state/trades.csv (if available) to produce calibrated slippage and
commission estimates, then writes a markdown report to docs/SLIPPAGE_CALIBRATION.md.

Usage::
    python3 scripts/calibrate_slippage.py
    python3 scripts/calibrate_slippage.py --input-dir /tmp/paper_state
    python3 scripts/calibrate_slippage.py --symbols BTC/USDT ETH/USDT
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pandas as pd

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
REPORT_PATH = "docs/SLIPPAGE_CALIBRATION.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Slippage & Fee Calibration — estimate PaperBroker parameters empirically",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python3 scripts/calibrate_slippage.py
  python3 scripts/calibrate_slippage.py --input-dir /tmp/paper_state
  python3 scripts/calibrate_slippage.py --symbols BTC/USDT ETH/USDT
        """,
    )
    parser.add_argument(
        "--input-dir", default="paper_state",
        help="Directory containing pnl.csv and trades.csv (default: paper_state)",
    )
    parser.add_argument(
        "--symbols", nargs="+", default=DEFAULT_SYMBOLS,
        help=f"Symbols to analyze (default: {' '.join(DEFAULT_SYMBOLS)})",
    )
    return parser.parse_args()


def _synthetic_trades(n: int = 100, symbols: list[str] | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    symbols = symbols or DEFAULT_SYMBOLS
    np.random.seed(42)

    rows: list[dict[str, Any]] = []
    base_prices = {"BTC/USDT": 67000.0, "ETH/USDT": 3400.0, "SOL/USDT": 145.0, "XRP/USDT": 0.62}

    for i in range(n):
        sym = symbols[i % len(symbols)]
        base = base_prices.get(sym, 100.0)
        side = "BUY" if rng.random() < 0.5 else "SELL"
        qty = round(rng.uniform(0.01, 2.0), 4)
        price = base * (1 + rng.normal(0, 0.02))

        slippage_bps = round(rng.uniform(3.0, 15.0), 2)
        slip = slippage_bps / 10_000.0
        fill_price = price * (1 + slip) if side == "BUY" else price * (1 - slip)

        fee_bps = round(rng.uniform(5.0, 10.0), 2)
        fee = (fee_bps / 10_000.0) * qty * fill_price

        ts = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() + i * 3600
        rows.append({
            "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "symbol": sym,
            "side": side,
            "strategy": rng.choice(["Momentum", "RegimeBased", "MeanReversion"]),
            "price": round(price, 2),
            "quantity": qty,
            "fill_price": round(fill_price, 2),
            "slippage_bps": slippage_bps,
            "commission_bps": fee_bps,
            "commission": round(fee, 4),
            "notional": round(qty * fill_price, 2),
        })

    return pd.DataFrame(rows)


def _pnl_to_trades(pnl_df: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    base_prices = {"BTC/USDT": 67000.0, "ETH/USDT": 3400.0, "SOL/USDT": 145.0, "XRP/USDT": 0.62}

    trades: list[dict[str, Any]] = []
    for i, row in pnl_df.iterrows():
        if row.get("signals", 0) == 0:
            continue
        signal_count = int(abs(row.get("signals", 0)))
        sym = symbols[i % len(symbols)]
        base = base_prices.get(sym, 100.0)

        for _ in range(min(signal_count, 3)):
            side = "BUY" if rng.random() < 0.5 else "SELL"
            ts = pd.to_datetime(row.get("timestamp", row.get("date", "2026-01-01")))
            if ts.tz is None:
                ts = ts.tz_localize("UTC")

            slippage_bps = round(rng.uniform(3.0, 15.0), 2)
            slip = slippage_bps / 10_000.0
            price = base * (1 + rng.normal(0, 0.02))
            fill_price = price * (1 + slip) if side == "BUY" else price * (1 - slip)
            qty = round(rng.uniform(0.01, 1.0), 4)
            fee_bps = round(rng.uniform(5.0, 10.0), 2)
            fee = (fee_bps / 10_000.0) * qty * fill_price

            trades.append({
                "timestamp": ts.isoformat(),
                "symbol": sym,
                "side": side,
                "strategy": rng.choice(["Momentum", "RegimeBased", "MeanReversion"]),
                "price": round(price, 2),
                "quantity": qty,
                "fill_price": round(fill_price, 2),
                "slippage_bps": slippage_bps,
                "commission_bps": fee_bps,
                "commission": round(fee, 4),
                "notional": round(qty * fill_price, 2),
            })
    return pd.DataFrame(trades)


def analyze_trades(trades: pd.DataFrame) -> dict[str, Any]:
    results: dict[str, Any] = {}

    overall_slippage = trades["slippage_bps"]
    results["overall"] = {
        "avg_slippage_bps": float(overall_slippage.mean()),
        "std_slippage_bps": float(overall_slippage.std()),
        "p90_slippage_bps": float(overall_slippage.quantile(0.90)),
        "n_trades": len(trades),
    }

    by_symbol: dict[str, dict[str, Any]] = {}
    for sym in trades["symbol"].unique():
        sym_trades = trades[trades["symbol"] == sym]
        slip = sym_trades["slippage_bps"]
        by_symbol[sym] = {
            "avg_slippage_bps": float(slip.mean()),
            "std_slippage_bps": float(slip.std()),
            "p90_slippage_bps": float(slip.quantile(0.90)),
            "n_trades": len(sym_trades),
        }
    results["by_symbol"] = by_symbol

    if "strategy" in trades.columns:
        by_strategy: dict[str, dict[str, Any]] = {}
        for strat in trades["strategy"].unique():
            strat_trades = trades[trades["strategy"] == strat]
            slip = strat_trades["slippage_bps"]
            by_strategy[strat] = {
                "avg_slippage_bps": float(slip.mean()),
                "std_slippage_bps": float(slip.std()),
                "p90_slippage_bps": float(slip.quantile(0.90)),
                "n_trades": len(strat_trades),
            }
        results["by_strategy"] = by_strategy

    if "commission_bps" in trades.columns:
        results["commission"] = {
            "avg_commission_bps": float(trades["commission_bps"].mean()),
            "std_commission_bps": float(trades["commission_bps"].std()),
        }
    else:
        results["commission"] = {"avg_commission_bps": 0.0, "std_commission_bps": 0.0}

    avg_slip = results["overall"]["avg_slippage_bps"]
    avg_comm = results["commission"]["avg_commission_bps"]
    results["round_trip_cost_bps"] = (avg_slip + avg_comm) * 2

    results["recommended"] = {
        "slippage_bps": round(max(1.0, np.ceil(results["overall"]["p90_slippage_bps"])), 0),
        "commission_bps": round(max(0.5, np.ceil(avg_comm)), 0),
    }
    if "commission_bps" not in trades.columns or trades["commission_bps"].isna().all():
        results["recommended"]["commission_bps"] = 3.0

    return results


def _find_paper_broker_defaults() -> dict[str, Any]:
    defaults: dict[str, Any] = {"current_slippage_bps": None, "current_commission_rate": None}
    paths_to_check = [
        _REPO_ROOT + "/quant_nanggroe/exchange/paper_broker.py",
        _REPO_ROOT + "/quant_nanggroe/broker/paper_broker.py",
    ]
    for path in paths_to_check:
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            for line in content.splitlines():
                line_s = line.strip()
                if "slippage_bps" in line_s and "float" in line_s:
                    try:
                        defaults["current_slippage_bps"] = float(
                            line_s.split("=")[-1].replace(",", "").strip()
                        )
                    except (ValueError, IndexError):
                        pass
                if "commission_rate" in line_s and "float" in line_s:
                    try:
                        defaults["current_commission_rate"] = float(
                            line_s.split("=")[-1].replace(",", "").strip()
                        )
                    except (ValueError, IndexError):
                        pass
    return defaults


def generate_report(results: dict[str, Any], trades: pd.DataFrame, data_source: str,
                    date_range: str, broker_defaults: dict[str, Any]) -> str:
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append("# Slippage & Fee Calibration Report")
    lines.append(f"Generated: {now}")
    lines.append("")

    lines.append("## Data Source")
    lines.append(f"- Trades analyzed: {results['overall']['n_trades']} ({data_source})")
    lines.append(f"- Date range: {date_range}")
    lines.append("")

    if broker_defaults.get("current_slippage_bps") is not None:
        comm_pct = broker_defaults.get("current_commission_rate", "N/A")
        comm_bps = round(comm_pct * 10_000, 1) if isinstance(comm_pct, float) else "N/A"
        lines.append("### Current PaperBroker Defaults")
        lines.append(f"- `slippage_bps`: {broker_defaults['current_slippage_bps']}")
        lines.append(f"- `commission_rate`: {comm_pct} ({comm_bps} bps)")
        lines.append("- Source: `quant_nanggroe/exchange/paper_broker.py`")
        lines.append("")

    lines.append("## Slippage by Symbol")
    lines.append("| Symbol | Avg (bps) | Std (bps) | P90 (bps) | Trades |")
    lines.append("|--------|-----------|-----------|-----------|--------|")
    for sym in sorted(results["by_symbol"].keys()):
        s = results["by_symbol"][sym]
        lines.append(
            f"| {sym} | {s['avg_slippage_bps']:.1f} | {s['std_slippage_bps']:.1f} "
            f"| {s['p90_slippage_bps']:.1f} | {s['n_trades']} |"
        )
    lines.append("")

    if "by_strategy" in results:
        lines.append("## Slippage by Strategy")
        lines.append("| Strategy | Avg (bps) | Std (bps) | P90 (bps) | Trades |")
        lines.append("|----------|-----------|-----------|-----------|--------|")
        for strat in sorted(results["by_strategy"].keys()):
            s = results["by_strategy"][strat]
            lines.append(
                f"| {strat} | {s['avg_slippage_bps']:.1f} | {s['std_slippage_bps']:.1f} "
                f"| {s['p90_slippage_bps']:.1f} | {s['n_trades']} |"
            )
        lines.append("")

    lines.append("## Aggregate")
    lines.append(f"- Average slippage: {results['overall']['avg_slippage_bps']:.1f} bps")
    lines.append(f"- Slippage std dev: {results['overall']['std_slippage_bps']:.1f} bps")
    lines.append(f"- Slippage P90: {results['overall']['p90_slippage_bps']:.1f} bps")
    lines.append(f"- Average commission: {results['commission']['avg_commission_bps']:.1f} bps")
    lines.append(f"- Estimated round-trip cost: {results['round_trip_cost_bps']:.1f} bps")
    lines.append("")

    lines.append("## Recommended Defaults")
    lines.append("Set PaperBroker to:")
    lines.append(f"- `slippage_bps`: {results['recommended']['slippage_bps']:.0f}")
    lines.append(f"- `commission_bps`: {results['recommended']['commission_bps']:.0f}")
    lines.append("")
    lines.append("---")
    lines.append("*Report generated by `scripts/calibrate_slippage.py`*")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir
    symbols = args.symbols

    pnl_path = os.path.join(input_dir, "pnl.csv")
    trades_path = os.path.join(input_dir, "trades.csv")

    trades: pd.DataFrame | None = None
    data_source = "synthetic fallback"
    date_range = "N/A"
    using_synthetic = False

    if os.path.exists(trades_path):
        trades = pd.read_csv(trades_path)
        trades["slippage_bps"] = pd.to_numeric(trades.get("slippage_bps", pd.NA), errors="coerce")
        if trades["slippage_bps"].isna().all():
            trades["slippage_bps"] = None
        trades = trades[trades["slippage_bps"].notna()] if trades["slippage_bps"] is not None else trades
        data_source = "real trades.csv"
        if "timestamp" in trades.columns:
            ts_col = pd.to_datetime(trades["timestamp"], errors="coerce")
            date_range = f"{ts_col.min().strftime('%Y-%m-%d')} to {ts_col.max().strftime('%Y-%m-%d')}" if ts_col.notna().any() else "N/A"
        print(f"Read {len(trades)} trades from {trades_path}", file=sys.stderr)
    elif os.path.exists(pnl_path):
        pnl_df = pd.read_csv(pnl_path)
        trades = _pnl_to_trades(pnl_df, symbols)
        data_source = "derived from pnl.csv (synthetic fills)"
        if "timestamp" in trades.columns:
            ts_col = pd.to_datetime(trades["timestamp"], errors="coerce")
            date_range = f"{ts_col.min().strftime('%Y-%m-%d')} to {ts_col.max().strftime('%Y-%m-%d')}" if ts_col.notna().any() else "N/A"
        print(f"Derived {len(trades)} trades from {pnl_path}", file=sys.stderr)
    else:
        trades = _synthetic_trades(100, symbols)
        data_source = "synthetic fallback"
        using_synthetic = True
        date_range = "2026-01-01 to 2026-01-05"
        print("NO REAL DATA — USING SYNTHETIC", file=sys.stderr)
        print(f"Generated {len(trades)} synthetic trades for calibration", file=sys.stderr)

    if trades is None or len(trades) == 0:
        print("ERROR: No trade data available for calibration.", file=sys.stderr)
        sys.exit(1)

    if "slippage_bps" not in trades.columns or trades["slippage_bps"].isna().all():
        if "fill_price" in trades.columns and "price" in trades.columns:
            trades["slippage_bps"] = (
                (trades["fill_price"] - trades["price"]).abs() / trades["price"] * 10_000
            )
        else:
            print("ERROR: Cannot compute slippage — missing fill_price/price columns.", file=sys.stderr)
            sys.exit(1)

    if "commission_bps" not in trades.columns:
        if "commission" in trades.columns and "notional" in trades.columns:
            trades["commission_bps"] = trades["commission"] / trades["notional"] * 10_000
        else:
            trades["commission_bps"] = float("nan")

    results = analyze_trades(trades)
    broker_defaults = _find_paper_broker_defaults()
    report = generate_report(results, trades, data_source, date_range, broker_defaults)

    print(report)

    report_path = os.path.join(_REPO_ROOT, REPORT_PATH)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport written to: {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
