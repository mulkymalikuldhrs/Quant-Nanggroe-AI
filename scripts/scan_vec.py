"""Scan live strategies for vectorized entry columns."""
import os
import sys

sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")
os.environ["PYTHONPATH"] = r"D:\repositories\Quant-Nanggroe-AI-worktree"
import numpy as np
import yfinance as yf

from quant_nanggroe.engine.registry import list_strategies

df = yf.download("EURUSD=X", period="20d", interval="15m", auto_adjust=False, progress=False)
df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
df.columns = ["open", "high", "low", "close", "volume"]; df.index.name = "date"

S = list_strategies()
live = {k: v for k, v in S.items() if not k.startswith("archive_")}
for name, cls in live.items():
    if not hasattr(cls, "generate_signals"):
        continue
    try:
        inst = cls()
        r = inst.generate_signals(df)
    except Exception as e:
        print(f"{name}: ERR {type(e).__name__}")
        continue
    if r is None:
        continue
    if not hasattr(r, "columns"):
        continue
    cols = list(r.columns)
    for col in ["entry", "signal", "side", "direction", "action"]:
        if col in cols:
            a = np.asarray(r[col].values)
            if np.issubdtype(a.dtype, np.number):
                nz = int(np.sum(np.abs(a) > 0))
                if nz > 0:
                    print(f"{name}: {col} nz={nz}")
print("DONE")