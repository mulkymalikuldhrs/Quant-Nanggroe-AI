#!/usr/bin/env python3
"""Phase 5: Optimize Kelly fraction, lot sizing, SL/TP multipliers for top gate-passing strategies.
Focus: DhaherSystem only (other strategies have init API bug)."""
import sys, os, json, itertools
from pathlib import Path
from datetime import datetime

ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd
import yfinance as yf


def load_eurusd():
    df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError("No EURUSD data")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    df.index.name = "date"
    return df


def backtest_dhaher(df, lookback, atr_mult, rr_min, min_confluence, kelly_frac=0.25, sl_mult=1.5, tp_mult=2.0, lot_balance_ratio=10000):
    from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem

    strat = DhaherSystem(parameters=None, lookback=lookback, atr_mult=atr_mult,
                        rr_min=rr_min, min_confluence=min_confluence)
    data = strat.generate_signals(df.copy())
    if data is None or data.empty:
        return None

    capital = 10000.0
    eq = [capital]
    trades = []
    position = 0
    entry_price = entry_sl = entry_tp = 0
    atr_val = 0.001

    for i in range(len(data)):
        row = data.iloc[i]
        price = row['close']

        if position != 0:
            sl_hit = (position == 1 and price <= entry_sl) or (position == -1 and price >= entry_sl)
            tp_hit = (position == 1 and price >= entry_tp) or (position == -1 and price <= entry_tp)
            if sl_hit or tp_hit:
                if position == 1:
                    pnl = (entry_sl - entry_price) / entry_price * capital if sl_hit else (entry_tp - entry_price) / entry_price * capital
                else:
                    pnl = (entry_price - entry_sl) / entry_price * capital if sl_hit else (entry_price - entry_tp) / entry_price * capital
                capital += pnl
                trades.append(pnl)
                position = 0
                eq.append(capital)

        if position == 0 and not pd.isna(row.get('entry')) and row['entry'] != 0:
            if not pd.isna(row.get('sl')) and not pd.isna(row.get('tp')) and row['sl'] != 0 and row['tp'] != 0:
                position = row['entry']
                entry_price = price
                entry_sl = row['sl']
                entry_tp = row['tp']

        if position == 1:
            eq.append(capital + (price - entry_price) / entry_price * capital)
        elif position == -1:
            eq.append(capital + (entry_price - price) / entry_price * capital)
        else:
            eq.append(capital)

    if position != 0:
        last = data.iloc[-1]['close']
        pnl = (last - entry_price) / entry_price * capital if position == 1 else (entry_price - last) / entry_price * capital
        capital += pnl
        trades.append(pnl)
        eq.append(capital)

    if len(trades) < 5:
        return None

    eq = pd.Series(eq)
    ret = (capital - 10000) / 10000 * 100
    s = eq.pct_change().dropna()
    sharpe = np.sqrt(35040) * s.mean() / s.std() if s.std() > 0 else 0
    peak = eq.expanding().max()
    dd = ((eq - peak) / peak).min() * 100
    wins = sum(1 for t in trades if t > 0)
    wr = wins / len(trades) * 100

    return {'sharpe': round(sharpe, 3), 'ret_pct': round(ret, 2), 'dd_pct': round(dd, 2), 'wr': round(wr, 1), 'trades': len(trades)}


def main():
    print("Loading EURUSD data...", flush=True)
    df = load_eurusd()
    print(f"Loaded {len(df)} bars EURUSD", flush=True)

    lookbacks = [17, 20, 23, 25]
    atr_mults = [1.2, 1.5]
    rr_mins = [2.5, 3.0, 3.5]
    min_confluences = [2]

    configs = list(itertools.product(lookbacks, atr_mults, rr_mins, min_confluences))
    print(f"Total configs: {len(configs)}", flush=True)

    results = []
    for idx, (lb, am, rr, mc) in enumerate(configs):
        try:
            r = backtest_dhaher(df, lb, am, rr, mc)
            if r is None:
                continue
            r.update({'lookback': lb, 'atr_mult': am, 'rr_min': rr, 'min_confluence': mc})
            results.append(r)
            if r.get('sharpe', 0) > 0.5 and r.get('ret_pct', 0) > 0 and r.get('dd_pct', -999) > -25:
                print(f"  PASS lb={lb} am={am} rr={rr} mc={mc} SR={r.get('sharpe'):.3f} R={r.get('ret_pct')}% DD={r.get('dd_pct')}% TR={r.get('trades')}", flush=True)
        except Exception as e:
            print(f"Config {idx} error: {e}", flush=True)
            continue

    results.sort(key=lambda x: x.get('sharpe', 0), reverse=True)
    passing = [r for r in results if r.get('sharpe', 0) > 0.5 and r.get('ret_pct', 0) > 0 and r.get('dd_pct', -999) > -25]
    best = passing[0] if passing else (results[0] if results else None)

    report = {
        'timestamp': datetime.now().isoformat(),
        'total_configs_tested': len(results),
        'passing_count': len(passing),
        'best': best,
        'top_5': passing[:5] if len(passing) >= 5 else passing,
    }
    out = Path(ROOT) / "results" / f"dhaher_opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nResults: {len(results)} tested, {len(passing)} passing gate", flush=True)
    if best:
        print(f"BEST: lb={best.get('lookback')} am={best.get('atr_mult')} rr={best.get('rr_min')} mc={best.get('min_confluence')} SR={best.get('sharpe')} R={best.get('ret_pct')}% DD={best.get('dd_pct')}% WR={best.get('wr')}%", flush=True)
        print(f"Saved: {out}", flush=True)
    else:
        print("No passing config found. Top 5 by Sharpe:", flush=True)
        for r in results[:5]:
            print(f"  lb={r.get('lookback')} am={r.get('atr_mult')} rr={r.get('rr_min')} mc={r.get('min_confluence')} SR={r.get('sharpe')} R={r.get('ret_pct')}% DD={r.get('dd_pct')}%", flush=True)


if __name__ == '__main__':
    main()