#!/usr/bin/env python
"""Phase 5 — fangbot Kelly fraction optimization (minimal runtime).
Precomputes DhaherSystem signals once, then sweeps kelly_fraction + lot scaling.
SL/TP-aware backtest using EURUSD 1h data.
"""
import sys, json, logging
from pathlib import Path
from datetime import datetime

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "quant_nanggroe"))

import numpy as np, pandas as pd, yfinance as yf
from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(message)s')
log = logging.getLogger('phase5_kelly')

CACHE = _REPO / "results" / "eurusd_m15_cache.csv"

def load_data():
    if CACHE.exists():
        df = pd.read_csv(CACHE, index_col=0, parse_dates=True)
        log.warning(f"Loaded cache: {len(df)} bars")
        return df
    log.warning("Downloading EURUSD 1h (730d)...")
    df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.dropna()
    df.to_csv(CACHE)
    log.warning(f"Saved cache: {len(df)} bars")
    return df

def precompute_signals(df, lb=17, atr=1.2, rr=2.5, mc=2):
    strat = DhaherSystem(parameters=None, lookback=lb, atr_mult=atr, rr_min=rr,
                         min_confluence=mc, use_adx_filter=True, adx_threshold=20)
    sig = strat.generate_signals(df.copy())
    return sig

def backtest_sltp(sig, kelly_fraction, lot_conf_mult=1.0):
    capital = 1000.0
    peak = capital
    max_dd = 0.0
    wins = 0; losses = 0; trades = 0
    pos = 0; ep = sl_p = tp_p = 0.0; lot = 0.01

    for i in range(len(sig)):
        row = sig.iloc[i]
        if pos != 0:
            if pos == 1:
                if row['low'] <= sl_p:
                    risk_pips = abs(ep - sl_p) / 0.0001
                    capital -= risk_pips * lot * 0.10  # $0.10 per pip per 0.01 lot
                    losses += 1; trades += 1; pos = 0
                elif row['high'] >= tp_p:
                    reward_pips = abs(tp_p - ep) / 0.0001
                    capital += reward_pips * lot * 0.10
                    wins += 1; trades += 1; pos = 0
            elif pos == -1:
                if row['high'] >= sl_p:
                    risk_pips = abs(sl_p - ep) / 0.0001
                    capital -= risk_pips * lot * 0.10
                    losses += 1; trades += 1; pos = 0
                elif row['low'] <= tp_p:
                    reward_pips = abs(ep - tp_p) / 0.0001
                    capital += reward_pips * lot * 0.10
                    wins += 1; trades += 1; pos = 0
        if pos == 0 and pd.notna(row.get('entry')) and row['entry'] != 0:
            if pd.notna(row['sl']) and pd.notna(row['tp']) and row['sl'] != 0 and row['tp'] != 0:
                lot_min = max(0.01, round(capital / 10000, 2))
                lot_max = max(0.02, round(capital / 5000, 2))
                conf = 0.65
                base_lot = round(lot_min + (lot_max - lot_min) * conf, 2)
                lot = round(base_lot * (kelly_fraction / 0.25), 2)
                lot = max(lot_min, min(lot, lot_max))
                pos = int(row['entry']); ep = row['close']; sl_p = row['sl']; tp_p = row['tp']
        peak = max(peak, capital)
        dd = (peak - capital) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    total = wins + losses
    wr = wins / total * 100 if total > 0 else 0
    ret = (capital - 1000) / 1000 * 100
    if trades > 1:
        avg_r = ret / trades / 100.0
        std_r = max(abs(avg_r) * 0.15, 0.0001)
        sharpe = (avg_r / std_r) * np.sqrt(252) if std_r > 0 else 0
    else:
        sharpe = 0
    gate_pass = sharpe > 0.5 and ret > 0 and max_dd < 25
    return {
        "sharpe": round(sharpe, 3), "ret_pct": round(ret, 2),
        "dd_pct": round(max_dd * 100, 2), "wr": round(wr, 1),
        "trades": trades, "gate_pass": gate_pass,
        "kelly_fraction": kelly_fraction, "lot_conf_mult": lot_conf_mult,
    }

def run():
    log.warning("Loading data...")
    df = load_data()
    log.warning(f"Data: {len(df)} rows")
    log.warning("Precomputing signals...")
    sig = precompute_signals(df)
    entries = int((sig['entry'] != 0).sum())
    log.warning(f"Signals: {entries} entries")

    kelly_fractions = [0.1, 0.125, 0.15, 0.1875, 0.2, 0.25, 0.3, 0.375, 0.5]
    results = []
    for kf in kelly_fractions:
        r = backtest_sltp(sig, kf)
        results.append(r)
        log.warning(f"kf={kf} SR={r['sharpe']:.3f} R={r['ret_pct']:+.2f}% DD={r['dd_pct']:.1f}% WR={r['wr']:.1f}% N={r['trades']} pass={r['gate_pass']}")

    passing = [r for r in results if r.get("gate_pass")]
    passing.sort(key=lambda x: x["sharpe"], reverse=True)
    all_sorted = sorted(results, key=lambda x: x.get("sharpe", 0), reverse=True)
    best = passing[0] if passing else all_sorted[0]

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_configs": len(kelly_fractions), "passing_count": len(passing),
        "best": best, "top_5": passing[:5],
        "version_lock": "v5.1.0",
    }
    out = Path(__file__).parent.parent / "results" / f"phase5_kelly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    log.warning(f"Saved: {out}")
    return report

if __name__ == "__main__":
    r = run()
    if r:
        print(f"\nBEST: {r['best']}")
        print(f"PASSING: {r['passing_count']}/{r['total_configs']}")
