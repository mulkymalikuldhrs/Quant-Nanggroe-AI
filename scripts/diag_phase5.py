"""Diagnostic: validate backtest harness + probe strategy edge on real EURUSD."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")
os.environ["PYTHONPATH"] = r"D:\repositories\Quant-Nanggroe-AI-worktree"
import numpy as np
import pandas as pd
import yfinance as yf

from quant_nanggroe.engine.registry import list_strategies

df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
df = df[["Open","High","Low","Close","Volume"]].dropna()
df.columns = ["open","high","low","close","volume"]; df.index.name="date"
n=len(df); close=df["close"].values.astype(float)
h,l=df["high"].values,df["low"].values; c=df["close"].values
pc=np.roll(c,1); pc[0]=c[0]
tr=np.maximum(h-l,np.maximum(np.abs(h-pc),np.abs(l-pc)))
atr=np.concatenate([[np.nan],tr[1:]]); atr=pd.Series(tr).rolling(14).mean().values

def sig(inst):
    try: r=inst.generate_signals(df)
    except Exception as e: return None, str(e)
    if r is None: return None,"none"
    if hasattr(r,"columns"):
        col=next((x for x in ["signal","side","direction","action"] if x in r.columns),None)
        if col is None: return None,"nocol"
        a=r[col].values
    else: a=np.asarray(r).flatten()
    s=np.array([0 if v is None else int(np.sign(v)) for v in a[:n]])
    return s,None

def bt(sig, sl_atr=None, tp_atr=None, initial=10000.0):
    eq=initial; peak=initial; mdd=0.0; tr_n=0; win=0; pnl=[]
    pos=False; side=0.0; entry=0.0; units=0.0; sl=0.0; tp=0.0
    for i in range(1,n):
        s=sig[i]; p=close[i]
        if not pos and s!=0:
            if sl_atr is not None:
                a=atr[i]
                if not np.isfinite(a) or a<=0: continue
                sl=entry-s*sl_atr*a; tp=entry+s*tp_atr*a
                units=(eq*0.0025)/(sl_atr*a)
            pos=True; side=float(s); entry=p; continue
        if pos:
            hl_hit=(side>0 and p>=tp) or (side<0 and p<=tp)
            ll_hit=(side>0 and p<=sl) or (side<0 and p>=sl)
            exit_p=p
            if hl_hit: exit_p=tp
            elif ll_hit: exit_p=sl
            rev=(s!=0 and np.sign(s)!=np.sign(side))
            if hl_hit or ll_hit or rev or i==n-1:
                pl=(exit_p-entry)*units*side; eq+=pl; tr_n+=1; win+=1 if pl>0 else 0; pnl.append(pl)
                peak=max(peak,eq); mdd=min(mdd,(eq-peak)/peak); pos=False
    if tr_n==0: return None
    ret=(eq-initial)/initial*100; wr=win/tr_n; m=np.mean(pnl); sd=np.std(pnl) if tr_n>1 else 0
    sh=(m/sd)*np.sqrt(252) if sd>0 else 0
    return dict(sharpe=round(sh,3),ret=round(ret,2),dd=round(mdd*100,2),wr=round(wr*100,1),trades=tr_n)

strs=list_strategies()
for name in ["MeanReversion","SMC","Wyckoff","DhaherSystem","Kronos","TrendFollow"]:
    if name not in strs: 
        print(f"{name}: NOT REGISTERED"); continue
    s,err=sig(strs[name]())
    if s is None: print(f"{name}: sig_err={err}"); continue
    nz=int((s!=0).sum())
    naive=bt(s); atr_bt=bt(s,2.5,4.0)
    print(f"{name}: signals={nz} naive={naive} atr(2.5/4)={atr_bt}")
print("DONE")
