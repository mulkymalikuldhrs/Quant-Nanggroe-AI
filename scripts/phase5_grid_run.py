#!/usr/bin/env python
import sys, json, logging, itertools
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "quant_nanggroe"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("phase5")

# Real data
log.info("Downloading EURUSD=X M15 (60d)...")
df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df = df.dropna()
log.info(f"{len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")

from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem

def backtest_sltp(df, lookback, atr_mult, rr_min, min_conf, kelly_frac, use_adx=True):
    strat = DhaherSystem(
        parameters=None, lookback=lookback, atr_mult=atr_mult,
        rr_min=rr_min, min_confluence=min_conf,
        use_adx_filter=use_adx, adx_threshold=20
    )
    sig = strat.generate_signals(df.copy())
    capital = 1000.0
    wins = losses = 0
    peak = capital
    max_dd = 0.0
    pos = 0
    entry_p = sl_p = tp_p = 0.0
    for i in range(len(sig)):
        row = sig.iloc[i]
        if pos != 0:
            if pos == 1:
                if row["low"] <= sl_p:
                    losses += 1
                    pnl = - (abs(entry_p - sl_p) / 0.0001) * 0.10 * kelly_frac
                    capital += pnl
                    pos = 0
                elif row["high"] >= tp_p:
                    wins += 1
                    pnl = (abs(tp_p - entry_p) / 0.0001) * 0.10 * kelly_frac
                    capital += pnl
                    pos = 0
            elif pos == -1:
                if row["high"] >= sl_p:
                    losses += 1
                    pnl = - (abs(sl_p - entry_p) / 0.0001) * 0.10 * kelly_frac
                    capital += pnl
                    pos = 0
                elif row["low"] <= tp_p:
                    wins += 1
                    pnl = (abs(entry_p - tp_p) / 0.0001) * 0.10 * kelly_frac
                    capital += pnl
                    pos = 0
        if pos == 0 and row["entry"] != 0:
            if not pd.isna(row.get("sl")) and not pd.isna(row.get("tp")) and row["sl"] != 0 and row["tp"] != 0:
                pos = row["entry"]
                entry_p = row["close"]
                sl_p = row["sl"] if not pd.isna(row["sl"]) else (entry_p * 0.995 if pos == 1 else entry_p * 1.005)
                tp_p = row["tp"] if not pd.isna(row["tp"]) else (entry_p * 1.02 if pos == 1 else entry_p * 0.98)
        peak = max(peak, capital)
        dd = (peak - capital) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    total = wins + losses
    wr = wins / total * 100 if total > 0 else 0
    ret = (capital - 1000) / 1000 * 100
    return {"ret": round(ret, 2), "wr": round(wr, 1), "dd": round(max_dd * 100, 2), "trades": total, "lookback": lookback, "atr_mult": atr_mult, "rr_min": rr_min, "min_conf": min_conf, "kelly_frac": kelly_frac}

lookbacks = [14, 17, 20, 23, 25]
atr_mults = [1.0, 1.2, 1.5]
rr_mins = [2.0, 2.5, 3.0]
min_confs = [2, 3]
kelly_fracs = [0.10, 0.15, 0.25, 0.50]

results = []
total = len(lookbacks) * len(atr_mults) * len(rr_mins) * len(min_confs) * len(kelly_fracs)
log.info("Testing " + str(total) + " parameter combinations...")
idx = 0
for lb, am, rr, mc, kf in itertools.product(lookbacks, atr_mults, rr_mins, min_confs, kelly_fracs):
    try:
        r = backtest_sltp(df, lb, am, rr, mc, kf)
        results.append(r)
    except Exception as e:
        results.append({"error": str(e), "lookback": lb, "atr_mult": am, "rr_min": rr, "min_conf": mc, "kelly_frac": kf})
    idx += 1
    if idx % 50 == 0:
        log.info("  [" + str(idx) + "/" + str(total) + "] done")

passing = [r for r in results if r.get("ret", 0) > 0 and r.get("dd", 0) < 25 and r.get("trades", 0) > 10]
passing.sort(key=lambda x: x["ret"], reverse=True)
best = passing[0] if passing else None

report = {"timestamp": datetime.now().isoformat(), "data_bars": len(df), "total_configs": total, "passing": len(passing), "best": best, "top_5": passing[:5]}
out = Path(r"E:/trading/results/phase5_grid.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2, default=str))
log.info("\n=== Phase 5 GRID RESULTS ===")
log.info("Total configs: " + str(total) + ", Passing: " + str(len(passing)))
if best:
    log.info("BEST: " + str(best))
    log.info("  Return: " + str(best["ret"]) + "% | Trades: " + str(best["trades"]) + " | DD: " + str(best["dd"]) + "% | WR: " + str(best["wr"]) + "% | Kelly: " + str(best["kelly_frac"]))
else:
    log.info("No config passed the gate.")
log.info("\nTop 5:")
for r in passing[:5]:
    log.info("  ret=" + str(r["ret"]) + "% DD=" + str(r["dd"]) + "% WR=" + str(r["wr"]) + "% lookback=" + str(r["lookback"]) + " atr_mult=" + str(r["atr_mult"]) + " rr_min=" + str(r["rr_min"]) + " min_conf=" + str(r["min_conf"]) + " kelly=" + str(r["kelly_frac"]))
log.info("\n=== Phase 5 COMPLETE ===")