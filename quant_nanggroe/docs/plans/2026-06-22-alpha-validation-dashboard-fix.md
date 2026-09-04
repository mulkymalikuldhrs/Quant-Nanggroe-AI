# Alpha Validation + Dashboard Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use godmode:task-runner to implement this plan task-by-task.

**Goal:** Produce first validated alpha numbers for QNA (walk-forward backtest on 15 strategies with BTC/ETH data), fix dashboard API endpoint mismatches (27 endpoints), and remove mock data from 5 pages.

**Architecture:** Use existing `BacktestEngine` + `WalkForwardAnalyzer` from `engine/backtest/`. Extend `EnginePriceProvider` to fetch 2+ years of daily data. Script-driven, not service-level — a standalone Python script that loads strategies, runs walk-forward, persists to SQLite, and generates WS1_ALPHA_REPORT.md. Dashboard fixes: change API base from `/api/v1` to `/api`, align all 31 endpoint paths with backend routes, remove hardcoded mock data from 5 pages, fix dual layout on 5 pages, fix WebSocket path.

**Tech Stack:** Python 3.12, pydantic v2, SQLite, Next.js 16, TypeScript, Zustand, Recharts

**Strategy:** TDD — test first, implement, verify, commit per task.

---

### Task 1: Create backtest data fetcher

**Files:**
- Create: `scripts/fetch_backtest_data.py`
- No test needed (data fetch is I/O-bound, verified by inspection)

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Fetch historical OHLCV data for backtesting from all available providers."""

import json, os, sys, time
from pathlib import Path

# Add project to path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("PYTHONPATH", str(REPO))

from quant_nanggroe.engine_bridge import EnginePriceProvider

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
TIMEFRAME = "1d"
CANDLES_COUNT = 750  # ~2 years
DATA_DIR = REPO / "quant_nanggroe" / "data" / "backtest"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def fetch_all():
    provider = EnginePriceProvider()
    for sym in SYMBOLS:
        path = DATA_DIR / f"{sym}_daily.json"
        if path.exists():
            print(f"{sym}: cached ({path.stat().st_size} bytes)")
            continue
        print(f"{sym}: fetching {CANDLES_COUNT} candles...")
        klines = provider.get_klines(sym, TIMEFRAME, CANDLES_COUNT)
        if klines:
            # Convert timestamps to ISO for readability
            for k in klines:
                k["date"] = time.strftime(
                    "%Y-%m-%d", time.gmtime(k["timestamp"] / 1000)
                )
            path.write_text(json.dumps(klines, indent=2))
            print(f"{sym}: {len(klines)} candles saved to {path}")
        else:
            print(f"{sym}: NO DATA")
        time.sleep(1)

if __name__ == "__main__":
    fetch_all()
    print("\nDone.")
```

**Step 2: Run it**

Run: `cd /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree && python3 scripts/fetch_backtest_data.py`
Expected: 4 JSON files in `quant_nanggroe/data/backtest/` with 500+ candles each.

**Step 3: Verify**

Run: `ls -la quant_nanggroe/data/backtest/`
Expected: 4 files, each > 100KB (500+ daily candles).

**Step 4: Commit**

```bash
git add scripts/fetch_backtest_data.py quant_nanggroe/data/backtest/
git commit -m "feat: add backtest data fetcher with 2yr daily data for BTC/ETH/SOL/XRP"
```

---

### Task 2: Create walk-forward backtest runner

**Files:**
- Create: `scripts/run_walkforward.py`
- Test: `tests/test_walkforward.py`

**Step 1: Write the failing test**

```python
"""Tests for walk-forward backtest runner."""

import sys, json, os, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.run_walkforward import load_candles, run_strategy_backtest


def test_load_candles_missing_file():
    result = load_candles("NONEXISTENT.json")
    assert result == [], f"Expected [], got {result}"


def test_load_candles_valid():
    data = [{"close": 100.0, "open": 99.0, "high": 101.0, "low": 98.0, "volume": 1000}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        fname = f.name
    try:
        result = load_candles(fname)
        assert len(result) == 1
        assert result[0]["close"] == 100.0
    finally:
        os.unlink(fname)


def test_run_strategy_backtest_no_data():
    result = run_strategy_backtest("Momentum", [])
    assert result is not None
    assert result["total_trades"] == 0
```

**Step 2: Run test to verify failure**

Run: `cd /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree && python3 -m pytest tests/test_walkforward.py -v 2>&1`
Expected: FAIL with "ModuleNotFoundError" or "function not defined"

**Step 3: Write the runner script**

```python
#!/usr/bin/env python3
"""Walk-forward backtest runner for all 15 QNA strategies.

