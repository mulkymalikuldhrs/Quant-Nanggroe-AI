"""DhaherSystem parameter grid search — SL/TP-aware backtest."""
import sys, json, logging, itertools
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('opt')

from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem
import yfinance as yf

def backtest_sltp(df, params):
    strat = DhaherSystem(**params)
    data = strat.generate_signals(df.copy())
    if data is None or data.empty:
        return None

    capital = 1000.0
    eq = [capital]
    trades = []
    position = 0
    entry_price = entry_sl = entry_tp = 0
    pos_start = 0

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
        if position == 0 and not pd.isna(row.get('entry')) and row['entry'] != 0:
            if not pd.isna(row.get('sl')) and not pd.isna(row.get('tp')) and row['sl'] != 0 and row['tp'] != 0:
                position = row['entry']
                entry_price = price
                entry_sl = row['sl']
                entry_tp = row['tp']
                pos_start = i
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

    if len(trades) < 5:
        return None

    eq = pd.Series(eq)
    ret = (capital - 1000) / 1000 * 100
    s = eq.pct_change().dropna()
    sharpe = np.sqrt(35040) * s.mean() / s.std() if s.std() > 0 else 0
    peak = eq.expanding().max()
    dd = ((eq - peak) / peak).min() * 100
    wins = sum(1 for t in trades if t > 0)
    wr = wins / len(trades) * 100
    return {'sharpe': round(sharpe, 3), 'ret_pct': round(ret, 2), 'dd_pct': round(dd, 2), 'wr': round(wr, 1), 'trades': len(trades)}

def main():
    log.info("Downloading EURUSD M15...")
    df = yf.download('EURUSD=X', period='60d', interval='15m', auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    df.columns = [c.lower() if isinstance(c, str) else c for c in df.columns]
    log.info(f"{len(df)} bars decoded")

    grid = {
        'lookback': [14, 17, 20, 23, 25, 28, 30],
        'atr_mult': [1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0],
        'rr_min': [2.0, 2.5, 3.0, 3.5],
        'min_confluence': [2, 3],
    }
    configs = list(itertools.product(*grid.values()))
    log.info(f"Total configs: {len(configs)}")

    results = []
    for idx, combo in enumerate(configs):
        lb, am, rr, mc = combo
        params = {'lookback': lb, 'atr_mult': am, 'rr_min': rr, 'min_confluence': mc}
        try:
            r = backtest_sltp(df, params)
            if r is None:
                continue
            r.update({'lookback': lb, 'atr_mult': am, 'rr_min': rr, 'min_confluence': mc})
            results.append(r)
            if r['pass'] if 'pass' in r else r.get('sharpe', 0) > 0.5 and r.get('ret_pct', 0) > 0 and r.get('dd_pct', -999) > -25:
                if idx % 5 == 0:
                    log.info(f"  [{idx}/{len(configs)}] lb={lb} am={am} rr={rr} mc={mc} SR={r['sharpe']:.3f} R={r['ret_pct']:+.2f}% DD={r['dd_pct']:.2f}% WR={r['wr']:.1f}% TRADES={r['trades']}")
            if idx % 200 == 0 and idx > 0:
                log.info(f"Progress: {idx}/{len(configs)}")
        except Exception as e:
            if idx % 100 == 0:
                log.warning(f"Config {idx} error: {e}")
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
    out = Path(r'D:/repositories/Quant-Nanggroe-AI-worktree/results') / f"dhaher_opt_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str))
    log.info(f"\nResults: {len(results)} tested, {len(passing)} passing gate")
    if best:
        log.info(f"BEST: lb={best.get('lookback')} am={best.get('atr_mult')} rr={best.get('rr_min')} mc={best.get('min_confluence')} SR={best.get('sharpe')} R={best.get('ret_pct')}% DD={best.get('dd_pct')}% WR={best.get('wr')}%")
        log.info(f"Saved: {out}")
    else:
        log.info("No passing config found. Top 5 by Sharpe:")
        for r in results[:5]:
            log.info(f"  lb={r.get('lookback')} am={r.get('atr_mult')} rr={r.get('rr_min')} mc={r.get('min_confluence')} SR={r.get('sharpe')} R={r.get('ret_pct')}% DD={r.get('dd_pct')}%")
    return report

if __name__ == '__main__':
    main()