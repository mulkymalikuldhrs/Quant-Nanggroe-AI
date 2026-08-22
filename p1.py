import pathlib
t = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe\engine\backtest\walk_forward.py").read_text(encoding="utf-8", errors="ignore")
lines = t.splitlines()
for i, l in enumerate(lines, 1):
    s = l.strip()
    if ("def analyze" in s or 'mode == "cpcv"' in s or "cpcv" in s.lower() and "def " in s):
        print(f"{i}: {s[:110]}")
