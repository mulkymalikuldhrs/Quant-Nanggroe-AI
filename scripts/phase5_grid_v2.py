#!/usr/bin/env python
"""Phase 5 Grid — focused param tuning for DhaherSystem v1.1
Runs with Hermes venv python. ~6480 configs on 60d EURUSD M15.
"""
import itertools
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "quant_nanggroe"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("phase5")

# Download data
log.info("Downloading EURUSD=X M15 (60d)...")
df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df = df.dropna()
df.columns = [c.lower() for c in df.columns]
log.info(f"{len(df)} bars from {df.index[0]} to {df.index[-1]}")

from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem


def backtest_sltp(df, lookback, atr_mult, rr_min, min_conf, kelly_frac, use_adx=True):
    try:
        strat = DhaherSystem(
            parameters=None, lookback=lookback, atr_mult=atr_mult,
            rr_min=rr_min, min_confluence=min_conf,
            use_adx_filter=use_adx, adx_threshold=20,
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
                        capital -= (abs(entry_p - sl_p) / 0.0001) * 0.10 * kelly_frac
                        pos = 0
                    elif row["high"] >= tp_p:
                        wins += 1
                        capital += (abs(tp_p - entry_p) / 0.0001) * 0.10 * kelly_frac
                        pos = 0
                elif pos == -1:
                    if row["high"] >= sl_p:
                        losses += 1
                        capital -= (abs(sl_p - entry_p) / 0.0001) * 0.10 * kelly_frac
                        pos = 0
                    elif row["low"] <= tp_p:
                        wins += 1
                        capital += (abs(entry_p - tp_p) / 0.0001) * 0.10 * kelly_frac
                        pos = 0
            if pos == 0 and row["entry"] != 0:
                entry_p = row["close"]
                sl_p = row["sl"] if not pd.isna(row["sl"]) else entry_p * 0.995
                tp_p = row["tp"] if not pd.isna(row["tp"]) else entry_p * 1.02
                pos = int(row["entry"])
            peak = max(peak, capital)
            dd = (peak - capital) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        total = wins + losses
        wr = wins / total * 100 if total > 0 else 0
        ret = (capital - 1000) / 1000 * 100
        return {
            "ret": round(ret, 2), "wr": round(wr, 1), "dd": round(max_dd * 100, 2),
            "trades": total, "lookback": lookback, "atr_mult": atr_mult,
            "rr_min": rr_min, "min_conf": min_conf, "kelly_frac": kelly_frac,
        }
    except Exception as e:
        return {"error": str(e), "lookback": lookback, "atr_mult": atr_mult,
                "rr_min": rr_min, "min_conf": min_conf, "kelly_frac": kelly_frac}


# Parameter grids (current best: lb=20, atr=1.2, rr=2.5, mc=2, kf=0.25)
lookbacks = [14, 16, 18, 20, 22, 24, 26, 28, 30]
atr_mults = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5]
rr_mins = [1.5, 2.0, 2.5, 3.0, 3.5]
min_confs = [1, 2, 3, 4]
kelly_fracs = [0.10, 0.15, 0.20, 0.25, 0.30, 0.50]

total = len(lookbacks) * len(atr_mults) * len(rr_mins) * len(min_confs) * len(kelly_fracs)
log.info(f"Testing {total} parameter combinations...")

results = []
idx = 0
for lb, am, rr, mc, kf in itertools.product(lookbacks, atr_mults, rr_mins, min_confs, kelly_fracs):
    r = backtest_sltp(df, lb, am, rr, mc, kf)
    results.append(r)
    idx += 1
    if idx % 500 == 0:
        log.info(f"  [{idx}/{total}] done")

# Analyze
passing = [r for r in results if "error" not in r and r.get("ret", 0) > 0 and r.get("dd", 100) < 25 and r.get("trades", 0) > 5]
passing.sort(key=lambda x: x["ret"], reverse=True)
best = passing[0] if passing else None

no_errors = [r for r in results if "error" not in r and r.get("trades", 0) > 5]
for r in no_errors:
    r["sharpe_proxy"] = round(r["ret"] / max(r["dd"], 0.01), 2)
no_errors.sort(key=lambda x: x["sharpe_proxy"], reverse=True)

report = {
    "timestamp": datetime.now().isoformat(),
    "data_bars": len(df),
    "total_configs": total,
    "passing": len(passing),
    "best": best,
    "top_5": passing[:5],
    "top_10_sharpe": no_errors[:10],
}

out = _REPO / "results" / "phase5_grid_v2.json"
out.write_text(json.dumps(report, indent=2, default=str))
log.info(f"\n=== GRID COMPLETE === {total} tested, {len(passing)} pass")
if best:
    log.info(f"BEST ret={best['ret']}% dd={best['dd']}% wr={best['wr']}% kelly={best['kelly_frac']}")
    log.info(f"  params: lb={best['lookback']} atr={best['atr_mult']} rr={best['rr_min']} mc={best['min_conf']}")
else:
    log.info("No config passes all gates.")
    if no_errors:
        top = no_errors[0]
        log.info(f"Top by ret: {top['ret']}% dd={top['dd']}% kelly={top['kelly_frac']} lb={top['lookback']} atr={top['atr_mult']} rr={top['rr_min']}")
log.info(f"Saved: {out}")
