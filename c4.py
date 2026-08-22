import pathlib
t = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe\engine\self_aware.py").read_text(encoding="utf-8", errors="ignore")
lines = t.splitlines()
for i, l in enumerate(lines, 1):
    s = l.strip()
    if "extra" in s or "def reflect" in s or "anomal" in s.lower() or "statements" in s and "append" in s:
        print(f"{i}: {s[:110]}")
