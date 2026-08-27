"""Inspect dhaher_system schema + params (fast, single strategy)."""
import sys, os
sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")
os.environ["PYTHONPATH"] = r"D:\repositories\Quant-Nanggroe-AI-worktree"
import numpy as np, pandas as pd, yfinance as yf, inspect
from quant_nanggroe.engine.registry import list_strategies

df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
df.columns = ["open", "high", "low", "close", "volume"]; df.index.name = "date"

S = list_strategies()
cls = S["dhaher_system"]
print("=== __init__ signature ===")
print(inspect.signature(cls.__init__))
print("=== generate_signals signature ===")
print(inspect.signature(cls.generate_signals))
try:
    inst = cls()
    r = inst.generate_signals(df)
    print("=== columns ===")
    print(list(r.columns))
    print("=== entry stats ===")
    a = r["entry"].values
    print("nonzero:", int(np.sum(np.abs(a) > 0)), "buy:", int(np.sum(a == 1)), "sell:", int(np.sum(a == -1)))
    if "stop_loss" in r.columns:
        sl = r["stop_loss"].values
        print("stop_loss nonzero:", int(np.sum(np.isfinite(sl) & (sl != 0))), "sample:", sl[np.isfinite(sl) & (sl != 0)][:5])
    if "take_profit" in r.columns:
        tp = r["take_profit"].values
        print("take_profit nonzero:", int(np.sum(np.isfinite(tp) & (tp != 0))), "sample:", tp[np.isfinite(tp) & (tp != 0)][:5])
except Exception as e:
    import traceback; traceback.print_exc()
print("DONE")
