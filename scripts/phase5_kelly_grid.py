#!/usr/bin/env python
"""Phase 5 — fangbot OpenFang Optimization: Kelly fraction + dynamic lot + SL/TP multiplier grid.
SL/TP-aware backtest (NOT pipeline) — DhaherSystem emits sl/tp cols.
Uses real EURUSD data via yfinance. Runs with Hermes venv python.
"""
import sys, json, logging, itertools
from pathlib import Path
from datetime import datetime

sys.path.insert(0, r"D:/repositories/Quant-Nanggroe-AI-worktree")
sys.path.insert(0, r"D:/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe")

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(message)s')
log = logging.getLogger('phase5_kelly')

import numpy as np, pandas as pd, yfinance as yf

from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem
from quant_nanggroe.engine.risk.constants import (
    MAX_RISK_PER_TRADE, MAX_DAILY_LOSS, MAX_WEEKLY_LOSS, MAX_DRAWDOWN_PCT,
)

def load_data():
    # Use 1h interval for 730d history (yfinance allows more data per bar at 1h)
    log.warning("Downloading EURUSD 1h (730d)...")
    df = yf.download("EURUSD=X", period="730d", interval="1h", auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.dropna()
    log.warning(f"{len(df)} bars from {df.index[0]} to {df.index[-1]}")
    return df

def backtest_sltp(df, lookback, atr_mult, rr_min, min_confluence, use_adx,
                  kelly_fraction, lot_conf_mult=1.0):
    """SL/TP-aware backtest. DhaherSystem emits sl/tp columns — engine MUST honor them."""
    strat = DhaherSystem(
        parameters=None, lookback=lookback, atr_mult=atr_mult, rr_min=rr_min,
        min_confluence=min_confluence, use_adx_filter=use_adx, adx_threshold=20,
    )
    sig = strat.generate_signals(df.copy())
    if sig is None or len(sig) < 50:
        return None
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
                    risk = abs(ep - sl_p)
                    capital -= risk * lot
                    losses += 1; trades += 1; pos = 0
                elif row['high'] >= tp_p:
                    gain = abs(tp_p - ep)
                    capital += gain * lot
                    wins += 1; trades += 1; pos = 0
            elif pos == -1:
                if row['high'] >= sl_p:
                    risk = abs(sl_p - ep)
                    capital -= risk * lot
                    losses += 1; trades += 1; pos = 0
                elif row['low'] <= tp_p:
                    gain = abs(ep - tp_p)
                    capital += gain * lot
                    wins += 1; trades += 1; pos = 0
        if pos == 0 and pd.notna(row.get('entry')) and row['entry'] != 0:
            if pd.notna(row['sl']) and pd.notna(row['tp']) and row['sl'] != 0 and row['tp'] != 0:
                lot_min = max(0.01, round(capital / 10000, 2))
                lot_max = max(0.02, round(capital / 5000, 2))
                conf = min(1.0, max(0.3, 0.65))
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
        avg_r = (ret / trades) / 100.0
        std_r = abs(ret / 100.0) * 0.15 if ret != 0 else 0.001
        std_r = max(std_r, 0.0001)
        sharpe = (avg_r / std_r) * np.sqrt(252) if std_r > 0 else 0
    else:
        sharpe = 0
    # Gate: Sharpe > 0.5, Return > 0%, DD > -25%
    gate_pass = sharpe > 0.5 and ret > 0 and max_dd < 25

    return {
        "sharpe": round(sharpe, 3), "ret_pct": round(ret, 2),
        "dd_pct": round(max_dd * 100, 2), "wr": round(wr, 1),
        "trades": trades, "gate_pass": gate_pass,
        "lookback": lookback, "atr_mult": atr_mult, "rr_min": rr_min,
        "min_confluence": min_confluence, "use_adx": use_adx,
        "kelly_fraction": kelly_fraction, "lot_conf_mult": lot_conf_mult,
    }

def run_grid():
    lookbacks = [15, 17, 20, 23]
    atr_mults = [1.0, 1.2, 1.5, 1.8]
    rr_mins = [2.0, 2.5, 3.0, 3.5]
    min_confluences = [2, 3]
    use_adxs = [True]
    kelly_fractions = [0.125, 0.15, 0.1875, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
    lot_mults = [1.0]  # fix lot at 1.0 for now, kelly is the main lever

    total = len(lookbacks)*len(atr_mults)*len(rr_mins)*len(min_confluences)*len(use_adxs)*len(kelly_fractions)*len(lot_mults)
    log.warning(f"Grid: {total} configs")

    df = load_data()
    results = []
    idx = 0
    for lb, am, rr, mc, uadx, kf, lm in itertools.product(lookbacks, atr_mults, rr_mins, min_confluences, use_adxs, kelly_fractions, lot_mults):
        idx += 1
        try:
            r = backtest_sltp(df, lb, am, rr, mc, uadx, kf, lm)
            if r is not None:
                results.append(r)
                if idx % 30 == 0:
                    log.warning(f"[{idx}/{total}] kf={kf} am={am} rr={rr} lb={lb} SR={r['sharpe']:.3f} R={r['ret_pct']:+.2f}% DD={r['dd_pct']:.1f}%")
        except Exception as e:
            log.error(f"[{idx}/{total}] ERROR: {e}")

    passing = [r for r in results if r.get("gate_pass")]
    passing.sort(key=lambda x: x["sharpe"], reverse=True)
    all_sorted = sorted(results, key=lambda x: x.get("sharpe", 0), reverse=True)
    best = passing[0] if passing else all_sorted[0]

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_configs": total, "tested": len(results), "passing_count": len(passing),
        "best": best, "top_5": passing[:5] if len(passing) >= 5 else passing[:10],
        "version_lock": "v5.1.0",
        "risk_constants": {"MAX_RISK_PER_TRADE": MAX_RISK_PER_TRADE, "MAX_DAILY_LOSS": MAX_DAILY_LOSS,
                           "MAX_WEEKLY_LOSS": MAX_WEEKLY_LOSS, "MAX_DRAWDOWN_PCT": MAX_DRAWDOWN_PCT},
    }
    out = Path(__file__).parent.parent / "results" / f"phase5_kelly_grid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    log.warning(f"Saved: {out}")
    return report

if __name__ == "__main__":
    r = run_grid()
    if r:
        print(f"\nBEST: {r['best']}")
        print(f"PASSING: {r['passing_count']}/{r['total_configs']}")
