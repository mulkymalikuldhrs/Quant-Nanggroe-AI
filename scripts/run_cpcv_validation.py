#!/usr/bin/env python3
"""CPCV validation — institutional PROVE pillar for top WF-admitted strategies.

Combinatorial Purged Cross-Validation (de Prado AFML Ch.12): evaluates across
ALL train/test group combinations (not a single path), with purge+embargo.
A strategy that survives CPCV has far stronger evidence than rolling-WF alone.

Usage:
  C:\\Python314\\python.exe scripts/run_cpcv_validation.py
  C:\\Python314\\python.exe scripts/run_cpcv_validation.py --only archive_aroon --symbols BTC-USD

Results -> data/cpcv_registry.json + console summary table.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import quant_nanggroe.engine.strategies  # noqa: F401
from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

# Top distinct-logic strategies from tri-asset rolling WF (CANONICAL 4.5)
DEFAULT_TARGETS = [
    "archive_aroon", "archive_amdx", "archive_algebra",
    "archive_mean_rev", "archive_ict_ote",
    "archive_gold_inflation", "archive_wyckoff",
    # live canonical admitted pair for comparison
    "kaufman_ama", "multi_timeframe",
]


def fetch(sym: str) -> pd.DataFrame | None:
    try:
        df = yf.download(sym, period="2y", interval="1d",
                         progress=False, auto_adjust=True)
    except Exception as e:
        print(f"  fetch {sym} failed: {e}")
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.dropna()
    return df if len(df) >= 325 else None


def _mean_or_none(vals: list) -> float | None:
    """Mean of vals, or None when no usable values (fail-soft, never fabricate)."""
    clean = [float(v) for v in vals if v is not None]
    if not clean:
        return None
    try:
        return round(sum(clean) / len(clean), 4)
    except Exception:
        return None


def build_cpcv_entry(sym: str, windows: list) -> dict:
    """Build one registry entry from analyzer windows (fail-soft).

    Existing keys are byte-identical to the pre-extension writer.
    New keys (win_rate/total_trades/avg_oos_return/max_oos_dd) are populated
    ONLY from fields actually present on the window objects; otherwise None.
    WalkForwardResult currently exposes oos_trades / out_of_sample_return /
    out_of_sample_max_dd but NO per-window win_rate, so win_rate is None
    until the analyzer pipeline propagates trade-level win rates.
    """
    sharpes = [float(w.out_of_sample_sharpe) for w in windows]
    n_combos = len(sharpes)
    pos = sum(1 for s in sharpes if s > 0)
    avg = sum(sharpes) / n_combos if n_combos else 0.0
    # de Prado robustness metric: share of profitable combos
    combo_share = pos / n_combos if n_combos else 0.0
    entry = {
        "symbol": sym, "n_combinations": n_combos,
        "profitable_combos": pos,
        "combo_profit_share": round(combo_share, 4),
        "avg_oos_sharpe": round(avg, 4),
        "min_sharpe": round(min(sharpes), 4) if sharpes else None,
        "max_sharpe": round(max(sharpes), 4) if sharpes else None,
    }
    # --- extended trade stats (fail-soft; None > invented) ---
    try:
        trade_counts = [getattr(w, "oos_trades", None) for w in windows]
        if trade_counts and all(isinstance(c, (int, float)) for c in trade_counts):
            entry["total_trades"] = int(sum(trade_counts))
        else:
            entry["total_trades"] = None
    except Exception:
        entry["total_trades"] = None
    try:
        rets = [getattr(w, "out_of_sample_return", None) for w in windows]
        if any(v is None or not isinstance(v, (int, float)) for v in rets) or not rets:
            entry["avg_oos_return"] = _mean_or_none(
                [v for v in rets if isinstance(v, (int, float))]) if rets else None
            if not rets:
                entry["avg_oos_return"] = None
        else:
            entry["avg_oos_return"] = _mean_or_none(rets)
    except Exception:
        entry["avg_oos_return"] = None
    try:
        dds = [getattr(w, "out_of_sample_max_dd", None) for w in windows]
        clean_dd = [float(v) for v in dds if isinstance(v, (int, float))]
        # max_dd <= 0 convention (drawdown.min): worst = most negative = min()
        entry["max_oos_dd"] = round(min(clean_dd), 4) if clean_dd else None
    except Exception:
        entry["max_oos_dd"] = None
    try:
        wrs = [getattr(w, o, None)
               for w in windows for o in ("win_rate", "oos_win_rate")]
        clean_wr = [float(v) for v in wrs if isinstance(v, (int, float))]
        entry["win_rate"] = round(sum(clean_wr) / len(clean_wr), 4) if clean_wr else None
    except Exception:
        entry["win_rate"] = None
    return entry


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=str, default="BTC-USD,EURUSD=X,GC=F")
    ap.add_argument("--only", type=str, default="")
    ap.add_argument("--n-groups", type=int, default=6)
    ap.add_argument("--n-test-groups", type=int, default=2)
    args = ap.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    targets = ([s.strip() for s in args.only.split(",") if s.strip()]
               if args.only else DEFAULT_TARGETS)

    engine = BacktestEngine(BacktestConfig(initial_capital=10000, commission_rate=0.001))
    analyzer = WalkForwardAnalyzer(
        engine=engine,
        train_window=252, test_window=63,
        mode="cpcv",                    # <- THE point of this script
        n_groups=args.n_groups, n_test_groups=args.n_test_groups,
        purge_gap=5, embargo=3,
    )

    out_path = ROOT / "data" / "cpcv_registry.json"
    registry: dict = {}
    if out_path.exists():
        try:
            registry = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            registry = {}

    results: list[dict] = []
    for sym in symbols:
        print(f"\n{'='*72}\nCPCV {sym}\n{'='*72}")
        df = fetch(sym)
        if df is None:
            print("  skipped (no data)")
            continue
        for name in targets:
            cls = StrategyRegistry.get(name)
            if cls is None:
                print(f"  SKIP {name} (not registered)")
                continue
            t0 = time.time()
            try:
                res = analyzer.analyze_strategy(prices=df, strategy_class=cls,
                                                 strategy_params={})
                windows = res.get("windows", [])
                entry = build_cpcv_entry(sym, windows)
                n_combos = entry["n_combinations"]
                pos = entry["profitable_combos"]
                combo_share = entry["combo_profit_share"]
                avg = entry["avg_oos_sharpe"]
                registry.setdefault(name, {})[sym] = entry
                results.append({"name": name, **entry})
                print(f"  {name}: {pos}/{n_combos} combos profitable "
                      f"({combo_share:.0%}) avg={avg:+.3f} [{time.time()-t0:.0f}s]")
            except Exception as e:
                print(f"  ERROR {name}: {e}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    # final ranking by weakest-link (min sharpe across symbols)
    print("\n=== CPCV ROBUSTNESS RANKING (survivor = min Sharpe > 0 across all symbols) ===")
    by_name: dict[str, list] = {}
    for r in results:
        by_name.setdefault(r["name"], []).append(r)
    ranked = []
    for name, rs in by_name.items():
        if len(rs) < len(symbols):
            continue  # must have every symbol
        mins = min(r["min_sharpe"] or 0 for r in rs)
        shares = [r["combo_profit_share"] for r in rs]
        avgs = [r["avg_oos_sharpe"] for r in rs]
        ranked.append((name, mins, sum(shares) / len(shares),
                       sum(avgs) / len(avgs)))
    ranked.sort(key=lambda t: t[1], reverse=True)
    for name, mn, share, avg in ranked:
        verdict = "SURVIVOR" if mn > 0 else "fragile"
        print(f"  {name:28s} worst-combo={mn:+.3f} "
              f"profit-share={share:.0%} avg={avg:+.3f}  [{verdict}]")
    print(f"\nregistry -> {out_path}")


if __name__ == "__main__":
    main()