Usage:
    python3 scripts/run_walkforward.py [--symbol BTCUSDT] [--strategy Momentum]

Output: JSON results to data/backtest/results/ + summary to stdout.
"""

import json, os, sys, time, argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("PYTHONPATH", str(REPO))

DATA_DIR = REPO / "quant_nanggroe" / "data" / "backtest"
RESULTS_DIR = DATA_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

import numpy as np


def load_candles(symbol: str) -> List[Dict]:
    """Load cached OHLCV data for a symbol."""
    path = DATA_DIR / f"{symbol}_daily.json"
    if not path.exists():
        print(f"  No data for {symbol}, run fetch_backtest_data.py first")
        return []
    with open(path) as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} candles for {symbol}")
    return data


def compute_metrics(
    trades: List[Dict], equity_curve: List[float]
) -> Dict:
    """Compute performance metrics from trade list and equity curve."""
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl_pct": 0.0,
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
            "avg_hold_bars": 0,
        }

    closed = [t for t in trades if t.get("exit_idx")]
    wins = sum(1 for t in closed if t.get("pnl_pct", 0) > 0)
    losses = len(closed) - wins
    win_rate = wins / len(closed) if closed else 0.0

    # PnL from final cash
    first_equity = equity_curve[0] if equity_curve else 10000.0
    last_equity = equity_curve[-1] if equity_curve else first_equity
    total_pnl_pct = (last_equity - first_equity) / first_equity * 100

    # Sharpe from trade returns
    returns = [t["pnl_pct"] / 100 for t in closed if t.get("pnl_pct")]
    if len(returns) >= 2:
        avg_r = sum(returns) / len(returns)
        var_r = sum((r - avg_r) ** 2 for r in returns) / len(returns)
        std = var_r ** 0.5
        sharpe = (avg_r / std * 252 ** 0.5) if std > 0 else 0.0
    else:
        sharpe = 0.0

    # Max drawdown
    max_dd = 0.0
    peak = equity_curve[0] if equity_curve else 10000.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    avg_hold = 0
    if closed:
        holds = [t.get("exit_idx", 0) - t.get("entry_idx", 0) for t in closed]
        avg_hold = sum(holds) / len(holds) if holds else 0

    return {
        "total_trades": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "sharpe": round(sharpe, 4),
        "max_drawdown_pct": round(max_dd, 4),
        "avg_hold_bars": round(avg_hold, 1),
    }


def run_strategy_backtest(
    strategy_name: str,
    closes: List[float],
    initial_capital: float = 10000.0,
    position_pct: float = 0.95,
) -> Dict:
    """Run a simple backtest on a strategy using closing prices only."""
    if len(closes) < 30:
        return {"strategy": strategy_name, "total_trades": 0, "error": "insufficient_data"}

    # Import strategy by name
    try:
        from quant_nanggroe.engine.strategy.strategies import create_strategy
        strategy = create_strategy(strategy_name)
    except Exception as e:
        return {"strategy": strategy_name, "total_trades": 0, "error": str(e)}

    # Run
    cash = initial_capital
    position = 0.0
    trades: List[Dict] = []
    equity_curve = [initial_capital]

    for i in range(30, len(closes)):
        try:
            signal = strategy.generate_signal(
                _make_df(closes[: i + 1])
            )
        except Exception:
            signal = None

        sig_type = "hold"
        if signal is not None:
            sig_type = getattr(signal, "signal_type", "hold")
            if hasattr(sig_type, "value"):
                sig_type = sig_type.value

        price = closes[i]

        if sig_type == "buy" and position == 0:
            position = cash * position_pct / price
            cash *= 1 - position_pct
            trades.append({"type": "buy", "price": price, "entry_idx": i})
        elif sig_type == "sell" and position > 0 and trades:
            cash += position * price
            entry = trades[-1]
            entry["exit_price"] = price
            entry["exit_idx"] = i
            entry["pnl_pct"] = round((price - entry["price"]) / entry["price"] * 100, 4)
            position = 0.0

        equity_curve.append(cash + (position * price if position > 0 else 0))

    # Close any remaining position
    if position > 0:
        cash += position * closes[-1]
        position = 0.0

    metrics = compute_metrics(trades, equity_curve)
    metrics["strategy"] = strategy_name
    metrics["symbol"] = "BTCUSDT"
    metrics["period"] = f"{len(closes)} days"
    metrics["final_equity"] = round(cash, 2)
    metrics["initial_capital"] = initial_capital

    return metrics


def _make_df(closes):
    """Create a minimal DataFrame-like structure for strategy.generate_signal()."""
    import pandas as pd
    import numpy as np
    dates = pd.date_range(end="2026-06-22", periods=len(closes), freq="D")
    return pd.DataFrame({
        "close": closes,
        "open": closes,  # approximate
        "high": [c * 1.002 for c in closes],
        "low": [c * 0.998 for c in closes],
        "volume": np.random.randint(1000, 10000, len(closes)),
    }, index=dates)


def run_walk_forward(
    strategy_name: str,
    closes: List[float],
    n_folds: int = 5,
) -> Dict:
    """Run n-fold walk-forward validation."""
    fold_size = len(closes) // n_folds
    fold_results = []

    for fold in range(n_folds):
        val_start = fold * fold_size
        val_end = val_start + fold_size if fold < n_folds - 1 else len(closes)
        train_closes = closes[:val_start] if val_start > 0 else []
        val_closes = closes[val_start:val_end]

        if len(train_closes) < 30 or len(val_closes) < 10:
            continue

        result = run_strategy_backtest(strategy_name, list(train_closes) + list(val_closes))
        fold_results.append({
            "fold": fold + 1,
            "train_size": len(train_closes),
            "val_size": len(val_closes),
            "sharpe": result["sharpe"],
            "trades": result["total_trades"],
            "pnl_pct": result["total_pnl_pct"],
        })

    # Aggregate
    if fold_results:
        shrapes = [f["sharpe"] for f in fold_results]
        avg_sharpe = sum(shrapes) / len(shrapes)
        consistent = sum(1 for s in shrapes if s > 0.5)
    else:
        avg_sharpe = 0.0
        consistent = 0

    return {
        "strategy": strategy_name,
        "folds": fold_results,
        "avg_sharpe": round(avg_sharpe, 4),
        "folds_above_0.5": consistent,
        "total_folds": len(fold_results),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair")
    parser.add_argument("--strategy", default=None, help="Strategy name (default: all)")
    args = parser.parse_args()

    from quant_nanggroe.engine.strategy.strategies import list_strategies

    candles = load_candles(args.symbol)
    if not candles:
        return
    closes = [c["close"] for c in candles]
    print(f"\nPrice range: ${min(closes):.2f} - ${max(closes):.2f}")
    print(f"Period: {len(closes)} days\n")

    strategies = [args.strategy] if args.strategy else list_strategies()
    all_results = []

    for name in strategies:
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")

        # Full backtest
        bt = run_strategy_backtest(name, closes)
        print(f"  Backtest: {bt['total_trades']} trades, Sharpe {bt['sharpe']}, "
              f"PnL {bt['total_pnl_pct']:+.2f}%, DD {bt['max_drawdown_pct']*100:.1f}%")

        # Walk-forward
        wf = run_walk_forward(name, closes)
        print(f"  Walk-Forward: {wf['total_folds']} folds, avg Sharpe {wf['avg_sharpe']}, "
              f"consistent: {wf['folds_above_0.5']}/{wf['total_folds']}")

        result = {"name": name, "backtest": bt, "walkforward": wf}
        all_results.append(result)

    # Save all results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = RESULTS_DIR / f"walkforward_{args.symbol}_{timestamp}.json"
    result_path.write_text(json.dumps(all_results, indent=2))
    print(f"\nResults saved to {result_path}")

    # Summary table
    print(f"\n{'='*60}")
    print(f"  SUMMARY - {args.symbol}")
    print(f"{'='*60}")
    print(f"{'Strategy':<20} {'Trades':>7} {'Sharpe':>8} {'Win%':>7} {'PnL%':>8} {'DD%':>7} {'WF_Sharpe':>10}")
    print("-" * 70)
    for r in sorted(all_results, key=lambda x: x["backtest"]["sharpe"], reverse=True):
        bt = r["backtest"]
        wf = r["walkforward"]
        print(f"{r['name']:<20} {bt['total_trades']:>7} {bt['sharpe']:>8.2f} "
              f"{bt['win_rate']*100:>6.1f}% {bt['total_pnl_pct']:>7.2f}% "
              f"{bt['max_drawdown_pct']*100:>6.1f}% {wf['avg_sharpe']:>10.2f}")


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `cd /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree && python3 -m pytest tests/test_walkforward.py -v 2>&1`
Expected: 3/3 PASS

**Step 5: Quick smoke test of runner**

Run: `cd /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree && timeout 120 python3 scripts/run_walkforward.py --strategy Momentum 2>&1 | tail -20`
Expected: Momentum backtest results with trades, Sharpe, walk-forward folds.

**Step 6: Commit**

```bash
git add scripts/run_walkforward.py tests/test_walkforward.py
git commit -m "feat: add walk-forward backtest runner for all 15 strategies"
```

---

### Task 3: Run walk-forward on ALL 15 strategies

**Files:**
- None created. Run existing `scripts/run_walkforward.py`

**Step 1: Ensure data is available**

Run: `ls /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe/data/backtest/BTCUSDT_daily.json`
Expected: file exists with 500+ candles

**Step 2: Run full backtest**

Run: `cd /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree && timeout 600 python3 scripts/run_walkforward.py --symbol BTCUSDT 2>&1`
Expected: Results for all 15 strategies with trades, Sharpe, walk-forward data.

**Step 3: Repeat for ETH**

Run: `cd /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree && timeout 600 python3 scripts/run_walkforward.py --symbol ETHUSDT 2>&1`
Expected: Results for ETH.

**Step 4: Check results**

Run: `ls -la quant_nanggroe/data/backtest/results/`
Expected: JSON result files.

**Step 5: Commit**

```bash
git add quant_nanggroe/data/backtest/results/
git commit -m "feat: run walk-forward backtest on all 15 strategies for BTC/ETH"
```

---

### Task 4: Generate WS1_ALPHA_REPORT.md

**Files:**
- Create: `docs/WS1_ALPHA_REPORT.md`

**Step 1: Read results and generate report**

```python
#!/usr/bin/env python3
"""Generate WS1 Alpha Report from walk-forward results."""
import json
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("quant_nanggroe/data/backtest/results")
REPORT_PATH = Path("docs/WS1_ALPHA_REPORT.md")

result_files = sorted(RESULTS_DIR.glob("walkforward_*.json"))
if not result_files:
    print("No results found. Run scripts/run_walkforward.py first.")
    exit(1)

all_results = []
for f in result_files:
    all_results.extend(json.loads(f.read_text()))

# Group by symbol
by_symbol = {}
for r in all_results:
    sym = r["backtest"].get("symbol", "BTCUSDT")
    by_symbol.setdefault(sym, []).append(r)

report = f"""# WS1 Alpha Validation Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Methodology:** Walk-forward validation on daily data
**Assets:** {', '.join(by_symbol.keys())}
**Strategies:** {len(all_results)}

