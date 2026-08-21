"""Phase5 fangbot — fast SL/TP-aware grid for DhaherSystem on 1h EURUSD.
Caches download to CSV. Gate: SR>0.5, R>0%, DD>-25%. Minimal diff, real backtest."""
import sys, json, itertools, time
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "quant_nanggroe" / "engine" / "strategies"))
import numpy as np, pandas as pd

from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem

CACHE = Path("data/eurusd_h1_cache.csv")

def load():
    if CACHE.exists():
        return pd.read_csv(CACHE, index_col=0, parse_dates=True)
    import yfinance as yf
    df = yf.download("EURUSD=X", period="1y", interval="1h", auto_adjust=False)
    if hasattr(df.columns,"get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() if isinstance(c, str) else str(c).lower() for c in df.columns]
    df = df.dropna()
    df.to_csv(CACHE)
    return df

def backtest(df, params):
    strat = DhaherSystem(parameters=None, **{k:v for k,v in params.items() if k in ('lookback','atr_mult','rr_min','min_confluence')})
    for k,v in params.items():
        if hasattr(strat,k): setattr(strat,k,v)
    data = strat.generate_signals(df.copy())
    if data is None or len(data) < 20: return None
    capital = 10000.0
    trades = []
    position = 0; ep=es=et=0
    eq = [capital]*len(data)
    for i in range(len(data)):
        row = data.iloc[i]
        price = row['close']
        if position==1:
            eq[i] = capital + (price-ep)/ep*capital
            if price<=es:
                capital += (es-ep)/ep*capital; trades.append((es-ep)/ep)
                position=0; eq[i]=capital
            elif price>=et:
                capital += (et-ep)/ep*capital; trades.append((et-ep)/ep)
                position=0; eq[i]=capital
        elif position==-1:
            eq[i] = capital + (ep-price)/ep*capital
            if price>=es:
                capital += (ep-es)/ep*capital; trades.append((ep-es)/ep)
                position=0; eq[i]=capital
            elif price<=et:
                capital += (ep-et)/ep*capital; trades.append((ep-et)/ep)
                position=0; eq[i]=capital
        if position==0 and pd.notna(row.get('entry')) and row['entry']!=0 and pd.notna(row.get('sl')) and pd.notna(row.get('tp')) and row['sl']!=0 and row['tp']!=0:
            position=row['entry']; ep=price; es=row['sl']; et=row['tp']
    if len(trades)<5: return None
    s=pd.Series(eq); s=s[s!=0]
    r=(capital-10000)/10000*100
    ret=s.pct_change().dropna()
    sharpe=np.sqrt(8760)*ret.mean()/ret.std() if ret.std()>0 else 0
    peak=s.expanding().max(); dd=((s-peak)/peak).min()*100
    wins=sum(1 for t in trades if t>0); wr=wins/len(trades)*100
    return {'sharpe':round(sharpe,3),'ret_pct':round(r,2),'dd_pct':round(dd,2),'wr':round(wr,1),'trades':len(trades)}

def main():
    t0=time.time()
    df=load(); logf=len(df)
    grid={'lookback':[17,20,25],'atr_mult':[1.2,1.5],'rr_min':[2.5,3.0],'min_confluence':[2]}
    cfgs=list(itertools.product(*grid.values()))
    print(f"df={logf}bars configs={len(cfgs)} t0={time.time()-t0:.1f}s")
    res=[]
    for idx,(lb,am,rr,mc) in enumerate(cfgs):
        try:
            r=backtest(df,{'lookback':lb,'atr_mult':am,'rr_min':rr,'min_confluence':mc})
            if r is None: continue
            r.update({'lookback':lb,'atr_mult':am,'rr_min':rr,'min_confluence':mc})
            res.append(r)
            if r['sharpe']>0.5 and r['ret_pct']>0 and r['dd_pct']>-25:
                print(f"PASS [{idx}] lb={lb} am={am} rr={rr} mc={mc} SR={r['sharpe']:.3f} R={r['ret_pct']:+.2f}% DD={r['dd_pct']:.1f}% TR={r['trades']}")
        except Exception as e:
            print(f"ERR [{idx}]: {e}"); continue
    res.sort(key=lambda x:x.get('sharpe',0),reverse=True)
    passg=[r for r in res if r.get('sharpe',0)>0.5 and r.get('ret_pct',0)>0 and r.get('dd_pct',-999)>-25]
    best=passg[0] if passg else (res[0] if res else None)
    out=Path("results")/f"phase5_opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'total':len(res),'passing':len(passg),'best':best,'top':passg[:5]},indent=2))
    print(f"best={best}")
    return best

if __name__=='__main__': main()