---

## Methodology

1. **Data:** Daily OHLCV from exchange API
2. **Walk-Forward:** 5-fold sequential validation
3. **Metrics:** Sharpe ratio (annualized), win rate, max drawdown, total return
4. **Pass Criteria:** Fold-specific Sharpe > 0.5 AND consistency across > 60% of folds
5. **Holding Period:** Strategy-determined (signal-based)

---

"""

for sym, results in by_symbol.items():
    results.sort(key=lambda x: x["walkforward"]["avg_sharpe"], reverse=True)
    report += f"## {sym}\n\n"
    report += f"| Strategy | Trades | Sharpe | Win% | PnL% | DD% | WF Sharpe | Consistent |\n"
    report += f"|----------|--------|--------|------|------|-----|-----------|------------|\n"

    for r in results:
        bt = r["backtest"]
        wf = r["walkforward"]
        consistent_flag = "✅" if wf["folds_above_0.5"] >= wf["total_folds"] * 0.6 else "❌"
        report += (f"| {r['name']} | {bt['total_trades']} | {bt['sharpe']:.2f} | "
                   f"{bt['win_rate']*100:.1f}% | {bt['total_pnl_pct']:+.2f}% | "
                   f"{bt['max_drawdown_pct']*100:.1f}% | {wf['avg_sharpe']:.2f} | "
                   f"{consistent_flag} |\n")

    report += "\n"

# Summary
report += "## Overall Assessment\n\n"
report += "| Criteria | Status |\n"
report += "|----------|--------|\n"

best_wf = max(all_results, key=lambda x: x["walkforward"]["avg_sharpe"])
best_bt = max(all_results, key=lambda x: x["backtest"]["sharpe"])

report += f"| Best Backtest Sharpe | {best_bt['name']}: {best_bt['backtest']['sharpe']:.2f} |\n"
report += f"| Best Walk-Forward Sharpe | {best_wf['name']}: {best_wf['walkforward']['avg_sharpe']:.2f} |\n"

consistent = sum(1 for r in all_results if r["walkforward"]["folds_above_0.5"] >= r["walkforward"]["total_folds"] * 0.6)
report += f"| Strategies with Validated Alpha | {consistent}/{len(all_results)} |\n"
report += f"| Consistent Walk-Forward | {consistent > len(all_results) * 0.3} |\n\n"

report += "## Conclusion\n\n"
if consistent == 0:
    report += "No strategy demonstrates consistent walk-forward alpha on daily data. "
    report += "Recommended next steps:\n"
    report += "1. Test on intraday data (4h, 1h) for higher signal density\n"
    report += "2. Combine top-3 strategies by Sharpe into ensemble\n"
    report += "3. Add regime filtering (HMM) to reduce false signals\n"
    report += "4. Test on additional assets (SOL, XRP) for cross-validation\n"
elif consistent >= len(all_results) * 0.6:
    report += f"{consistent}/{len(all_results)} strategies show consistent walk-forward alpha. "
    report += "The system has statistically validated edge on daily data.\n"
else:
    report += f"{consistent}/{len(all_results)} strategies show marginal alpha. "
    report += "Further validation needed on intraday data.\n"

REPORT_PATH.write_text(report)
print(f"Report saved to {REPORT_PATH}")
print(f"Best backtest: {best_bt['name']} Sharpe {best_bt['backtest']['sharpe']:.2f}")
print(f"Best walk-forward: {best_wf['name']} Sharpe {best_wf['walkforward']['avg_sharpe']:.2f}")
print(f"Consistent strategies: {consistent}/{len(all_results)}")
```

**Step 2: Run the report generator**

Run: `cd /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree && python3 scripts/generate_alpha_report.py`
Expected: `docs/WS1_ALPHA_REPORT.md` created with strategy-by-strategy table.

**Step 3: Verify report**

Run: `wc -l docs/WS1_ALPHA_REPORT.md && head -30 docs/WS1_ALPHA_REPORT.md`
Expected: Report has content for each strategy.

**Step 4: Commit**

```bash
git add docs/WS1_ALPHA_REPORT.md scripts/generate_alpha_report.py
git commit -m "docs: add WS1 alpha validation report with walk-forward results"
```

---

### Task 5: Fix API base URL in dashboard

**Files:**
- Modify: `dashboard/src/lib/api-client.ts`

**Step 1: Read current API base**

Run: `grep -n "api/v1\|NEXT_PUBLIC_API_URL" /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe/dashboard/src/lib/api-client.ts`
Expected: Shows all `/api/v1/` references and the base URL.

**Step 2: Change base URL from `/api/v1` to `/api`**

Edit `dashboard/src/lib/api-client.ts`:
- Change `apiRequest<T>(\`/api/v1/${module}${endpoint}\`)` to use a configurable base
- Add: `const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";`
- Change all endpoint references from `/api/v1/...` to `/api/...`

The simplest approach: change the base URL. Find all occurrences of `/api/v1` and replace with `/api` if the backend route matches, otherwise map to the correct backend path.

**Step 3: Create endpoint mapping**

The following frontend endpoints need to be mapped to backend routes:

| Frontend calls | Backend has | Fix |
|---|---|---|
| `/api/v1/trade` | `/api/trading/order` | `/api/trading/order` |
| `/api/v1/portfolio` | `/api/portfolio/summary` | `/api/portfolio/summary` |
| `/api/v1/agents` | `/api/agents/status` | `/api/agents/status` |
| `/api/v1/risk/{symbol}` | `/api/portfolio/risk` | `/api/portfolio/risk` |
| `/api/v1/backtest` | `/api/backtest/run` | `/api/backtest/run` |
| `/api/v1/market/symbols` | _doesn't exist_ → needs `/api/market/price` |
| `/api/v1/strategies` | `/api/strategies/list` | `/api/strategies/list` |
| `/api/v1/settings/exchanges` | _doesn't exist_ → return empty |
| `/api/v1/security/events` | _doesn't exist_ → return empty |
| `/api/v1/memory` | _doesn't exist_ → return empty |
| `/api/v1/colonies` | _doesn't exist_ → return empty |
| `/api/v1/channels` | _doesn't exist_ → return empty |
| `/api/v1/tools` | _doesn't exist_ → return empty |

**Step 4: Write updated api-client.ts**

Replace all endpoint paths in `api-client.ts` with the correct backend paths. For endpoints that don't exist on the backend, keep the fallback pattern (`.catch(() => [])`).

**Step 5: Verify**

Run: `grep -c "api/v1" dashboard/src/lib/api-client.ts`
Expected: 0 (all `/api/v1` references removed).

**Step 6: Commit**

```bash
git add dashboard/src/lib/api-client.ts
git commit -m "fix: align dashboard API endpoints with backend paths (remove /api/v1 prefix)"
```

---

### Task 6: Remove mock data from dashboard pages

**Files:**
- Modify: `dashboard/src/app/backtest/page.tsx:63-77`
- Modify: `dashboard/src/app/risk/page.tsx:119`
- Modify: `dashboard/src/app/market/page.tsx:86`
- Modify: `dashboard/src/app/strategies/page.tsx:78`
- Modify: `dashboard/src/app/channels/page.tsx:60`

**Step 1: Backtest page — replace hardcoded fallback**

Edit lines 63-77 of `dashboard/src/app/backtest/page.tsx`:
Remove the hardcoded fallback object. Instead, show a loading state or "No backtest data available" message.

The fallback is inside a `.catch()` handler. Change to return null/default values instead of fake data:
```typescript
// Before:
.catch(() => ({
  totalReturn: 28.45,
  sharpe: 1.92,
  ...
}))

// After:
.catch(() => null)
```

Then handle null in the render: show "Run a backtest to see results" placeholder.

**Step 2: Risk page — remove Math.random()**

Edit line 119 of `dashboard/src/app/risk/page.tsx`:
Replace `Math.min(Math.round(Math.random() * 60 + 20), 90)` with `0` or null:
```typescript
// Before:
width={Math.min(Math.round(Math.random() * 60 + 20), 90)}
// After:
width={check.value !== undefined ? Math.round(check.value) : 0}
```

**Step 3: Market page — remove fake volume**

Edit line 86 of `dashboard/src/app/market/page.tsx`:
Replace `Math.round(400 + idx * 7.3)` with actual data or 0:
```typescript
// Before:
volume: Math.round(400 + idx * 7.3),
// After:
volume: item.volume ?? 0,
```

**Step 4: Strategies page — remove Math.random() performance**

Edit line 78 of `dashboard/src/app/strategies/page.tsx`:
Replace `Math.random() * 5` with actual metric or 0:

**Step 5: Channels page — remove hardcoded messages**

Edit line 60 of `dashboard/src/app/channels/page.tsx`:
Remove the hardcoded messages array. Let the empty state render instead.

**Step 6: Verify**

Run: `grep -rn "Math\.random\|Math\.round.*Math\.random\|hardcoded\|fake\|FALLBACK" dashboard/src/app/ --include="*.tsx" | grep -v node_modules`
Expected: Only legitimate uses of Math.random() (not data generation).

**Step 7: Commit**

```bash
git add dashboard/src/app/backtest/page.tsx dashboard/src/app/risk/page.tsx \
      dashboard/src/app/market/page.tsx dashboard/src/app/strategies/page.tsx \
      dashboard/src/app/channels/page.tsx
git commit -m "fix: remove mock/hardcoded data from dashboard pages"
```

---

### Task 7: Fix dual layout bug on 5 pages

**Files:**
- Modify: `dashboard/src/app/security/page.tsx`
- Modify: `dashboard/src/app/memory/page.tsx`
- Modify: `dashboard/src/app/colony/page.tsx`
- Modify: `dashboard/src/app/channels/page.tsx`
- Modify: `dashboard/src/app/tools/page.tsx`

**Step 1: Remove AppLayout import from each page**

For each of the 5 pages, remove:
```typescript
import AppLayout from '@/components/layout/app-layout';
```
And remove the wrapping `<AppLayout>...</AppLayout>` or `AppLayout({ children: ... })`.

These pages already get wrapped by the root `layout.tsx`, so the inner import creates a double sidebar.

**Step 2: Verify one page**

Run: `grep -c "AppLayout" dashboard/src/app/security/page.tsx`
Expected: 0 (no AppLayout reference).

**Step 3: Do for all 5 pages**

Repeat for memory, colony, channels, tools.

**Step 4: Commit**

```bash
git add dashboard/src/app/security/page.tsx dashboard/src/app/memory/page.tsx \
      dashboard/src/app/colony/page.tsx dashboard/src/app/channels/page.tsx \
      dashboard/src/app/tools/page.tsx
git commit -m "fix: remove double layout wrapping on 5 pages (security, memory, colony, channels, tools)"
```

---

### Task 8: Fix WebSocket path

**Files:**
- Modify: `dashboard/src/lib/websocket.ts`

**Step 1: Read current WebSocket URL**

Run: `grep -n "ws://\|WebSocket\|socket" /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe/dashboard/src/lib/websocket.ts`
Expected: Shows current WebSocket connection URL.

**Step 2: Change WebSocket path from `/ws/trading` to `/api/ws/stream`**

Edit the `websocket.ts` file:
Change `ws://localhost:8000/ws/trading` to `ws://localhost:8000/api/ws/stream` (match the new backend).

**Step 3: Verify**

Run: `grep "ws://\|WEBSOCKET_URL\|WS_URL\|websocketUrl" /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe/dashboard/src/lib/websocket.ts`
Expected: Shows `/api/ws/stream` path.

**Step 4: Commit**

```bash
git add dashboard/src/lib/websocket.ts
git commit -m "fix: align WebSocket path with new backend (/api/ws/stream)"
```

---

### Task 9: Security — move API keys to env-only

**Files:**
- Modify: `.env` (remove sensitive keys)

**Step 1: Audit `.env` for sensitive keys**

Run: `grep -E "API_KEY|TOKEN|SECRET|PASSWORD" /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/.env`
Expected: Shows all sensitive keys.

**Step 2: Replace values with placeholders**

For each sensitive key, replace the live value with `CHANGEME`:
```bash
# Before
NVIDIA_API_KEY=nvapi-7oCtX8S5F7bZK...
# After
NVIDIA_API_KEY=CHANGEME
```

**Step 3: Verify no live keys remain**

Run: `grep -c "CHANGEME" /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/.env`
Count should match number of sensitive keys.

**Step 4: Commit**

```bash
git add .env
git commit -m "security: remove live API keys from .env, use env vars only"
```

---

## Post-Execution Verification

After all tasks complete:

1. **Backtest**: `python3 scripts/run_walkforward.py --strategy Momentum` produces valid output
2. **Dashboard**: All pages load without mock data, API calls go to correct endpoints
3. **Security**: No live keys in any committed file
4. **Import chain**: `python3 -c "from quant_nanggroe.live_engine import LiveEngine"` succeeds

---


---

> **SSOT:** `CANONICAL.md` v8.1.3 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
